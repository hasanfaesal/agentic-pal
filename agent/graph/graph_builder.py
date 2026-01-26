"""
Main graph builder.
Assembles all nodes and edges into the complete agent graph.

Supports two modes:
1. Legacy mode: Load filtered tools upfront based on category classification
2. Lazy loading mode: Use meta-tools (discover, schema, invoke) for dynamic discovery

Lazy loading reduces token usage
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    classify_intent,
    plan_actions,
    plan_actions_with_meta_tools,
    route_execution,
    execute_tools_parallel,
    execute_tools_sequential,
    confirm_actions,
    process_confirmation,
    synthesize_response,
)
from .edges.routers import route_after_planning, route_after_confirm
from ..tools.tool_definitions import get_tools_for_categories
from functools import partial

def build_agent_graph(
    tools_registry,
    llm,
    checkpointer=None,
    use_lazy_loading: bool = True,
):
    """
    Build the complete agent graph.
    
    Args:
        tools_registry: AgentTools instance with tool registry
        llm: LLM instance for planning and synthesis
        checkpointer: Optional checkpointer for persistence (default: MemorySaver)
        use_lazy_loading: If True, use meta-tools for dynamic tool discovery (default)
                         If False, use legacy mode with upfront tool loading
        
    Returns:
        Compiled graph ready for invocation
    """
    from ..tools.meta_tools import MetaTools
    
    # Create meta-tools for lazy loading
    meta_tools = MetaTools(tools_registry) if use_lazy_loading else None
    
    # ─────────────────────────────────────────────────────────────────────
    # Build the graph
    # ─────────────────────────────────────────────────────────────────────
    
    graph = StateGraph(AgentState)
    
    # Add nodes - using partial for dependency injection, direct refs otherwise
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("plan_actions", partial(plan_actions_with_meta_tools, meta_tools=meta_tools, llm=llm) if use_lazy_loading else partial(plan_actions, llm=llm))
    graph.add_node("route_execution", route_execution)
    graph.add_node("execute_parallel", partial(execute_tools_parallel, execute_fn=tools_registry.execute_tool))
    graph.add_node("execute_sequential", partial(execute_tools_sequential, execute_fn=tools_registry.execute_tool))
    graph.add_node("confirm_actions", confirm_actions)
    graph.add_node("process_confirmation", process_confirmation)
    graph.add_node("synthesize_response", partial(synthesize_response, llm=llm))
    
    # ─────────────────────────────────────────────────────────────────────
    # Add edges
    # ─────────────────────────────────────────────────────────────────────
    
    # Entry point
    graph.set_entry_point("classify_intent")
    
    # Linear edges
    graph.add_edge("classify_intent", "plan_actions")
    graph.add_edge("plan_actions", "route_execution")
    
    # Conditional routing after route_execution
    def _route_after_execution(state: AgentState) -> Literal["execute_parallel", "execute_sequential", "confirm_actions"]:
        mode = state.get("execution_mode", "parallel")
        if mode == "confirm":
            return "confirm_actions"
        elif mode == "sequential":
            return "execute_sequential"
        else:
            return "execute_parallel"
    
    graph.add_conditional_edges(
        "route_execution",
        _route_after_execution,
        {
            "execute_parallel": "execute_parallel",
            "execute_sequential": "execute_sequential",
            "confirm_actions": "confirm_actions",
        }
    )
    
    # After confirmation
    def _route_after_confirm(state: AgentState) -> Literal["execute_parallel", "execute_sequential", "synthesize_response"]:
        result = route_after_confirm(state)
        if result == "execute":
            # Determine execution mode for confirmed actions
            actions = state.get("actions", [])
            if any(a.get("depends_on") for a in actions):
                return "execute_sequential"
            return "execute_parallel"
        return "synthesize_response"
    
    graph.add_conditional_edges(
        "confirm_actions",
        _route_after_confirm,
        {
            "execute_parallel": "execute_parallel",
            "execute_sequential": "execute_sequential",
            "synthesize_response": "synthesize_response",
        }
    )
    
    # Execution paths converge to synthesis
    graph.add_edge("execute_parallel", "synthesize_response")
    graph.add_edge("execute_sequential", "synthesize_response")
    
    # End
    graph.add_edge("synthesize_response", END)
    
    # ─────────────────────────────────────────────────────────────────────
    # Compile with checkpointer
    # ─────────────────────────────────────────────────────────────────────
    
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["confirm_actions"],  # Interrupt for human confirmation
    )
    
    return compiled_graph


def create_graph_runner(
    calendar_service,
    gmail_service,
    tasks_service,
    model_name: str = "qwen-plus-2025-01-01",
    default_timezone: str = "UTC",
    use_lazy_loading: bool = True,
):
    """
    Create a complete graph runner with all dependencies.
    
    Args:
        calendar_service: CalendarService instance
        gmail_service: GmailService instance
        tasks_service: TasksService instance
        model_name: LLM model name
        default_timezone: Default timezone for date parsing
        use_lazy_loading: Use meta-tools for ~96% token reduction (default: True)
        
    Returns:
        Tuple of (compiled_graph, tools_registry)
    """
    from langchain_qwq import ChatQwen
    from ..tools.registry import AgentTools
    
    # Initialize LLM
    llm = ChatQwen(model=model_name)
    
    # Initialize tool registry
    tools_registry = AgentTools(
        calendar_service=calendar_service,
        gmail_service=gmail_service,
        tasks_service=tasks_service,
        default_timezone=default_timezone,
    )
    
    # Build graph
    graph = build_agent_graph(
        tools_registry, 
        llm, 
        use_lazy_loading=use_lazy_loading,
    )
    
    return graph, tools_registry
