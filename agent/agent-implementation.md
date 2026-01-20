## 1. Tool/Function Definitions Layer (tools.py)
Create wrapper functions that:

Take your service instances and expose simplified interfaces
Have clear, descriptive names that LLMs can understand
Return structured dictionaries with consistent format
Include comprehensive docstrings (these become tool descriptions for the LLM)

Each tool function should:

Accept parameters the LLM can extract from natural language
Handle date/time parsing (using dateutil or similar)
Call the appropriate service method
Return standardized responses with success/failure status

### Tools you'll need:

add_calendar_event - wraps CalendarService.add_event
delete_calendar_event - wraps CalendarService.delete_event
search_calendar_events - wraps CalendarService.search_events
list_calendar_events - wraps CalendarService.list_events
create_task - wraps TasksService.create_task
list_tasks - wraps TasksService.list_tasks
mark_task_complete - wraps TasksService.mark_task_complete
mark_task_incomplete - wraps TasksService.mark_task_incomplete
read_emails - wraps GmailService.list_messages
get_email_details - wraps GmailService.get_message_full
summarize_weekly_emails - wraps GmailService.weekly_summary

## 2. Tool Schema Generation
Use Pydantic to define schemas for each tool function:

Define tool parameters as Pydantic models
Auto-generate schemas from type hints
Provides runtime validation
Schema structure should include:

name: function name
description: what the function does (LLM uses this!)
parameters: object schema with properties, types, descriptions
required: list of required parameter names

## 3. Agent Core Logic (agent.py)
Create an Agent class that manages:

### Initialization:

LLM client (Qwen)
Service instances (CalendarService, GmailService, TasksService)
Tool registry (mapping function names to actual functions)
Conversation memory (list of messages)
System prompt defining agent behavior

### System Prompt Design:

Describe agent's role and capabilities
List available tools with brief descriptions
Set guidelines (e.g., "Always confirm before deleting", "Ask clarifying questions if dates are ambiguous") -> HITL? Human in the Loop?
Define personality/tone
Include today's date and context

### Main Processing Loop:

Take user input
Add to conversation history
Send to LLM with system prompt, conversation history, and tool schemas

### Handle LLM response types:
Text response: Stream tokens to user in real-time as they're generated (Server-Sent Events)
Function call request: Execute the tool and feed result back to LLM
Multiple function calls: Execute sequentially or in parallel if independent
Continue loop until LLM returns final text response
Limit iterations to prevent infinite loops (max 5-10 turns)

### Tool Execution:

Extract function name and arguments from LLM response
Validate function exists in registry
Parse arguments (especially dates - use dateutil.parser)
Execute function with error handling
Format result for LLM (include success status, data, error messages)
Feed tool result back to LLM for next decision

## 4. Conversation Memory
Maintain conversation state:

Store messages in order: user → assistant → tool_call → tool_result
Keep last N messages (10-20) to avoid token limits
Format varies by LLM provider:
OpenAI: [{"role": "user", "content": "..."}, {"role": "assistant", "tool_calls": [...]}, ...]
Anthropic: Similar but different structure for tool calls
Session context tracking:

Remember event IDs from just-created events for follow-up actions
Track current working calendar/task list
Store user preferences from conversation

## 5. Date/Time Parsing
Critical for natural language → API calls:

Use dateutil.parser.parse() for flexible date parsing
Handle relative dates: "tomorrow", "next Tuesday", "in 3 days"
Library option: dateparser for even more natural language support
Convert to ISO 8601 format for Google APIs
Handle timezone awareness (get from user preferences or default to UTC)
All-day events vs timed events (check if time is specified)
Date parsing wrapper:

Take natural language date string
Return ISO formatted datetime
Handle errors gracefully (ask user to clarify)
Consider duration (if only start given, default 1 hour for events)

## 6. Error Handling & Recovery
Tool Execution Errors:

Catch exceptions from service calls
Return error message to LLM in tool result
LLM can ask user for clarification or retry with different params

### LLM API Errors:

Rate limits: implement exponential backoff
Invalid responses: log and ask user to rephrase
Timeout: return graceful message
User Input Validation:

Missing required info: LLM should ask clarifying questions
Ambiguous dates: LLM confirms interpretation
Destructive operations: require explicit confirmation

## 7. Confirmation Flow for Destructive Actions
Before deleting events or bulk operations:

LLM identifies it's a destructive action
Returns a confirmation request to user (not a tool call)
Wait for explicit user confirmation ("yes", "confirm", etc.)
Only then execute the tool
Track "pending confirmation" state in conversation

## 8. Multi-turn Conversation Handling
Support complex interactions:

Example flow:

Implementation:

LLM decides if it has enough info to call tool
If not, asks question without tool call
Accumulates information across turns
Executes when complete

## 9. Main CLI Loop (main.py)
Startup sequence:

Initialize services (build_service for calendar, gmail, tasks)
Create service instances
Initialize agent with services
Load user preferences if exists
Display welcome message (show custom message from a set of lists, according to time of the day)

### REPL(Read-Eval-Print Loop):

Show prompt (e.g., "You: ")
Read user input
Handle special commands:
"exit", "quit", "q" → exit gracefully
"help" → show capabilities
"clear" → clear conversation history
Pass regular input to agent
Display agent response
Handle errors and continue loop

### Display formatting:

Use rich library for colored/formatted output
Show user input in one color, agent responses in another
Format tool results nicely (tables for events/tasks)
Show thinking/processing indicators

## 10. Dependencies to Add
Update pyproject.toml with:

openai or anthropic (LLM client)
python-dateutil (already have)
Optional: dateparser (better natural language dates)
rich (CLI formatting - highly recommended)
Optional: typer (better CLI arg parsing if you add command-line flags)
pydantic for schema generation approach
rich.console.Console() with live rendering capabilities

## 11. Configuration Management
Create environment variable handling:

OPENAI_API_KEY or ANTHROPIC_API_KEY
Optional: GOOGLE_CALENDAR_TIMEZONE (default timezone)
Store in .env file, load with python-dotenv
Never commit API keys
User preferences file (JSON):

## 12. Iteration Strategy
### Phase 1: Basic tool calling

Get LLM responding to simple requests
Single tool call per turn
No conversation memory

### Phase 2: Add conversation history

Multi-turn support
Context retention

### Phase 3: Advanced features

Multiple tool calls
Confirmation flows
Better date parsing

### Phase 4: Polish

Error recovery
Better prompts
Rich formatting
Key Gotchas to Avoid
Token limits: Trim conversation history, don't send all messages forever
Infinite loops: Limit max iterations in agent loop
Date parsing: Always validate parsed dates make sense
Tool results: Format them clearly for LLM (include all relevant data)
Error messages: Make them actionable for the LLM to handle
Timezone handling: Be consistent, store everything in ISO format
Event IDs: Return them so user can reference "the event I just created"
Testing Approach
Test scenarios:

Simple add event with explicit date/time
Add event with relative date ("tomorrow")
Multi-turn event creation (agent asks for missing info)
Delete event by searching then confirming
Create task, then mark it complete in next message
Email summary request
Error cases: invalid dates, API failures, missing permissions
Would you like me to clarify any specific aspect of this implementation, or would you like me to provide recommendations on which LLM provider or architectural pattern to use?
