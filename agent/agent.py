import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_qwq import ChatQwen
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from .tools.registry import AgentTools
from services.calendar import CalendarService
from services.gmail import GmailService
from services.tasks import TasksService


class Agent:
    """
    AI Agent that orchestrates LLM interactions with Google Calendar, Gmail, and Tasks.
    
    Manages:
    - LLM client (Qwen)
    - Tool registry and execution
    - Conversation memory
    - Multi-turn interactions
    - Confirmation flows for destructive actions
    """
    
    def __init__(
        self,
        calendar_service: CalendarService,
        gmail_service: GmailService,
        tasks_service: TasksService,
        model_name: str = "qwen-plus-2025-12-01",
        max_iterations: int = 5,
        default_timezone: str = "UTC"
    ):
        """
        Initialize the Agent.
        
        Args:
            calendar_service: CalendarService instance
            gmail_service: GmailService instance
            tasks_service: TasksService instance
            model_name: Qwen model name to use
            max_iterations: Maximum number of LLM turns per conversation
            default_timezone: Default timezone for date parsing
        """
        # Initialize LLM client
        self.llm = ChatQwen(model=model_name)
        
        # Initialize tool registry
        self.tools = AgentTools(
            calendar_service=calendar_service,
            gmail_service=gmail_service,
            tasks_service=tasks_service,
            default_timezone=default_timezone
        )
        
        # Conversation memory
        self.conversation_history: List[Any] = []
        self.max_history_length = 20  # Keep last 20 messages to avoid token limits
        
        # Configuration
        self.max_iterations = max_iterations
        self.default_timezone = default_timezone
        
        # Session state
        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self.session_context: Dict[str, Any] = {}
        
        # Generate system prompt
        self.system_prompt = self._build_system_prompt()
        
        # Get LangChain tools from registry and bind to LLM
        self.langchain_tools = self.tools.get_langchain_tools()
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt that defines the agent's role and capabilities.
        
        Returns:
            System prompt string
        """
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_time = datetime.now().strftime("%I:%M %p")
        
        # Get tool descriptions
        tool_registry = self.tools.get_tool_registry()
        tool_descriptions = []
        for name, tool_info in tool_registry.items():
            tool_descriptions.append(f"- **{name}**: {tool_info['description']}")
        
        tools_list = "\n".join(tool_descriptions)
        
        system_prompt = f"""You are AgenticPal, a helpful AI assistant that manages the user's Google Calendar, Gmail, and Google Tasks.

**Current Date & Time:** {current_date} at {current_time}
**Timezone:** {self.default_timezone}

## Your Capabilities

You have access to the following tools:

{tools_list}

## Guidelines & Behavior

1. **Be Conversational & Helpful**: Use a friendly, professional tone. Address the user naturally.

2. **Ask Clarifying Questions**: If information is missing or ambiguous, ask before taking action.
   - For dates/times: If the user says "tomorrow" or "next week", confirm the specific date.
   - For deletions: Always confirm which specific item to delete.
   - For updates: Clarify what should be changed.

3. **Handle Dates Intelligently**: 
   - Today is {current_date}
   - Parse relative dates like "tomorrow", "next Monday", "in 3 days"
   - For events without specified times, ask if it's an all-day event or needs a specific time
   - Default event duration is 1 hour if not specified

4. **Confirm Destructive Actions**: 
   - ALWAYS confirm before deleting events, tasks, or emails
   - Present the specific item to be deleted and ask for explicit confirmation
   - Only proceed after user confirms with "yes", "confirm", or similar affirmative response

5. **Multi-step Interactions**:
   - Gather all needed information across multiple turns before executing tools
   - Remember context from earlier in the conversation
   - Reference items from previous interactions (e.g., "the event I just created")

6. **Error Handling**:
   - If a tool fails, explain the error clearly and suggest alternatives
   - If dates can't be parsed, ask the user to provide dates in a clearer format
   - If permissions are missing, explain what's needed

7. **Tool Usage**:
   - Use search tools before delete/update operations to find the correct item
   - Return event IDs and task IDs so they can be referenced later
   - When listing items, format them clearly for the user

8. **Privacy & Security**:
   - Never expose sensitive information unnecessarily
   - Summarize email contents professionally
   - Respect user privacy in all interactions

## Response Format

- Use clear, concise language
- Format lists and data in readable ways
- When showing events/tasks/emails, present them in a structured format
- Confirm successful actions with brief summaries

Remember: You are proactive, intelligent, and user-focused. Your goal is to make managing calendar, email, and tasks effortless for the user."""

        return system_prompt
    
    def process_message(self, user_input: str) -> str:
        """
        Process a user message and return the agent's response.
        
        This is the main entry point for the agent's processing loop.
        Handles:
        - Adding user message to history
        - Calling LLM with tools
        - Executing tool calls
        - Managing multi-turn interactions
        - Enforcing iteration limits
        
        Args:
            user_input: The user's message
            
        Returns:
            The agent's final text response
        """
        # Add user message to conversation history
        self.conversation_history.append(HumanMessage(content=user_input))
        
        # Build messages list with system prompt + conversation history
        messages = [SystemMessage(content=self.system_prompt)] + self.conversation_history
        
        # Iterate until we get a final text response (or hit max iterations)
        for iteration in range(self.max_iterations):
            # Call LLM with tools
            response = self.llm_with_tools.invoke(messages)
            
            # Check if response has tool calls
            if response.tool_calls:
                # Add assistant message with tool calls to history
                self.conversation_history.append(response)
                messages.append(response)
                
                # Execute each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    # Execute the tool
                    result = self._execute_tool_call(tool_name, tool_args)
                    
                    # Create tool message with result
                    tool_message = ToolMessage(
                        content=json.dumps(result, default=str),
                        tool_call_id=tool_id,
                        name=tool_name
                    )
                    self.conversation_history.append(tool_message)
                    messages.append(tool_message)
            else:
                # Final text response - no more tool calls
                self.conversation_history.append(response)
                self._trim_conversation_history()
                return response.content
        
        # Max iterations reached - return graceful fallback
        fallback_response = (
            "I apologize, but I've reached the maximum number of processing steps "
            "for this request. Could you please try rephrasing your question or "
            "breaking it into smaller parts?"
        )
        self.conversation_history.append(AIMessage(content=fallback_response))
        self._trim_conversation_history()
        return fallback_response
    
    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments dict for the tool
            
        Returns:
            Tool execution result
        """
        try:
            # Execute via the tool registry
            result = self.tools.execute_tool(tool_name, arguments)
            
            # Store context for follow-up references (e.g., event IDs)
            if result.get("success") and result.get("data"):
                data = result["data"]
                # Track created/found items for future reference
                if "id" in data:
                    self.session_context[f"last_{tool_name}_id"] = data["id"]
                if "event_id" in data:
                    self.session_context["last_event_id"] = data["event_id"]
                if "task_id" in data:
                    self.session_context["last_task_id"] = data["task_id"]
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error executing {tool_name}: {str(e)}",
                "error": str(e)
            }
    
    def _is_destructive_action(self, tool_name: str) -> bool:
        """
        Check if a tool is a destructive action that requires confirmation.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if destructive, False otherwise
        """
        destructive_tools = {
            "delete_calendar_event",
            "delete_task",
        }
        return tool_name in destructive_tools
    
    def _trim_conversation_history(self):
        """
        Trim conversation history to stay within token limits.
        Keeps the most recent messages up to max_history_length.
        """
        if len(self.conversation_history) > self.max_history_length:
            # Keep system message (if first) + most recent messages
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def clear_history(self):
        """Clear conversation history. Useful for starting a fresh conversation."""
        self.conversation_history = []
        self.session_context = {}
        self.pending_confirmation = None
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation state.
        
        Returns:
            Summary string for debugging/display
        """
        return f"Conversation: {len(self.conversation_history)} messages | " \
               f"Pending confirmation: {self.pending_confirmation is not None}"
