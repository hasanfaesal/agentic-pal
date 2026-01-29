"""
Main graph builder.
Assembles all nodes and edges into the complete agent graph.

Uses meta-tools (discover, schema, invoke) for dynamic tool discovery.
This reduces token usage by ~96% compared to loading all tools upfront.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from functools import partial

from .state import AgentState
from .nodes import (
    plan_actions,
    route_execution,
    execute_tools_parallel,
    execute_tools_sequential,
    confirm_actions,
    process_confirmation,
    synthesize_response,
)
from .edges.routers import route_after_confirm


def build_agent_graph(
    tools_registry,
    llm,
    checkpointer=None,
):
    """
    Build the complete agent graph.
    
    Args:
        tools_registry: AgentTools instance with tool registry
        llm: LLM instance for planning and synthesis
        checkpointer: Optional checkpointer for persistence (default: MemorySaver)
        
    Returns:
        Compiled graph ready for invocation
    """
    from ..tools.meta_tools import MetaTools
    
    # Create meta-tools for lazy loading
    meta_tools = MetaTools(tools_registry)
    
    # ─────────────────────────────────────────────────────────────────────
    # Build the graph
    # ─────────────────────────────────────────────────────────────────────
    
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("plan_actions", partial(plan_actions, meta_tools=meta_tools, llm=llm))
    graph.add_node("route_execution", route_execution)
    graph.add_node("execute_parallel", partial(execute_tools_parallel, tool_executor=tools_registry.execute_tool))
    graph.add_node("execute_sequential", partial(execute_tools_sequential, tool_executor=tools_registry.execute_tool))
    graph.add_node("confirm_actions", confirm_actions)
    graph.add_node("process_confirmation", process_confirmation)
    graph.add_node("synthesize_response", partial(synthesize_response, llm=llm))
    
    # ─────────────────────────────────────────────────────────────────────
    # Add edges
    # ─────────────────────────────────────────────────────────────────────
    
    # Entry point - start directly at plan_actions
    graph.set_entry_point("plan_actions")
    
    # Linear edge
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
):
    """
    Create a complete graph runner with all dependencies.
    
    Args:
        calendar_service: CalendarService instance
        gmail_service: GmailService instance
        tasks_service: TasksService instance
        model_name: LLM model name
        default_timezone: Default timezone for date parsing
        
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
    graph = build_agent_graph(tools_registry, llm)
    
    return graph, tools_registry
