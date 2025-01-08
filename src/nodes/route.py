# src/nodes/route.py
from typing import Literal
from ..schemas import State

async def route_node(state: State) -> dict:
    """Routing decision node.
    
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

def determine_next_node(state: State) -> Literal["pattern", "process"]:
    """Determine the next node based on state.
    
    Used for StateGraph conditional routing.
    
    Args:
        state: Current graph state

    Returns:
        Literal["pattern", "process"]: Name of the next node
        - "pattern": If LLM needs to generate filter patterns
        - "process": If using existing filter patterns
    """
    return "pattern" if state["should_generate_patterns"] else "process"