"""
Sprint 14 Demo - Event Stream.

Shows the central real-time event pipeline in action.

Flow:
  Planner        publishes  -> PROJECT   channel
  Executive      publishes  -> PROJECT   channel
  WorkflowEngine publishes  -> WORKFLOW  channel
  AgentRuntime   publishes  -> RUNTIME   channel
  DiscussionEngine publishes -> DISCUSSION channel
  DecisionEngine publishes  -> DECISION  channel

Two subscribers observe the stream:
  Dashboard   - subscribed to ALL channels (receives everything)
  OpsMonitor  - subscribed to WORKFLOW + RUNTIME only

Run with:
    set PYTHONPATH=C:\\Projects\\AI-Company-OS
    .venv\\Scripts\\python.exe examples/demo_event_stream.py
"""

from core.event_stream import EventStream
from core.stream_channel import StreamChannel
from core.stream_event import StreamEvent


SEP = "-" * 60
SEP2 = "=" * 60


def main():
    print(SEP2)
    print("  AI Company OS - Event Stream Demo")
    print("  Sprint 14: Central Real-Time Event Pipeline")
    print(SEP2)

    # ------------------------------------------------------------------
    # 1. Create the event stream
    # ------------------------------------------------------------------
    stream = EventStream()
    print("\n[INIT] EventStream created.")

    # ------------------------------------------------------------------
    # 2. Subscribe consumers
    # ------------------------------------------------------------------
    dashboard_inbox = []
    ops_inbox = []

    stream.subscribe(
        "Dashboard",
        list(StreamChannel),                  # all channels
        callback=dashboard_inbox.append,
    )
    stream.subscribe(
        "OpsMonitor",
        [StreamChannel.WORKFLOW, StreamChannel.RUNTIME],
        callback=ops_inbox.append,
    )

    print("\n[SUBSCRIBE] Registered consumers:")
    for sub_name in stream.subscribers():
        sub = stream.find_subscription(sub_name)
        print(f"  {sub_name:20s} -> channels: {sub.channel_names()}")

    # ------------------------------------------------------------------
    # 3. Publish events from each producer
    # ------------------------------------------------------------------
    print("\n[PUBLISH] Producers emitting events...\n")

    producers = [
        (
            "Planner",
            StreamChannel.PROJECT,
            {"action": "project_analyzed", "project": "AI Company OS Platform"},
        ),
        (
            "Executive",
            StreamChannel.PROJECT,
            {"action": "project_created", "departments": 4},
        ),
        (
            "WorkflowEngine",
            StreamChannel.WORKFLOW,
            {"action": "stage_advanced", "stage": "Architecture Design"},
        ),
        (
            "AgentRuntime",
            StreamChannel.RUNTIME,
            {"action": "agent_started", "agent": "BackendEngineer"},
        ),
        (
            "DiscussionEngine",
            StreamChannel.DISCUSSION,
            {"action": "discussion_started", "topic": "Tech stack selection"},
        ),
        (
            "DecisionEngine",
            StreamChannel.DECISION,
            {"action": "decision_recommended", "title": "Choose backend framework"},
        ),
    ]

    for source, channel, payload in producers:
        event = StreamEvent.create(source, channel, payload)
        stream.publish(event)
        print(f"  [{source:20s}] -> [{channel}] {list(payload.values())[0]}")

    # ------------------------------------------------------------------
    # 4. Show what Dashboard received
    # ------------------------------------------------------------------
    print(SEP)
    print(f"\n[DASHBOARD] Received {len(dashboard_inbox)} / {len(producers)} events (all channels):\n")
    for i, e in enumerate(dashboard_inbox, 1):
        print(f"  {i}. [{e.category}] from '{e.source}'")
        action = e.get_payload_value("action", "(no action)")
        print(f"      action: {action}")

    # ------------------------------------------------------------------
    # 5. Show what OpsMonitor received
    # ------------------------------------------------------------------
    print(SEP)
    print(f"\n[OPS MONITOR] Received {len(ops_inbox)} events (WORKFLOW + RUNTIME only):\n")
    for i, e in enumerate(ops_inbox, 1):
        print(f"  {i}. [{e.category}] from '{e.source}'")
        print(f"      action: {e.get_payload_value('action')}")

    # ------------------------------------------------------------------
    # 6. History queries
    # ------------------------------------------------------------------
    print(SEP)
    print("\n[HISTORY QUERIES]")

    project_events = stream.history(channel=StreamChannel.PROJECT)
    print(f"  PROJECT channel events  : {len(project_events)}")

    planner_events = stream.history(source="Planner")
    print(f"  Events from 'Planner'   : {len(planner_events)}")

    recent = stream.history(limit=2)
    print(f"  Last 2 events (any)     : {[e.source for e in recent]}")

    latest_wf = stream.latest(StreamChannel.WORKFLOW)
    print(f"  Latest WORKFLOW event   : from '{latest_wf.source}' -> "
          f"{latest_wf.get_payload_value('action')}")

    # ------------------------------------------------------------------
    # 7. Statistics
    # ------------------------------------------------------------------
    print(SEP)
    print("\n[STATISTICS]")
    stats = stream.statistics()
    print(f"  Total events published  : {stats['total_events']}")
    print(f"  Total subscribers       : {stats['total_subscribers']}")
    print(f"  Active subscribers      : {stats['active_subscribers']}")
    print(f"\n  Events by channel:")
    for ch, count in stats["events_by_channel"].items():
        bar = "#" * count if count > 0 else "."
        print(f"    {ch:12s}: {bar} ({count})")
    print(f"\n  Events by source:")
    for src, count in stats["events_by_source"].items():
        print(f"    {src:20s}: {count}")

    # ------------------------------------------------------------------
    # 8. Add a subscriber mid-stream
    # ------------------------------------------------------------------
    print(SEP)
    ceo_inbox = []
    stream.subscribe("CEOAlert", [StreamChannel.CEO], callback=ceo_inbox.append)
    stream.publish(StreamEvent.create(
        "CEO",
        StreamChannel.CEO,
        {"action": "project_approved", "project": "AI Company OS Platform"},
    ))
    print(f"\n[LATE SUBSCRIBE] CEOAlert subscribed to CEO channel.")
    print(f"  CEOAlert inbox: {len(ceo_inbox)} event(s)")
    print(f"  Dashboard inbox: {len(dashboard_inbox)} event(s) (received CEO event too)")

    # ------------------------------------------------------------------
    # 9. Unsubscribe demo
    # ------------------------------------------------------------------
    print(SEP)
    stream.unsubscribe("OpsMonitor")
    stream.publish(StreamEvent.create("WorkflowEngine", StreamChannel.WORKFLOW, {"action": "stage_completed"}))
    print(f"\n[UNSUBSCRIBE] OpsMonitor removed.")
    print(f"  OpsMonitor inbox stays at: {len(ops_inbox)} (no new events)")
    print(f"  Dashboard inbox now at   : {len(dashboard_inbox)} (received it)")

    # ------------------------------------------------------------------
    # 10. Final state
    # ------------------------------------------------------------------
    print(SEP)
    final = stream.statistics()
    print(f"\n[FINAL STATE]")
    print(f"  Total events in log   : {final['total_events']}")
    print(f"  Active subscribers    : {final['active_subscribers']}")
    print()
    print(SEP2)
    print("  Demo complete. Event Stream is working correctly.")
    print(SEP2)


if __name__ == "__main__":
    main()
