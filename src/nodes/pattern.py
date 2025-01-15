# src/nodes/pattern.py
import logging
from typing import Any, Dict

from ..schemas import State, PatternGeneratorResult
from ..llm_tools import LanguageModelChain

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
As a Git repository analysis expert, you need to help users generate appropriate file matching patterns based on their requirements. Please follow these rules:

1. Choose the more suitable approach based on user needs:
   - Use "include" mode when users want to view specific content
   - Use "exclude" mode when users want to exclude certain content
   - Choose the approach that requires the fewest rules to meet user needs

2. Generate glob patterns that can include:
   - File name matching: e.g., *.py, *.js
   - Directory matching: e.g., tests/*, docs/*
   - Specific path matching: e.g., src/main.py

3. Pattern rules:
   - Only use letters, numbers, underscore(_), hyphen(-), dot(.), slash(/), plus(+), and asterisk(*)
   - Directory matching must end with /*
   - Do not use ** or other advanced glob syntax
   - Do not include the project name in patterns

4. Consider:
   - User's specific requirements
   - Project directory structure
   - Common development standards and best practices

5. Handling uncertainty:
   - If the directory structure doesn't clearly indicate where the desired code is located:
     * Prefer broader matches over narrow ones
     * Include parent directories that might contain relevant code
     * Consider common locations based on development conventions

Please choose the simplest effective approach to meet user requirements, but when in doubt, provide broader coverage to ensure relevant code is not missed.
"""

USER_PROMPT = """
Project directory structure:
```
{tree}
```

User requirements:
[{query}]

Please generate appropriate file matching patterns based on user requirements and project structure.
"""

class PatternGenerator:
    """A tool class that uses LLM to generate file matching patterns."""
    
    def __init__(self, model: Any):
        """Initialize pattern generator with LLM model.
        
        Args:
            model: Initialized language model instance
        """
        self.chain = LanguageModelChain(
            model_cls=PatternGeneratorResult,
            sys_msg=SYSTEM_PROMPT,
            user_msg=USER_PROMPT,
            model=model
        )
    
    async def generate(self, tree: str, query: str) -> PatternGeneratorResult:
        """Generate file matching patterns.

        Args:
            tree: Project directory structure
            query: User's natural language query

        Returns:
            PatternGeneratorResult: Generated pattern result
        """
        try:
            chain = self.chain()
            result = await chain.ainvoke({
                "tree": tree,
                "query": query,
            })
            return result
        except Exception as e:
            logger.error(f"Pattern generation failed: {str(e)}")
            raise


async def pattern_node(state: State) -> Dict[str, Any]:
    """Pattern generation node."""
    try:
        if not state.get("should_generate_patterns"):
            return {}

        generator = PatternGenerator(model=state["model"])
        result = await generator.generate(
            tree=state["tree"],
            query=state["user_query"]
        )
        logger.info(f"Generated patterns: {result['patterns']}")

        return {
            "pattern_type": result["pattern_type"],
            "patterns": result["patterns"],
            "generated_patterns": result
        }

    except Exception as e:
        logger.error(f"Pattern node failed: {str(e)}")
        raise