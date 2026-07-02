# Collaboration Hub API

Feature 21 — Agent Collaboration Hub  
Package: `core/collaboration/`

---

## Overview

The Collaboration Hub provides real multi-agent collaboration orchestration built on top of the existing Discussion Engine. Agents can discuss, review, question, agree, disagree, propose improvements and receive policy-driven governance — all in pure, synchronous Python with no AI-specific imports.

---

## Public Classes

### `MessageCategory` (enum)  
`core.collaboration.conversation_message`

| Value | Turkish Label | CSS Class | Blocking |
|---|---|---|---|
| `question` | Soru | `bubble-question` | No |
| `answer` | Yanit | `bubble-answer` | No |
| `proposal` | Oneri | `bubble-proposal` | No |
| `review` | Inceleme | `bubble-review` | No |
| `approval_request` | Onay Istegi | `bubble-approval` | Yes |
| `warning` | Uyari | `bubble-warning` | No |
| `risk` | Risk | `bubble-risk` | Yes |
| `decision` | Karar | `bubble-decision` | No |

Methods: `label() -> str`, `css_class() -> str`, `is_blocking_category() -> bool`

---

### `ConversationMessage` (frozen dataclass)  
`core.collaboration.conversation_message`

```python
@dataclass(frozen=True)
class ConversationMessage:
    id: str
    sender: str          # participant_id
    receiver: str        # participant_id or "all"
    timestamp: datetime
    category: MessageCategory
    content: str
```

**Class methods**

| Method | Signature | Description |
|---|---|---|
| `create` | `(sender, receiver, category, content, timestamp=None) -> ConversationMessage` | Factory; assigns UUID, defaults timestamp to utcnow |

**Instance methods**

| Method | Returns | Description |
|---|---|---|
| `is_broadcast()` | `bool` | True when receiver == "all" |
| `is_directed_to(participant_id)` | `bool` | True when broadcast or directed to given id |
| `is_from(participant_id)` | `bool` | True when sender matches |
| `to_dict()` | `Dict` | Serialise to JSON-safe dict (includes `category_label`, `css_class`) |

---

### `ConversationParticipant` (dataclass)  
`core.collaboration.conversation_participant`

```python
@dataclass
class ConversationParticipant:
    participant_id: str
    name: str
    role: str
    department: str = ""
    joined_at: Optional[datetime] = None
```

| Method | Returns | Description |
|---|---|---|
| `initials()` | `str` | Up to 2 uppercase chars for avatar rendering |
| `display_label()` | `str` | "Name (Role)" |
| `to_dict()` | `Dict` | Serialise |

---

### `ConversationSummary` (dataclass)  
`core.collaboration.conversation_summary`

```python
@dataclass
class ConversationSummary:
    key_decisions: List[str]
    open_questions: List[str]
    risks: List[str]
    recommendations: List[str]
    executive_summary: str
    generated_at: datetime
```

| Method | Returns | Description |
|---|---|---|
| `has_open_items()` | `bool` | True when open_questions or risks are non-empty |
| `is_complete()` | `bool` | True when no open items remain |
| `total_items()` | `int` | Sum of all list lengths |
| `to_dict()` | `Dict` | Serialise |
| `empty()` (classmethod) | `ConversationSummary` | Returns blank summary |
| `auto_generate(conversation)` (classmethod) | `ConversationSummary` | Derives from message categories |

---

### `Conversation` (dataclass)  
`core.collaboration.conversation`

```python
@dataclass
class Conversation:
    id: str
    title: str
    project_id: Optional[str]
    task_id: Optional[str]
    creator: str
    participants: List[ConversationParticipant]
    messages: List[ConversationMessage]
    summary: Optional[ConversationSummary]
    created_at: datetime
    updated_at: datetime
    status: ConversationStatus
    template_type: Optional[str]
```

**Status predicates**

| Method | Description |
|---|---|
| `is_active()` | status == ACTIVE |
| `is_closed()` | status == CLOSED |
| `is_pending_review()` | status == PENDING_REVIEW |
| `is_approved()` | status == APPROVED |
| `is_open_for_messages()` | Active or pending review |

**Participant methods**

| Method | Returns |
|---|---|
| `participant_count()` | `int` |
| `has_participant(participant_id)` | `bool` |
| `get_participant(participant_id)` | `Optional[ConversationParticipant]` |
| `participant_ids()` | `List[str]` |

**Message methods**

| Method | Returns |
|---|---|
| `message_count()` | `int` |
| `last_message()` | `Optional[ConversationMessage]` |
| `messages_by_category(category)` | `List[ConversationMessage]` |
| `messages_by_sender(sender_id)` | `List[ConversationMessage]` |
| `messages_for(participant_id)` | `List[ConversationMessage]` |
| `unread_count(participant_id, since=None)` | `int` |
| `pending_approvals()` | `List[ConversationMessage]` |

**Serialisation**

| Method | Signature |
|---|---|
| `to_dict(include_messages=True)` | `Dict` |

---

### `ConversationStatus` (enum)  
`core.collaboration.conversation`

| Value | Label |
|---|---|
| `active` | Aktif |
| `pending_review` | Incelemede |
| `approved` | Onaylandi |
| `closed` | Kapali |

---

### `CollaborationSession` (dataclass)  
`core.collaboration.collaboration_session`

```python
@dataclass
class CollaborationSession:
    id: str
    title: str
    project_id: Optional[str]
    task_id: Optional[str]
    conversation_ids: List[str]
    status: SessionStatus
    created_at: datetime
    closed_at: Optional[datetime]
    metadata: Dict
```

| Method | Returns |
|---|---|
| `is_open()` | `bool` |
| `is_reviewing()` | `bool` |
| `is_closed()` | `bool` |
| `conversation_count()` | `int` |
| `has_conversation(conv_id)` | `bool` |
| `to_dict()` | `Dict` |

---

### `ConversationPolicy` (frozen dataclass)  
`core.collaboration.conversation_policy`

```python
@dataclass
class ConversationPolicy:
    name: str
    description: str
    trigger_role: str = ""
    trigger_category: str = ""
    required_reviewer_role: str = ""
    required_response_category: str = ""
    is_blocking: bool = True
    applies_to_template: Optional[str] = None
```

| Method | Description |
|---|---|
| `matches_trigger(sender_role, category_value)` | True when policy fires for given role+category |
| `is_satisfied_by(reviewer_role, response_category_value)` | True when a response satisfies this policy |
| `applies_to(template_type)` | True when policy applies to this template (or applies globally) |
| `to_dict()` | `Dict` |

---

### `PolicyViolation` (frozen dataclass)  
`core.collaboration.conversation_policy`

| Field | Type |
|---|---|
| `policy_name` | `str` |
| `description` | `str` |
| `is_blocking` | `bool` |
| `trigger_message_id` | `Optional[str]` |

---

### `PolicyEngine`  
`core.collaboration.conversation_policy`

| Method | Signature | Description |
|---|---|---|
| `add_policy` | `(policy) -> None` | Register a policy |
| `remove_policy` | `(name) -> None` | Remove by name |
| `get_policy` | `(name) -> ConversationPolicy` | Retrieve by name |
| `list_policies` | `() -> List[ConversationPolicy]` | All registered policies |
| `has_policy` | `(name) -> bool` | Existence check |
| `policy_count` | `() -> int` | Count |
| `get_applicable_policies` | `(sender_role, category_value, template_type=None) -> List[ConversationPolicy]` | Policies matching trigger |
| `evaluate` | `(conversation) -> List[PolicyViolation]` | Find unsatisfied policies |
| `has_blocking_violations` | `(conversation) -> bool` | True if any blocking violation exists |

---

### `TemplateType` (enum)  
`core.collaboration.conversation_templates`

| Value | Turkish Label |
|---|---|
| `architecture_review` | Mimari Inceleme |
| `security_review` | Guvenlik Incelemesi |
| `sprint_planning` | Sprint Planlamasi |
| `code_review` | Kod Incelemesi |
| `risk_assessment` | Risk Degerlendirmesi |
| `ceo_briefing` | CEO Brifing |

---

### `ConversationTemplate` (dataclass)  
`core.collaboration.conversation_templates`

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable name |
| `description` | `str` | Purpose |
| `template_type` | `TemplateType` | Enum identifier |
| `default_roles` | `List[str]` | Suggested participant roles |
| `suggested_categories` | `List[str]` | Typical message categories |
| `policy_names` | `List[str]` | Policies expected for this template |
| `opening_message` | `str` | Auto-posted when conversation is created |
| `required_roles` | `List[str]` | Roles that must be present |

**Module-level functions**

| Function | Signature | Description |
|---|---|---|
| `get_template` | `(template_type: TemplateType) -> ConversationTemplate` | Retrieve built-in template |
| `list_templates` | `() -> List[ConversationTemplate]` | All built-in templates |
| `default_policies` | `() -> List[ConversationPolicy]` | 4 default governance policies |

---

### `CollaborationHub`  
`core.collaboration.collaboration_manager`

The central orchestrator. Holds conversations, sessions, and policy engine.

```python
hub = CollaborationHub(seed_default_policies=True)
```

#### Conversation Management

| Method | Signature | Returns | Description |
|---|---|---|---|
| `create_conversation` | `(title, creator, project_id=None, task_id=None, template_type=None)` | `Conversation` | Create blank or template-linked conversation |
| `create_from_template` | `(template_type, creator, project_id=None, task_id=None, title_override=None)` | `Conversation` | Instantiate from TemplateType; posts opening message |
| `join` | `(conversation_id, participant)` | `Conversation` | Add a participant |
| `leave` | `(conversation_id, participant_id)` | `Conversation` | Remove a participant |
| `send_message` | `(conversation_id, message)` | `Conversation` | Append a ConversationMessage |
| `broadcast` | `(conversation_id, sender_id, category, content)` | `Conversation` | Create + send a broadcast message |
| `summarize` | `(conversation_id)` | `ConversationSummary` | Auto-generate and attach summary |
| `request_review` | `(conversation_id)` | `Conversation` | Transition to PENDING_REVIEW |
| `approve_conversation` | `(conversation_id)` | `Conversation` | Transition to APPROVED |
| `close_conversation` | `(conversation_id, summary=None)` | `Conversation` | Transition to CLOSED |
| `get_conversation` | `(conversation_id)` | `Conversation` | Retrieve by ID |
| `list_conversations` | `(status=None)` | `List[Conversation]` | Filter by status or all |
| `list_active` | `()` | `List[Conversation]` | Active conversations |
| `list_pending_review` | `()` | `List[Conversation]` | Pending review conversations |
| `history` | `(conversation_id)` | `List[ConversationMessage]` | All messages in order |
| `conversation_count` | `()` | `int` | Total count |

#### Session Management

| Method | Signature | Returns | Description |
|---|---|---|---|
| `create_session` | `(title, project_id=None, task_id=None)` | `CollaborationSession` | New session |
| `add_to_session` | `(session_id, conversation_id)` | `CollaborationSession` | Link conversation |
| `get_session` | `(session_id)` | `CollaborationSession` | Retrieve |
| `list_sessions` | `()` | `List[CollaborationSession]` | All sessions |
| `close_session` | `(session_id)` | `CollaborationSession` | Transition to CLOSED |
| `session_count` | `()` | `int` | Total count |

#### Policy Management (delegates to PolicyEngine)

| Method | Signature | Description |
|---|---|---|
| `add_policy` | `(policy)` | Register a policy |
| `remove_policy` | `(name)` | Remove by name |
| `list_policies` | `()` | All policies |
| `get_policy` | `(name)` | Retrieve by name |
| `evaluate_policies` | `(conversation_id)` | Returns `List[PolicyViolation]` |
| `has_blocking_violations` | `(conversation_id)` | Returns `bool` |

#### Statistics

| Method | Returns |
|---|---|
| `statistics()` | `Dict[str, Any]` with keys: `total_conversations`, `active_conversations`, `pending_review_conversations`, `approved_conversations`, `closed_conversations`, `total_sessions`, `open_sessions`, `closed_sessions`, `total_messages`, `total_participants`, `total_policies`, `messages_by_category` |

---

## Exception Hierarchy

```
CollaborationHubError
├── ConversationNotFoundError
├── ConversationClosedError
├── ParticipantAlreadyError
├── ParticipantNotFoundError
├── SessionNotFoundError
├── SessionClosedError
└── InvalidConversationError
```

All are importable from `core.collaboration.collaboration_manager`.

---

## HTTP API Endpoints

All endpoints served by the Dashboard at `/api/collab/*`.

### Conversations

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/api/collab/conversations` | — | `[{...}]` list (no messages) |
| `POST` | `/api/collab/conversations` | `{title, creator, template_type?, project_id?, task_id?}` | `{success, conversation}` |
| `GET` | `/api/collab/conversations/{id}` | — | full conversation with messages |
| `POST` | `/api/collab/conversations/{id}/join` | `{participant_id, name, role, department?}` | `{success, conversation}` |
| `POST` | `/api/collab/conversations/{id}/broadcast` | `{sender, category, content}` | `{success, conversation}` |
| `POST` | `/api/collab/conversations/{id}/summarize` | — | `{success, summary}` |
| `POST` | `/api/collab/conversations/{id}/request-review` | — | `{success, conversation}` |
| `POST` | `/api/collab/conversations/{id}/approve` | — | `{success, conversation}` |
| `POST` | `/api/collab/conversations/{id}/close` | — | `{success, conversation}` |
| `GET` | `/api/collab/conversations/{id}/history` | — | `[{...}]` message list |
| `GET` | `/api/collab/conversations/{id}/evaluate-policies` | — | `{violations: [...], has_blocking}` |
| `GET` | `/api/collab/statistics` | — | statistics dict |
| `GET` | `/api/collab/templates` | — | `[{...}]` template list |

### Sessions

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/api/collab/sessions` | — | `[{...}]` session list |
| `POST` | `/api/collab/sessions` | `{title, project_id?, task_id?}` | `{success, session}` |
| `POST` | `/api/collab/sessions/{id}/close` | — | `{success, session}` |
| `POST` | `/api/collab/sessions/{id}/add` | `{conversation_id}` | `{success, session}` |

### Policies

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/api/collab/policies` | — | `[{...}]` policy list |
| `POST` | `/api/collab/policies` | `{name, description, trigger_role?, trigger_category?, required_reviewer_role?, required_response_category?, applies_to_template?, is_blocking?}` | `{success, policy}` |
| `DELETE` | `/api/collab/policies/{name}` | — | `{success}` |

---

## Dashboard Pages

| URL | Page | Description |
|---|---|---|
| `/collab` | `collab` | Hub overview (KPIs, active conversations, pending reviews, sessions, message stats) |
| `/collab/conversations` | `collab_conversations` | Full conversation list with interactive chat panel |
| `/collab/sessions` | `collab_sessions` | Session cards with conversation grouping |
| `/collab/policies` | `collab_policies` | Policy table with policy evaluator tool |

---

## Chat Bubble CSS Classes

| Class | Category | Color |
|---|---|---|
| `.bubble-question` | Question | Blue left border |
| `.bubble-answer` | Answer | Green left border |
| `.bubble-proposal` | Proposal | Purple left border |
| `.bubble-review` | Review | Cyan left border |
| `.bubble-approval` | Approval request | Amber left border |
| `.bubble-warning` | Warning | Orange left border |
| `.bubble-risk` | Risk | Red left border |
| `.bubble-decision` | Decision | Lime left border |

---

## Default Policies

Four policies are pre-loaded when `seed_default_policies=True`:

| Name | Trigger | Required Reviewer | Blocking |
|---|---|---|---|
| `security-review-required` | `security_review` template, any category | `security_engineer` role, `review` response | Yes |
| `qa-review-required` | `code_review` template, any category | `qa_engineer` role, `review` response | Yes |
| `executive-summary-required` | any `risk` category | `cto` role, `review` response | No |
| `ceo-approval-required` | `ceo_briefing` template, `approval_request` | `ceo` role, `decision` response | Yes |
