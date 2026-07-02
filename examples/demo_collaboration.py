"""
Feature 21: Agent Collaboration Hub - End-to-End Demo

Demonstrates the full lifecycle of the CollaborationHub:
- Creating conversations from templates
- Adding participants
- Sending typed messages
- Policy evaluation
- Auto-generating summaries
- Session grouping
- Statistics

Run:
    python examples/demo_collaboration.py
"""

from core.collaboration.collaboration_manager import CollaborationHub
from core.collaboration.conversation_message import MessageCategory
from core.collaboration.conversation_participant import ConversationParticipant
from core.collaboration.conversation_templates import TemplateType, list_templates
from core.collaboration.conversation_policy import ConversationPolicy


def separator(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> None:
    separator("1. Initialize CollaborationHub")
    hub = CollaborationHub(seed_default_policies=True)
    print(f"  Hub ready. Default policies loaded: {hub.policy_engine.policy_count()}")

    # ------------------------------------------------------------------
    separator("2. List built-in templates")
    for tmpl in list_templates():
        print(f"  [{tmpl.template_type.value}] {tmpl.name}")
        print(f"    Roles: {', '.join(tmpl.default_roles)}")
        print(f"    Opening: {tmpl.opening_message[:60]}...")

    # ------------------------------------------------------------------
    separator("3. Create a Security Review from template")
    conv = hub.create_from_template(
        TemplateType.SECURITY_REVIEW,
        creator="alice",
        project_id="proj-api-v2",
        title_override="API v2 Kimlik Dogrulama Guvenligi",
    )
    print(f"  Conversation: {conv.id[:16]}... — {conv.title}")
    print(f"  Status: {conv.status.label()}")
    print(f"  Template opening message appended: {conv.message_count()} message(s)")

    # ------------------------------------------------------------------
    separator("4. Add participants")
    participants = [
        ConversationParticipant("alice", "Alice Yilmaz", "security_engineer", "Engineering"),
        ConversationParticipant("bob",   "Bob Kaya",     "developer",         "Engineering"),
        ConversationParticipant("carol", "Carol Demir",  "cto",               "Executive"),
    ]
    for p in participants:
        hub.join(conv.id, p)
        print(f"  Joined: {p.display_label()} [{p.initials()}]")
    print(f"  Total participants: {conv.participant_count()}")

    # ------------------------------------------------------------------
    separator("5. Send typed messages")
    messages = [
        ("alice", MessageCategory.PROPOSAL,
         "JWT yerine OAuth2 + PKCE kullanmayi oneriyorum. Daha guvenli ve standart."),
        ("bob",   MessageCategory.QUESTION,
         "Mevcut sistemde token yenileme suresi ne kadar? Bunu bilmeden gecis plani yapamam."),
        ("alice", MessageCategory.ANSWER,
         "Simdi 24 saat. OAuth2'ye geciste 1 saat erisim / 30 gun yenileme token oneriyorum."),
        ("carol", MessageCategory.RISK,
         "Gecis sirasinda mevcut token'lar gecersiz kalacak. Kullanicilari bilgilendirme plani lazim."),
        ("bob",   MessageCategory.REVIEW,
         "PKCE akisi inceledim. Dogru yapilandirilirsak guvenli. Implementasyon rehberi hazirlanmali."),
        ("alice", MessageCategory.DECISION,
         "Karar: OAuth2 + PKCE benimseniyor. Gecis tarihi Sprint 23. Bildirim 2 hafta once gidecek."),
    ]
    for sender_id, cat, content in messages:
        hub.broadcast(conv.id, sender_id, cat, content)
        print(f"  [{cat.label():>14}] {sender_id}: {content[:55]}...")

    # ------------------------------------------------------------------
    separator("6. Evaluate policies")
    violations = hub.evaluate_policies(conv.id)
    if violations:
        print(f"  {len(violations)} violation(s) found:")
        for v in violations:
            flag = "BLOCK" if v.is_blocking else "WARN"
            print(f"    [{flag}] {v.policy_name}: {v.description}")
    else:
        print("  No policy violations.")

    # ------------------------------------------------------------------
    separator("7. Auto-generate summary")
    summary = hub.summarize(conv.id)
    print(f"  Executive summary:")
    print(f"    {summary.executive_summary}")
    print(f"  Key decisions : {summary.key_decisions}")
    print(f"  Risks         : {summary.risks}")
    print(f"  Open questions: {summary.open_questions}")
    print(f"  Recommendations: {summary.recommendations}")
    print(f"  Has open items: {summary.has_open_items()}")

    # ------------------------------------------------------------------
    separator("8. Request review and approve")
    hub.request_review(conv.id)
    print(f"  Status after request_review: {conv.status.label()}")

    hub.approve_conversation(conv.id)
    print(f"  Status after approve: {conv.status.label()}")

    # ------------------------------------------------------------------
    separator("9. Create an Architecture Review conversation manually")
    arch_conv = hub.create_conversation(
        title="Mikroservis vs Monolit Karari",
        creator="carol",
        project_id="proj-platform",
        template_type="architecture_review",
    )
    hub.join(arch_conv.id, ConversationParticipant("carol", "Carol Demir", "cto", "Executive"))
    hub.join(arch_conv.id, ConversationParticipant("dave",  "Dave Arslan", "architect", "Engineering"))
    hub.broadcast(arch_conv.id, "carol",
                  MessageCategory.QUESTION,
                  "Mikroservis'e gecmek bu sprint icin makul mu?")
    hub.broadcast(arch_conv.id, "dave",
                  MessageCategory.RISK,
                  "Servis aginda gecikme riski var. Oncesinde latency testleri yapilmali.")
    hub.broadcast(arch_conv.id, "carol",
                  MessageCategory.PROPOSAL,
                  "Once pilot olarak 2 servisi ayiralim, sonra kademeli gecis yapalim.")
    print(f"  Arch review created: {arch_conv.title}")
    print(f"  Messages: {arch_conv.message_count()}")
    print(f"  Pending approvals: {len(arch_conv.pending_approvals())}")

    # ------------------------------------------------------------------
    separator("10. Group into a session")
    session = hub.create_session("Platform Q3 Kararlari", project_id="proj-platform")
    hub.add_to_session(session.id, conv.id)
    hub.add_to_session(session.id, arch_conv.id)
    print(f"  Session: {session.title}")
    print(f"  Conversations in session: {session.conversation_count()}")

    # ------------------------------------------------------------------
    separator("11. Add a custom policy")
    custom_policy = ConversationPolicy(
        name="architect-must-review-risk",
        description="Herhangi bir Risk mesaji, bir mimar tarafindan inceleme gerektiriyor.",
        trigger_category="risk",
        required_reviewer_role="architect",
        required_response_category="review",
        is_blocking=False,
    )
    hub.add_policy(custom_policy)
    print(f"  Custom policy added: {custom_policy.name}")
    print(f"  Total policies: {hub.policy_engine.policy_count()}")

    # ------------------------------------------------------------------
    separator("12. Message category helpers")
    for cat in MessageCategory:
        print(f"  {cat.value:>18} | {cat.label():>16} | {cat.css_class():>20} | blocking={cat.is_blocking_category()}")

    # ------------------------------------------------------------------
    separator("13. Hub statistics")
    stats = hub.statistics()
    for key, val in stats.items():
        if key != "messages_by_category":
            print(f"  {key}: {val}")
    print("  Messages by category:")
    for cat, count in stats["messages_by_category"].items():
        if count:
            print(f"    {cat}: {count}")

    # ------------------------------------------------------------------
    separator("14. Pending approvals across active conversations")
    for c in hub.list_active():
        pending = c.pending_approvals()
        if pending:
            print(f"  [{c.title[:40]}] {len(pending)} pending approval(s)")

    # ------------------------------------------------------------------
    separator("15. History of security review")
    history = hub.history(conv.id)
    print(f"  {len(history)} messages total")
    for msg in history:
        print(f"  [{msg.category.label():>14}] {msg.sender}: {msg.content[:50]}...")

    separator("Demo complete")
    print("  All CollaborationHub public APIs exercised successfully.")
    print()


if __name__ == "__main__":
    main()
