# src/nodes/route.py
from typing import Literal
from ..schemas import State

async def route_pattern_node(state: State) -> dict:
    """Pattern generation routing node.
    
    Responsibilities:
    1. Check if user provided a natural language query
    2. Set should_generate_patterns flag
    
    Args:
        state: Current graph state

    Returns:
        dict: Contains updated should_generate_patterns flag
    """
    # Check if there's a user query
    has_query = bool(state.get("user_query"))
    
    return {
        "should_generate_patterns": has_query
    }

async def route_diagram_node(state: State) -> dict:
    """Diagram generation routing node.
    
    Responsibilities:
    1. Check if diagram generation is enabled
    2. Set should_generate_diagram flag
    
    Args:
        state: Current graph state

    Returns:
        dict: Contains updated should_generate_diagram flag
    """
    return {
        "should_generate_diagram": state.get("should_generate_diagram", True)
    }

def determine_next_node(state: State) -> Literal["pattern", "process"]:
    """Determine the next node for pattern generation path.
    
    Used for StateGraph conditional routing.
    
    Args:
        state: Current graph state

    Returns:
        Literal["pattern", "process"]: Name of the next node
        - "pattern": If LLM needs to generate filter patterns
        - "process": If using existing filter patterns
    """
    return "pattern" if state["should_generate_patterns"] else "process"

def determine_diagram_node(state: State) -> Literal["diagram", "process"]:
    """Determine whether to generate diagram or proceed to content processing.
    
    Used for StateGraph conditional routing.
    
    Args:
        state: Current graph state

    Returns:
        Literal["diagram", "process"]: Name of the next node
        - "diagram": If system design diagram should be generated
        - "process": If diagram generation is disabled, proceed to content processing
    """
    return "diagram" if state["should_generate_diagram"] else "process"