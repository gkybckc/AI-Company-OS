"""
Sprint 13 Demo - Workflow Engine: Software Project.

Steps through all 8 stages of a SOFTWARE_PROJECT workflow, demonstrating
create, start, advance through every stage, and complete.

Run with:
    .venv\\Scripts\\python.exe examples/demo_workflow.py
"""

from core.workflow_engine import WorkflowEngine
from core.workflow_template import WorkflowTemplate
from core.workflow import WorkflowEventType


def separator(char="-", width=60):
    print(char * width)


def main():
    print("=" * 60)
    print("  AI Company OS - Workflow Engine Demo")
    print("  Sprint 13: Software Project Lifecycle")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Create engine and workflow
    # ------------------------------------------------------------------
    engine = WorkflowEngine()

    wf = engine.create_workflow(
        name="AI Company OS Platform",
        description="Full product build using the Software Project template.",
        template=WorkflowTemplate.SOFTWARE_PROJECT,
    )

    print(f"\n[CREATE] Workflow: '{wf.name}'")
    print(f"  ID       : {wf.id}")
    print(f"  Template : {wf.template.display_name()}")
    print(f"  Status   : {wf.status}")
    print(f"  Stages   : {wf.stage_count()}")
    print(f"  Progress : {wf.progress:.0%}")

    separator()
    print("  Stage Plan:")
    for s in wf.stages:
        flags = []
        if s.approval_required:
            flags.append("APPROVAL")
        if s.discussion_allowed:
            flags.append("DISCUSSION")
        if s.memory_required:
            flags.append("MEMORY")
        flag_str = " [" + ", ".join(flags) + "]" if flags else ""
        print(f"    {s.order}. {s.name}{flag_str}")

    # ------------------------------------------------------------------
    # 2. Start
    # ------------------------------------------------------------------
    separator()
    engine.start(wf.id)
    print(f"\n[START]")
    print(f"  Status       : {wf.status}")
    print(f"  Current Stage: {wf.current_stage.name}")

    # ------------------------------------------------------------------
    # 3. Step through all stages
    # ------------------------------------------------------------------
    separator()
    print("\n[ADVANCE THROUGH ALL STAGES]")
    print()

    step = 1
    while True:
        cs = wf.current_stage
        next_s = wf.next_stage()

        print(f"  Step {step}: Stage {cs.order}/{wf.stage_count()} - '{cs.name}'")
        print(f"    Progress  : {wf.progress:.0%}")
        print(f"    Completed : {wf.completed_stage_count()}")
        print(f"    Remaining : {wf.remaining_stage_count()}")

        if cs.approval_required:
            print(f"    [APPROVAL REQUIRED at this stage]")
        if cs.discussion_allowed:
            print(f"    [DISCUSSION allowed at this stage]")
        if cs.memory_required:
            print(f"    [MEMORY entry will be created]")

        if next_s is None:
            print(f"    -> Final stage reached. Calling complete()...")
            engine.complete(wf.id)
            break
        else:
            print(f"    -> Advancing to '{next_s.name}'...")
            engine.advance(wf.id)

        print()
        step += 1

    # ------------------------------------------------------------------
    # 4. Final state
    # ------------------------------------------------------------------
    separator()
    print(f"\n[COMPLETE]")
    print(f"  Status          : {wf.status}")
    print(f"  Progress        : {wf.progress:.0%}")
    print(f"  Current Stage   : {wf.current_stage}")
    print(f"  Completed Stages: {wf.completed_stage_count()} / {wf.stage_count()}")
    print(f"  Transitions     : {len(wf.transitions)}")
    print(f"  Events recorded : {wf.event_count()}")

    # ------------------------------------------------------------------
    # 5. Event log summary
    # ------------------------------------------------------------------
    separator()
    print("\n[EVENT LOG SUMMARY]")
    for i, e in enumerate(wf.events, 1):
        stage_info = f" (stage: {e.stage_id})" if e.stage_id else ""
        print(f"  {i:2d}. {e.event_type}{stage_info}")

    # ------------------------------------------------------------------
    # 6. Completed stages listing
    # ------------------------------------------------------------------
    separator()
    print("\n[COMPLETED STAGES IN ORDER]")
    for s in wf.completed_stages:
        print(f"  {s.order}. {s.name}")

    # ------------------------------------------------------------------
    # 7. Statistics
    # ------------------------------------------------------------------
    separator()
    stats = engine.statistics()
    print("\n[ENGINE STATISTICS]")
    print(f"  Total workflows : {stats['total_workflows']}")
    print(f"  Completed       : {stats['completed_count']}")
    print(f"  Active          : {stats['active_count']}")
    print(f"  Avg progress    : {stats['average_progress']:.0%}")

    # ------------------------------------------------------------------
    # 8. Workflow summary dict
    # ------------------------------------------------------------------
    separator()
    print("\n[WORKFLOW SUMMARY DICT]")
    for k, v in wf.summary().items():
        print(f"  {k:30s}: {v}")

    separator("=")
    print("  Demo complete. All 8 stages executed successfully.")
    separator("=")


if __name__ == "__main__":
    main()
