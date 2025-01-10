# src/nodes/pattern.py
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..schemas import State, PatternGeneratorResult

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

4. Consider:
   - User's specific requirements
   - Project directory structure
   - Common development standards and best practices

Please choose the simplest effective approach to meet user requirements.

Output your answer as a JSON object that conforms to the following schema:
{schema}

Important instructions:
1. Ensure your JSON is valid and properly formatted.
2. Do not include the schema definition in your answer.
3. Only output the data instance that matches the schema.
4. Do not include any explanations or comments within the JSON output.
"""

USER_PROMPT = """
Project directory structure:
{tree}

User requirements:
{query}

Please generate appropriate file matching patterns based on user requirements and project structure.
"""

class PatternGenerator:
    """A tool class that uses LLM to generate file matching patterns."""
    
    def __init__(self, model: Any):
        """Initialize pattern generator with LLM model.
        
        Args:
            model: Initialized language model instance
        """
        self.model = model
        self.parser = JsonOutputParser(pydantic_object=PatternGeneratorResult)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]).partial(schema=PatternGeneratorResult.model_json_schema())
        
        self.chain = self.prompt | self.model | self.parser
    
    async def generate(self, tree: str, query: str) -> PatternGeneratorResult:
        """Generate file matching patterns.

        Args:
            tree: Project directory structure
            query: User's natural language query

        Returns:
            PatternGeneratorResult: Generated pattern result
        """
        try:
            result = await self.chain.ainvoke({
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