"""
Event Stream for AI Company OS.

The EventStream is the central real-time event pipeline. Every module
publishes StreamEvents to it; consumers subscribe to channels to receive
the events they care about.

The EventStream contains NO business logic. It only distributes events.

Design constraints:
- Pure in-memory. No networking, no WebSocket, no async, no databases,
  no external libraries.
- Append-only event log. Published events are never removed or modified.
- Synchronous callback delivery. When publish() is called, all matching
  subscriber callbacks are invoked before publish() returns.
- Callbacks are optional. A subscriber without a callback can still
  retrieve its events via history().

Integration:
- Existing modules are NOT modified. The EventStream is a new, standalone
  component that any module may use by importing it.

Architecture reference: §2.8 Event Bus, §10 Event Flow,
§3 Layer 3 (Infrastructure Layer).
"""

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.stream_channel import StreamChannel
from core.stream_event import StreamEvent
from core.stream_subscription import StreamSubscription


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EventStreamError(Exception):
    """Base class for all Event Stream errors."""


class SubscriptionNotFoundError(EventStreamError):
    """
    Raised when an operation references a subscriber that is not registered.

    Raised by unsubscribe() and find_subscription() when the given subscriber
    name is not present in the stream.
    """


class DuplicateSubscriberError(EventStreamError):
    """
    Raised when subscribe() is called for a subscriber that already exists.

    Call unsubscribe() first, then subscribe() again to re-register with
    different channels.
    """


class InvalidEventError(EventStreamError):
    """
    Raised when publish() receives an invalid argument.

    Covers: None event, wrong type.
    """


# ---------------------------------------------------------------------------
# EventStream
# ---------------------------------------------------------------------------

class EventStream:
    """
    Central real-time event pipeline for AI Company OS.

    The EventStream provides a single, shared publish-subscribe bus. Any
    module that produces observable events creates a StreamEvent and calls
    publish(). Any module that wants to react to events calls subscribe()
    with a list of channels and an optional callback.

    The engine stores every published event in an append-only log. This log
    is accessible via history() for audit, replay, and inspection. No event
    is ever removed from the log.

    Delivery model
    --------------
    When publish(event) is called:
    1. The event is appended to the global event log.
    2. For each subscription whose channel list contains event.category,
       the subscriber's registered callback (if any) is invoked synchronously
       with the event as its sole argument.
    3. Callback errors are caught and silently ignored — a misbehaving
       subscriber never prevents other subscribers from receiving the event
       or prevents the publish() call from returning normally.

    Callback signature: Callable[[StreamEvent], None]

    Subscription lifecycle
    ----------------------
    subscribe(subscriber, channels, callback=None)
        -> registers, raises DuplicateSubscriberError if already registered.
    unsubscribe(subscriber)
        -> removes registration, raises SubscriptionNotFoundError if absent.

    There is no update — to change channels, unsubscribe then subscribe again.

    Usage example:
        stream = EventStream()
        received = []
        stream.subscribe("Dashboard", list(StreamChannel), callback=received.append)
        stream.publish(StreamEvent.create("Planner", StreamChannel.PROJECT, {...}))
        assert len(received) == 1

    Attributes:
        _events:        Append-only list of all published StreamEvents.
        _subscriptions: Dict[subscriber_name, StreamSubscription].
        _callbacks:     Dict[subscriber_name, Callable]. Separate from
                        subscriptions so StreamSubscription stays serializable.
    """

    def __init__(self) -> None:
        self._events: List[StreamEvent] = []
        self._subscriptions: Dict[str, StreamSubscription] = {}
        self._callbacks: Dict[str, Callable[[StreamEvent], None]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish(self, event: StreamEvent) -> None:
        """
        Publish an event to the stream.

        The event is appended to the global event log and synchronously
        delivered to all subscribers registered for its channel. Callback
        errors are silently ignored.

        Args:
            event: The StreamEvent to publish.

        Raises:
            InvalidEventError: If event is None or not a StreamEvent.
        """
        if event is None:
            raise InvalidEventError("Published event must not be None.")
        if not isinstance(event, StreamEvent):
            raise InvalidEventError(
                f"Published event must be a StreamEvent instance; "
                f"got {type(event).__name__}."
            )

        self._events.append(event)
        self._deliver_to_subscribers(event)

    def subscribe(
        self,
        subscriber: str,
        channels: List[StreamChannel],
        callback: Optional[Callable[[StreamEvent], None]] = None,
    ) -> StreamSubscription:
        """
        Register a subscriber to receive events from specified channels.

        If a callback is provided it will be invoked synchronously every
        time an event is published to one of the registered channels.
        Events published before this call are NOT delivered to the callback,
        but they are available via history().

        Args:
            subscriber: Unique name for this subscriber. Must be non-empty.
            channels:   Channels to subscribe to. May be empty (subscriber
                        will be registered but receive no events until
                        they re-subscribe with channels).
            callback:   Optional callable. Signature: (StreamEvent) -> None.
                        Called synchronously on matching publish() calls.

        Returns:
            The newly created StreamSubscription.

        Raises:
            InvalidEventError:       If subscriber is empty or channels is None.
            DuplicateSubscriberError: If this subscriber is already registered.
        """
        if not subscriber or not subscriber.strip():
            raise InvalidEventError("Subscriber name must not be empty.")
        if channels is None:
            raise InvalidEventError("Channels list must not be None.")

        key = subscriber.strip()
        if key in self._subscriptions:
            raise DuplicateSubscriberError(
                f"Subscriber '{key}' is already registered. "
                "Call unsubscribe() first to change channels."
            )

        subscription = StreamSubscription(
            subscriber=key,
            channels=list(channels),
        )
        self._subscriptions[key] = subscription
        if callback is not None:
            self._callbacks[key] = callback

        return subscription

    def unsubscribe(self, subscriber: str) -> None:
        """
        Remove a subscriber's registration from the stream.

        After unsubscribe(), the subscriber's callback will no longer be
        invoked. The global event log is unaffected — history() still
        returns all previously published events.

        Args:
            subscriber: The subscriber to remove.

        Raises:
            SubscriptionNotFoundError: If subscriber is not registered.
        """
        if subscriber not in self._subscriptions:
            raise SubscriptionNotFoundError(
                f"Subscriber '{subscriber}' is not registered in the stream."
            )
        del self._subscriptions[subscriber]
        self._callbacks.pop(subscriber, None)

    def history(
        self,
        channel: Optional[StreamChannel] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[StreamEvent]:
        """
        Return published events from the append-only log.

        Filters are cumulative: if both channel and source are provided,
        only events matching BOTH filters are returned.

        Args:
            channel: Optional channel filter. Returns only events published
                     to this channel.
            source:  Optional source filter. Returns only events from this
                     source identity.
            limit:   Optional maximum number of results. When provided,
                     returns the most recent `limit` matching events.
                     Non-positive values are ignored (all matching returned).

        Returns:
            List of StreamEvent sorted by timestamp ascending (oldest first).
            Returns a new list; mutations do not affect the internal log.
        """
        events: List[StreamEvent] = list(self._events)

        if channel is not None:
            events = [e for e in events if e.category == channel]

        if source is not None:
            events = [e for e in events if e.source == source]

        if limit is not None and limit > 0:
            events = events[-limit:]

        return events

    def latest(
        self, channel: Optional[StreamChannel] = None
    ) -> Optional[StreamEvent]:
        """
        Return the most recently published event.

        Args:
            channel: Optional channel filter. Returns the most recent event
                     published to this channel. If None, returns the most
                     recent event across all channels.

        Returns:
            The most recently published StreamEvent matching the filter,
            or None if no events have been published (or no events match
            the channel filter).
        """
        if channel is None:
            return self._events[-1] if self._events else None

        matching = [e for e in self._events if e.category == channel]
        return matching[-1] if matching else None

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate statistics about the event stream.

        Returns:
            Dict with keys:
                total_events           — Total number of published events.
                total_subscribers      — Current number of registered subscribers.
                events_by_channel      — Dict mapping channel value to event count.
                events_by_source       — Dict mapping source name to event count.
                subscribers_by_channel — Dict mapping channel value to the number
                                         of subscribers registered for that channel.
                active_subscribers     — Sorted list of registered subscriber names.
        """
        events_by_channel: Dict[str, int] = {c.value: 0 for c in StreamChannel}
        events_by_source: Dict[str, int] = {}

        for event in self._events:
            events_by_channel[event.category.value] = (
                events_by_channel.get(event.category.value, 0) + 1
            )
            events_by_source[event.source] = (
                events_by_source.get(event.source, 0) + 1
            )

        subscribers_by_channel: Dict[str, int] = {c.value: 0 for c in StreamChannel}
        for sub in self._subscriptions.values():
            for ch in sub.channels:
                subscribers_by_channel[ch.value] = (
                    subscribers_by_channel.get(ch.value, 0) + 1
                )

        return {
            "total_events": len(self._events),
            "total_subscribers": len(self._subscriptions),
            "events_by_channel": dict(events_by_channel),
            "events_by_source": dict(events_by_source),
            "subscribers_by_channel": dict(subscribers_by_channel),
            "active_subscribers": sorted(self._subscriptions.keys()),
        }

    def find_subscription(self, subscriber: str) -> StreamSubscription:
        """
        Return the subscription record for a registered subscriber.

        Args:
            subscriber: The subscriber name to look up.

        Returns:
            The StreamSubscription for this subscriber.

        Raises:
            SubscriptionNotFoundError: If subscriber is not registered.
        """
        return self._require_subscription(subscriber)

    def subscribers(self) -> List[str]:
        """
        Return a sorted list of all registered subscriber names.

        Returns a new list — mutations do not affect the internal registry.
        """
        return sorted(self._subscriptions.keys())

    def event_count(self) -> int:
        """Return the total number of published events in the log."""
        return len(self._events)

    def subscriber_count(self) -> int:
        """Return the number of currently registered subscribers."""
        return len(self._subscriptions)

    def is_subscriber(self, subscriber: str) -> bool:
        """Return True if the given subscriber is currently registered."""
        return subscriber in self._subscriptions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_subscription(self, subscriber: str) -> StreamSubscription:
        """Return the subscription or raise SubscriptionNotFoundError."""
        sub = self._subscriptions.get(subscriber)
        if sub is None:
            raise SubscriptionNotFoundError(
                f"Subscriber '{subscriber}' is not registered in the stream."
            )
        return sub

    def _deliver_to_subscribers(self, event: StreamEvent) -> None:
        """
        Call each matching subscriber's callback with the event.

        A subscriber matches if event.category is in its channels list.
        Callback errors are silently caught so no subscriber failure can
        prevent other subscribers from receiving the event.
        """
        for subscriber_name, subscription in self._subscriptions.items():
            if subscription.is_subscribed_to(event.category):
                callback = self._callbacks.get(subscriber_name)
                if callback is not None:
                    try:
                        callback(event)
                    except Exception:
                        pass
