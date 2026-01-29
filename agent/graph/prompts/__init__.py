"""
DSPy-based prompt templates and modules for LLM calls.

This module provides both DSPy signatures/modules for modern usage
and legacy string prompts for backwards compatibility.

Use the config module to switch between modes:
    from agent.graph.prompts import PromptConfig, use_dspy, use_legacy
    
    # Switch to DSPy mode
    use_dspy()
    
    # Or switch to legacy mode
    use_legacy()
    
    # Or use environment variable:
    # export AGENTIC_PAL_PROMPT_MODE=dspy
"""

# Configuration and mode switching
from .config import (
    PromptConfig,
    PromptMode,
    use_dspy,
    use_legacy,
    is_dspy_mode,
    is_legacy_mode,
)

# DSPy Signatures and Modules for Action Planning
from .plan_actions import (
    # Signatures
    ToolDiscovery,
    ToolInvocation,
    ActionPlanner,
    MultiStepPlanner,
    # Modules
    ActionPlannerModule,
    ToolDiscoveryModule,
    ToolInvocationModule,
    MultiStepPlannerModule,
    # Legacy support
    PLAN_ACTIONS_SYSTEM_PROMPT,
    get_plan_actions_system_prompt,
)

# DSPy Signatures and Modules for Response Synthesis
from .synthesize_response import (
    # Signatures
    ResponseSynthesis,
    ErrorRecovery,
    MultiResultSynthesis,
    ConversationalResponse,
    ConfirmationResponse,
    # Modules
    ResponseSynthesisModule,
    ErrorRecoveryModule,
    MultiResultSynthesisModule,
    ConversationalModule,
    ConfirmationModule,
    ResponseHandler,
    # Legacy support
    SYNTHESIZE_RESPONSE_PROMPT,
)

__all__ = [
    # Configuration
    "PromptConfig",
    "PromptMode",
    "use_dspy",
    "use_legacy",
    "is_dspy_mode",
    "is_legacy_mode",
    # Action Planning - Signatures
    "ToolDiscovery",
    "ToolInvocation", 
    "ActionPlanner",
    "MultiStepPlanner",
    # Action Planning - Modules
    "ActionPlannerModule",
    "ToolDiscoveryModule",
    "ToolInvocationModule",
    "MultiStepPlannerModule",
    # Response Synthesis - Signatures
    "ResponseSynthesis",
    "ErrorRecovery",
    "MultiResultSynthesis",
    "ConversationalResponse",
    "ConfirmationResponse",
    # Response Synthesis - Modules
    "ResponseSynthesisModule",
    "ErrorRecoveryModule",
    "MultiResultSynthesisModule",
    "ConversationalModule",
    "ConfirmationModule",
    "ResponseHandler",
    # Legacy support
    "PLAN_ACTIONS_SYSTEM_PROMPT",
    "SYNTHESIZE_RESPONSE_PROMPT",
    "get_plan_actions_system_prompt",
]
