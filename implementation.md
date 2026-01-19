## 1. Project Setup & Environment

Use uv + .venv; keep credentials/token, LLM API keys out of git.
Dependencies: google-api-python-client, google-auth-httplib2, google-auth-oauthlib, python-dateutil (for parsing), rich/typer for CLI ergonomics, LLM client library (e.g., openai, anthropic), optional embedding library for semantic search.

## 2. Google Cloud Platform Configuration

Enable Calendar, Gmail, Tasks APIs.
OAuth consent screen with sensitive (calendar, tasks) and restricted (https://mail.google.com/) scopes; add your account as test user.
Create OAuth client (Desktop), download credentials.json, store securely.

## 3. Authentication Implementation

Scopes (full access as requested):
Calendar: https://www.googleapis.com/auth/calendar
Gmail: https://mail.google.com/ (restricted)
Tasks: https://www.googleapis.com/auth/tasks
Reusable auth helper: load token, refresh if possible, otherwise run browser flow; cache token.json; allow overriding scope set.
Graceful fallback: on invalid_grant or revoked token, drop token and re-consent.

## 4. Google Calendar Integration (minimal actions)

Add event (title, start/end, description, optional attendees).
Delete event (by ID or simple search then confirm).
Timezone: default to primary calendar settings; support all-day vs timed.
Error handling for quota/403/404.

## 5. Gmail Integration (read/summarize)

List recent messages (filter by sender/label/date).
Fetch snippets/bodies for summarization.
Weekly summary: gather this week’s messages (date filter), summarize subjects/snippets.
Pagination handling; avoid modifying state (read-only unless you later add labels).

## 6. Google Tasks Integration

List tasks (default list; allow selecting list).
Create task (title, optional due).
Mark task complete/incomplete.
Simple error handling for missing list/items.

## 7. Main Application Logic (agentic LLM loop)

LLM Agent Pattern: User inputs natural language; LLM determines intent and required tool(s).
Tools available to agent (function definitions): add_event, delete_event, create_task, mark_task_done, list_tasks, read_emails, summarize_emails.
Agent loops: parse user intent, call appropriate tool(s), return result, ask for clarification if needed.
Tool execution: validate inputs, call service helpers, return structured response.
Error recovery: on API errors, return user-friendly message; agent can re-prompt for missing info.
LLM Setup: Configure with your API key; system prompt instructs agent on available tools and constraints (e.g., avoid deleting without confirmation).

## 8. Memory & Preferences

User preferences file (JSON/YAML): default calendar, preferred task list, timezone, working hours.
Conversation context: store last N interactions (user input + agent action) in memory to handle multi-turn requests ("mark the event I just created as reminder 1 hour before").
Session state: track current calendar/task list context to avoid re-querying on repeated ops.
Init flow: on first run, prompt user for timezone, default calendar, default task list; save to preferences file.

## 9. Interaction Model (CLI now)

User types natural language intent: "add dentist appointment next Tuesday at 2pm", "mark all emails from bob as read this week", "create a todo: buy groceries".
LLM agent parses intent, extracts entities (dates, times, names), calls appropriate tools.
Multi-turn support: agent can ask clarifying questions ("which Tuesday?", "which calendar?").
Confirmations: destructive ops (delete event, bulk action) prompt user before execution.
Feedback loop: agent reports action result; user can refine or request next action.
Help: user can ask "what can you do?" → agent describes capabilities.

## 10. Embeddings & Semantic Search (optional, for Gmail)

Use embeddings to find semantically similar emails (e.g., "show me emails about project X").
Build embeddings index for email bodies/subjects on startup or periodically.
On user query "summarize emails about …", embed query and find closest matches via cosine similarity.
Trade-off: improves search UX but adds latency/cost; defer if not critical.

## 11. Testing & Validation

Fresh auth flow (delete token.json, run once).
LLM agent happy path: natural language input → correct tool calls.
Calendar add/delete + Gmail summarize + task management via agent.
Multi-turn conversation: agent asks clarifying questions, remembers context.
Error handling: API failures, invalid dates, missing data.
Offline/no-internet and LLM API errors.

## 12. Documentation & Deployment

README: setup (uv sync, auth flow, LLM API key setup), scopes used, supported capabilities, safety notes.
Example conversations showing agent in action.
Note restricted Gmail scope warnings for unverified app.
Keep web-app plans out-of-scope for now.

## 13. Future Enhancements (post-MVP)

Add batching (bulk delete events/mark tasks in one request).
Persistent conversation history (file-based or database).
Embeddings for semantic email search (if needed).
Web app UI (after CLI solid), add auth persistence for server use.
Implement configuration file for user preferences
Add natural language processing for more intuitive commands
Cache frequently accessed data
Add batch operations (delete multiple events, mark multiple tasks)
The core dependencies you'll need are: google-api-python-client, google-auth-httplib2, google-auth-oauthlib, and potentially python-dateutil for date parsing.

The most critical step is Google Cloud setup - without proper API credentials, nothing else will work. Start there first before writing any code.
