"""
Tool execution nodes.
Handles parallel and sequential tool execution.
"""

import concurrent.futures
from typing import Dict, Any, List
from ..state import AgentState


def _topological_sort(actions: List[dict]) -> List[dict]:
    """
    Sort actions by dependencies (topological sort).
    
    Args:
        actions: List of action dicts with depends_on fields
        
    Returns:
        Actions sorted so dependencies come first
    """
    # Build dependency graph
    action_map = {a["id"]: a for a in actions}
    in_degree = {a["id"]: len(a.get("depends_on", [])) for a in actions}
    dependents = {a["id"]: [] for a in actions}
    
    for action in actions:
        for dep_id in action.get("depends_on", []):
            if dep_id in dependents:
                dependents[dep_id].append(action["id"])
    
    # Kahn's algorithm
    queue = [aid for aid, deg in in_degree.items() if deg == 0]
    sorted_actions = []
    
    while queue:
        current = queue.pop(0)
        sorted_actions.append(action_map[current])
        
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    return sorted_actions


def _inject_dependencies(action: dict, results: dict) -> dict:
    """
    Inject results from dependent actions into current action's args.
    
    Args:
        action: Action with potential from_result references
        results: Results from previously executed actions
        
    Returns:
        Action with resolved args
    """
    args = action.get("args", {}).copy()
    
    # Check for from_result references
    for key, value in list(args.items()):
        if isinstance(value, str) and value in results:
            # Replace reference with actual result data
            args[key] = results[value].get("data", results[value])
        elif key == "from_result" and value in results:
            # Special handling: merge result data into args
            result_data = results[value].get("data", {})
            if isinstance(result_data, dict):
                args.update(result_data)
            del args["from_result"]
    
    return {**action, "args": args}


def execute_tools_parallel(state: AgentState, tool_executor) -> AgentState:
    """
    Execute all actions in parallel using ThreadPoolExecutor.
    
    Used when actions are independent (no depends_on).
    
    Args:
        state: Current agent state
        tool_executor: Function to execute a single tool (name, args) -> result
        
    Returns:
        Updated state with results
    """
    actions = state.get("actions", [])
    results = state.get("results", {}).copy()
    
    if not actions:
        return {**state, "results": results}
    
    # Execute all tools in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        
        for action in actions:
            future = executor.submit(
                tool_executor,
                action["tool"],
                action.get("args", {})
            )
            futures[action["id"]] = future
        
        # Collect results
        for action_id, future in futures.items():
            try:
                results[action_id] = future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                results[action_id] = {
                    "success": False,
                    "error": "Tool execution timed out",
                    "message": "The operation took too long to complete",
                }
            except Exception as e:
                results[action_id] = {
                    "success": False,
                    "error": str(e),
                    "message": f"Tool execution failed: {str(e)}",
                }
    
    return {**state, "results": results}


def execute_tools_sequential(state: AgentState, tool_executor) -> AgentState:
    """
    Execute actions sequentially respecting dependencies.
    
    Used when actions have depends_on relationships.
    
    Args:
        state: Current agent state
        tool_executor: Function to execute a single tool (name, args) -> result
        
    Returns:
        Updated state with results
    """
    actions = state.get("actions", [])
    results = state.get("results", {}).copy()
    
    if not actions:
        return {**state, "results": results}
    
    # Sort actions by dependencies
    sorted_actions = _topological_sort(actions)
    
    # Execute in order
    for action in sorted_actions:
        # Inject results from dependencies
        resolved_action = _inject_dependencies(action, results)
        
        try:
            result = tool_executor(
                resolved_action["tool"],
                resolved_action.get("args", {})
            )
            results[action["id"]] = result
        except Exception as e:
            results[action["id"]] = {
                "success": False,
                "error": str(e),
                "message": f"Tool execution failed: {str(e)}",
            }
    
    return {**state, "results": results}
