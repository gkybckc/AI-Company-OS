"""
StreamSubscription model for AI Company OS Event Stream.

A StreamSubscription records which channels a named subscriber has registered
to receive events from. Subscriptions are created by EventStream.subscribe()
and removed by EventStream.unsubscribe().

Architecture reference: §2.8 Event Bus, §10 Event Flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.stream_channel import StreamChannel


@dataclass(frozen=True)
class StreamSubscription:
    """
    Immutable record of a subscriber's registration with the Event Stream.

    A StreamSubscription declares which channels a named subscriber is
    interested in. When an event is published to a channel that appears
    in a subscription's channels list, the subscriber (and any registered
    callback) is notified.

    Subscriptions are created by EventStream.subscribe() and deleted by
    EventStream.unsubscribe(). The object itself is immutable — to change
    channels, the subscriber must unsubscribe and re-subscribe.

    Attributes:
        subscriber: Unique name identifying this subscriber. Set by the
                    caller at subscription time.
        channels:   The channels this subscriber wants to receive events
                    from. An empty list means the subscriber is registered
                    but will not receive any events (valid but unusual).
        created_at: UTC timestamp of when this subscription was created.
                    Defaults to the current time at construction.
    """

    subscriber: str
    channels: List[StreamChannel]
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------
    # Subscription query helpers
    # ------------------------------------------------------------------

    def is_subscribed_to(self, channel: StreamChannel) -> bool:
        """Return True if this subscription covers the given channel."""
        return channel in self.channels

    def channel_count(self) -> int:
        """Return the number of channels this subscription covers."""
        return len(self.channels)

    def is_subscribed_to_all(self) -> bool:
        """
        Return True if this subscription covers every available channel.

        Checks whether all StreamChannel values appear at least once
        in self.channels.
        """
        return set(self.channels) == set(StreamChannel)

    def has_channels(self) -> bool:
        """Return True if this subscription covers at least one channel."""
        return bool(self.channels)

    def channel_names(self) -> List[str]:
        """Return a list of string values for all subscribed channels."""
        return [str(c) for c in self.channels]

    def covers_any(self, channels: List[StreamChannel]) -> bool:
        """Return True if this subscription overlaps with the given channels."""
        return any(c in self.channels for c in channels)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a compact dict representation suitable for logging."""
        return {
            "subscriber": self.subscriber,
            "channels": self.channel_names(),
            "channel_count": self.channel_count(),
            "is_subscribed_to_all": self.is_subscribed_to_all(),
            "created_at": self.created_at.isoformat(),
        }
