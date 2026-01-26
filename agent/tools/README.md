# Agent Tools

Tool registry and lazy loading system for the agentic-pal agent.

## Architecture

```
tool_definitions.py   ← add new tools here
        ↓
   ┌────┴────┐
   ↓         ↓
registry.py  tool_index.py
   ↓              ↓
AgentTools   discover_tools()
   ↓              ↓
   └──────┬───────┘
          ↓
     meta_tools.py
          ↓
     MetaTools (3 meta-tools for LLM)
```

## Files

| File                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `tool_definitions.py` | all tool metadata lives here                         |
| `registry.py`         | `AgentTools` class — wraps services, executes tools  |
| `tool_index.py`       | Lightweight discovery index (~15 tokens/tool)        |
| `meta_tools.py`       | 3 meta-tools for lazy loading (~96% token reduction) |
| `__init__.py`         | Public exports                                       |

## Adding a New Tool

1. **Define the tool** in `tool_definitions.py`:

```python
"my_new_tool": ToolDefinition(
    name="my_new_tool",
    summary="Short description for discovery",
    description="Full description for LLM binding",
    category="calendar",  # or "gmail", "tasks"
    actions=["create", "write"],
    is_write=True,  # requires confirmation?
    schema=schemas.MyNewToolParams,  # Pydantic model in schemas.py
),
```

2. **Add the Pydantic schema** in `agent/schemas.py`:

```python
class MyNewToolParams(BaseModel):
    param1: str = Field(..., description="Required param")
    param2: Optional[int] = Field(None, description="Optional param")
```

3. **Implement the method** in `registry.py`:

```python
def my_new_tool(self, param1: str, param2: Optional[int] = None) -> dict:
    """Implementation."""
    return self.calendar.some_method(param1, param2)
```

That's it — the tool is automatically available in the registry, index, and meta-tools.

## Usage

### Direct Execution

```python
from agent.tools import AgentTools

tools = AgentTools(calendar_service, gmail_service, tasks_service)
result = tools.execute_tool("list_tasks", {"max_results": 10})
```

### Lazy Loading (Meta-Tools)

```python
from agent.tools import MetaTools

meta = MetaTools(tools)

# Step 1: Discover available tools
meta.discover_tools(categories=["calendar"], actions=["create"])

# Step 2: Get schema for a specific tool
meta.get_tool_schema("add_calendar_event")

# Step 3: Execute
meta.invoke_tool("add_calendar_event", {"title": "Meeting", "start_time": "tomorrow 2pm"})
```

### LangChain Integration

```python
langchain_tools = tools.get_langchain_tools()  # All tools
langchain_tools = tools.get_langchain_tools_for_categories(["calendar"])  # Filtered
```

## Tool Categories

| Category   | Tools                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| `calendar` | add_calendar_event, delete_calendar_event, search_calendar_events, list_calendar_events, update_calendar_event |
| `tasks`    | create_task, list_tasks, mark_task_complete, mark_task_incomplete, delete_task, update_task, get_task_lists    |
| `gmail`    | read_emails, get_email_details, summarize_weekly_emails, search_emails, list_unread_emails                     |

## Token Optimization

The meta-tools pattern reduces context size by ~96%:

| Mode                        | Tokens |
| --------------------------- | ------ |
| All 17 tools loaded upfront | ~6,800 |
| 3 meta-tools only           | ~550   |

The LLM uses `discover_tools` → `get_tool_schema` → `invoke_tool` to load schemas on-demand.
