# src/nodes/route.py
from typing import Literal
from ..schemas import State

async def route_node(state: State) -> dict:
    """路由判断节点。
    
    职责：
    1. 检查用户是否提供了自然语言查询
    2. 设置 should_generate_patterns 标志
    
    Args:
        state: 当前图状态

    Returns:
        dict: 包含更新的 should_generate_patterns 标志
    """
    # 检查是否有用户查询
    has_query = bool(state.get("user_query"))
    
    return {
        "should_generate_patterns": has_query
    }

def determine_next_node(state: State) -> Literal["pattern", "process"]:
    """根据状态判断下一个节点。
    
    用于 StateGraph 的条件路由。
    
    Args:
        state: 当前图状态

    Returns:
        Literal["pattern", "process"]: 下一个节点的名称
        - "pattern": 如果需要使用 LLM 生成过滤模式
        - "process": 如果直接使用已有过滤模式
    """
    return "pattern" if state["should_generate_patterns"] else "process"