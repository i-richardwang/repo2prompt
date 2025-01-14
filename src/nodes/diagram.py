import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..schemas import State, DiagramGeneratorResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are tasked with creating a system design diagram using Mermaid.js based on the repository structure and content analysis. Your goal is to accurately represent the architecture and design of the project.

Guidelines for creating the diagram:

1. Analyze the repository structure:
   - Identify main components (frontend, backend, services, etc.)
   - Understand the relationships between components
   - Note key configuration files and build scripts

2. Consider the following elements:
   - Main application components
   - External services and dependencies
   - Data flow between components
   - API layers and interfaces
   - Database or storage systems
   - Build and deployment components

3. Create a Mermaid.js diagram that:
   - Uses appropriate shapes for different components
   - Shows clear relationships and data flow
   - Includes all major architectural elements
   - Maintains a logical layout
   - Adds relevant click events for file references

4. Follow these technical guidelines:
   - Orient the diagram vertically when possible
   - Use clear and concise labels
   - Include a legend if needed
   - Ensure proper Mermaid.js syntax
   - Add click events for important components

Please analyze the provided repository structure and content to generate an accurate system design diagram.

Output your answer as a JSON object that conforms to the following schema:
{schema}

Important instructions:
1. Ensure your JSON is valid and properly formatted.
2. The diagram field should contain valid Mermaid.js code.
3. Include click events for relevant components.
4. Provide a brief explanation of the diagram.
"""

USER_PROMPT = """
Repository structure:
```
{tree}
```

Repository content:
```
{content}
```

Please generate a system design diagram that accurately represents this project's architecture.
"""

class DiagramGenerator:
    """A tool class that uses LLM to generate system design diagrams."""
    
    def __init__(self, model: Any):
        """Initialize diagram generator with LLM model."""
        self.model = model
        self.parser = JsonOutputParser(pydantic_object=DiagramGeneratorResult)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]).partial(schema=DiagramGeneratorResult.model_json_schema())
        
        self.chain = self.prompt | self.model | self.parser
    
    async def generate(self, tree: str, content: str) -> DiagramGeneratorResult:
        """Generate system design diagram.

        Args:
            tree: Repository structure
            content: Repository content

        Returns:
            DiagramGeneratorResult: Generated diagram result
        """
        try:
            result = await self.chain.ainvoke({
                "tree": tree,
                "content": content,
            })
            return result
        except Exception as e:
            logger.error(f"Diagram generation failed: {str(e)}")
            raise

async def diagram_node(state: State) -> Dict[str, Any]:
    """System design diagram generation node."""
    try:
        generator = DiagramGenerator(model=state["model"])
        result = await generator.generate(
            tree=state["tree"],
            content=state["content"]
        )
        logger.info("Generated system design diagram")

        return {
            "diagram": result["diagram"],
            "diagram_explanation": result["explanation"],
            "generated_diagram": result
        }

    except Exception as e:
        logger.error(f"Diagram node failed: {str(e)}")
        raise 