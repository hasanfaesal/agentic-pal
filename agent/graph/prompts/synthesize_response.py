"""
DSPy-based prompts and signatures for response synthesis.
LLM Call #2: Formats tool results into natural language.
"""

import dspy
from typing import List, Optional, Literal


class ResponseSynthesis(dspy.Signature):
    """
    Synthesize a natural, helpful response from tool execution results.
    
    ## Guidelines
    
    1. **Be Concise**: Summarize what was done in 1-3 sentences
    2. **Be Specific**: Include relevant details (event times, task names, email counts)
    3. **Handle Errors**: If a tool failed, explain clearly and suggest alternatives
    4. **Format Nicely**: Use bullet points or numbered lists for multiple items
    5. **Confirm Success**: Explicitly state what was created/modified/deleted
    6. **Include IDs**: Mention event or task IDs so user can reference them later
    """
    
    user_request: str = dspy.InputField(desc="The user's original request")
    tool_results: str = dspy.InputField(
        desc="JSON string of tool execution results with success/failure status"
    )
    
    response: str = dspy.OutputField(
        desc="Natural, helpful response summarizing what was done"
    )


class ErrorRecovery(dspy.Signature):
    """
    Generate a helpful error message when tool execution fails.
    Explain what went wrong and suggest alternatives or next steps.
    """
    
    user_request: str = dspy.InputField(desc="The user's original request")
    error_message: str = dspy.InputField(desc="The error that occurred")
    tool_name: str = dspy.InputField(desc="The tool that failed")
    
    explanation: str = dspy.OutputField(desc="Clear explanation of what went wrong")
    suggestions: List[str] = dspy.OutputField(desc="Suggested next steps or alternatives")
    response: str = dspy.OutputField(desc="Complete user-friendly error response")


class MultiResultSynthesis(dspy.Signature):
    """
    Synthesize responses when multiple tools were executed.
    Organizes and presents results from multiple operations clearly.
    """
    
    user_request: str = dspy.InputField(desc="The user's original request")
    tool_results: List[str] = dspy.InputField(
        desc="List of JSON results from each tool execution"
    )
    
    summary: str = dspy.OutputField(
        desc="Brief summary of all actions taken (1-2 sentences)"
    )
    detailed_response: str = dspy.OutputField(
        desc="Detailed response with bullet points for each action result"
    )


class ConversationalResponse(dspy.Signature):
    """
    Generate a conversational response when no tools were needed.
    For general questions, greetings, or clarifications.
    """
    
    user_message: str = dspy.InputField(desc="The user's message")
    conversation_context: Optional[str] = dspy.InputField(
        desc="Recent conversation history for context", default=""
    )
    
    response: str = dspy.OutputField(
        desc="Natural, helpful conversational response"
    )


class ConfirmationResponse(dspy.Signature):
    """
    Generate a confirmation message for destructive operations.
    Clearly explains what will happen and asks for confirmation.
    """
    
    action_type: str = dspy.InputField(
        desc="Type of action requiring confirmation (e.g., 'delete')"
    )
    target: str = dspy.InputField(
        desc="What will be affected (e.g., 'calendar event: Team Meeting')"
    )
    
    confirmation_message: str = dspy.OutputField(
        desc="Clear message asking user to confirm the action"
    )


# --- DSPy Modules ---

class ResponseSynthesisModule(dspy.Module):
    """
    DSPy module for synthesizing natural language responses from tool results.
    """
    
    def __init__(self):
        super().__init__()
        self.synthesize = dspy.Predict(ResponseSynthesis)
    
    def forward(self, user_request: str, tool_results: str):
        return self.synthesize(
            user_request=user_request,
            tool_results=tool_results
        )


class ErrorRecoveryModule(dspy.Module):
    """
    DSPy module for generating helpful error messages.
    Uses Chain of Thought to reason about error causes and solutions.
    """
    
    def __init__(self):
        super().__init__()
        self.recover = dspy.ChainOfThought(ErrorRecovery)
    
    def forward(self, user_request: str, error_message: str, tool_name: str):
        return self.recover(
            user_request=user_request,
            error_message=error_message,
            tool_name=tool_name
        )


class MultiResultSynthesisModule(dspy.Module):
    """
    DSPy module for synthesizing responses from multiple tool results.
    """
    
    def __init__(self):
        super().__init__()
        self.synthesize = dspy.ChainOfThought(MultiResultSynthesis)
    
    def forward(self, user_request: str, tool_results: List[str]):
        return self.synthesize(
            user_request=user_request,
            tool_results=tool_results
        )


class ConversationalModule(dspy.Module):
    """
    DSPy module for conversational responses when no tools are needed.
    """
    
    def __init__(self):
        super().__init__()
        self.respond = dspy.Predict(ConversationalResponse)
    
    def forward(self, user_message: str, conversation_context: str = ""):
        return self.respond(
            user_message=user_message,
            conversation_context=conversation_context
        )


class ConfirmationModule(dspy.Module):
    """
    DSPy module for generating confirmation messages for destructive actions.
    """
    
    def __init__(self):
        super().__init__()
        self.confirm = dspy.Predict(ConfirmationResponse)
    
    def forward(self, action_type: str, target: str):
        return self.confirm(
            action_type=action_type,
            target=target
        )


# --- Combined Response Handler ---

class ResponseHandler(dspy.Module):
    """
    Unified response handler that routes to appropriate synthesis module
    based on the situation (success, error, no tools, confirmation needed).
    """
    
    def __init__(self):
        super().__init__()
        self.synthesize = ResponseSynthesisModule()
        self.error_recovery = ErrorRecoveryModule()
        self.multi_result = MultiResultSynthesisModule()
        self.conversational = ConversationalModule()
        self.confirmation = ConfirmationModule()
    
    def forward(
        self,
        user_request: str,
        tool_results: Optional[str] = None,
        error: Optional[dict] = None,
        needs_confirmation: Optional[dict] = None,
        conversation_context: str = ""
    ):
        # Handle confirmation needed
        if needs_confirmation:
            return self.confirmation(
                action_type=needs_confirmation.get("action", "delete"),
                target=needs_confirmation.get("target", "item")
            )
        
        # Handle error case
        if error:
            return self.error_recovery(
                user_request=user_request,
                error_message=error.get("message", "Unknown error"),
                tool_name=error.get("tool", "unknown")
            )
        
        # Handle no tools case (conversational)
        if not tool_results:
            return self.conversational(
                user_message=user_request,
                conversation_context=conversation_context
            )
        
        # Normal synthesis
        return self.synthesize(
            user_request=user_request,
            tool_results=tool_results
        )


# --- Legacy Support (for backwards compatibility) ---

SYNTHESIZE_RESPONSE_PROMPT = """You are a helpful personal assistant that summarizes task results.

## Guidelines

1. **Be Concise**: Summarize what was done in 1-3 sentences
2. **Be Specific**: Include relevant details (event times, task names, email counts)
3. **Handle Errors**: If a tool failed, explain clearly and suggest alternatives
4. **Format Nicely**: Use bullet points or numbered lists for multiple items
5. **Confirm Success**: Explicitly state what was created/modified/deleted
6. **Include IDs**: Mention event or task IDs so user can reference them later

## Examples

Good response for calendar event:
"Done! I've scheduled 'Team Sync' for tomorrow at 10:00 AM (Event ID: abc123). You'll receive a calendar invite shortly."

Good response for multiple actions:
"Here's what I did:
• Created 3 tasks from your unread emails
• Scheduled 'Project Review' for Friday at 2 PM
• Found 5 emails from your manager (2 marked urgent)"

Good response for error:
"I couldn't delete the event because the ID wasn't found. Could you specify which event you'd like to delete? Try: 'List my events for this week' to see available events."

## Your Task

Take the tool results and user's original request, then generate a natural, helpful response.
"""
