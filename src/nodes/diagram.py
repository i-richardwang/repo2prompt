import logging
from typing import Any, Dict, Optional

from ..schemas import State, DiagramGeneratorResult
from ..llm_tools import LanguageModelChain

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a principal software engineer tasked with creating a comprehensive system design diagram using Mermaid.js. Your goal is to analyze a repository's structure and content to create an accurate architectural visualization.

First, analyze the provided repository to:
1. Identify the project type (e.g., full-stack application, library, tool)
2. Understand the main architectural components and their relationships
3. Recognize key technologies, frameworks, and services used
4. Map the logical data and control flow between components

Then, create a Mermaid.js diagram that meets these specifications:

1. Diagram Structure:
   - Select appropriate diagram type (typically flowchart TD for vertical orientation)
   - Create clear component hierarchy and grouping
   - Ensure logical top-to-bottom flow of architecture
   - Maintain balanced visual layout

2. Component Representation:
   - Use distinct shapes for different component types:
     * Frontend/UI components: rectangles with rounded edges
     * Backend services: regular rectangles
     * Databases: cylinders
     * External services: clouds
     * API/Interfaces: hexagons
   - Add clear, concise labels for each component
   - Group related components using subgraphs
   - Apply consistent styling and formatting

3. Relationships and Flow:
   - Show clear directional relationships between components
   - Label data flow or interaction types on connections
   - Use different arrow styles for different types of relationships
   - Ensure all connections are meaningful and documented

4. Technical Requirements:
   - Always use quotes for paths or URLs in node definitions
   - Never apply styles directly to subgraph declarations
   - Use proper Mermaid.js syntax for special characters
   - Format node IDs to be valid and unique
   - Keep node labels concise but descriptive

5. Visual Optimization:
   - Orient diagram vertically when possible (TD or TB direction)
   - Avoid long horizontal chains of components
   - Balance the visual weight of different sections
   - Use consistent spacing between elements
   - Limit diagram width to maintain readability

6. Essential Elements:
   - Include frontend architecture and components
   - Show backend services and APIs
   - Represent data storage and caching
   - Display external service integrations
   - Show build and deployment flow
   - Include important configuration and infrastructure elements

Critical Syntax Rules:
1. Always encapsulate paths in quotes: `component["api/service"]` not `component[api/service]`
2. Style nodes individually: `node1["Frontend"]:::frontend` not `subgraph "Frontend":::frontend`
3. Use consistent node naming: alphanumeric with no spaces in IDs
4. Format links properly: `nodeA --> nodeB`
5. Group related components: `subgraph name [title]`

Please analyze the provided repository structure and content to generate an accurate system design diagram.
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
        self.chain = LanguageModelChain(
            model_cls=DiagramGeneratorResult,
            sys_msg=SYSTEM_PROMPT,
            user_msg=USER_PROMPT,
            model=model
        )
    
    async def generate(self, tree: str, content: str) -> DiagramGeneratorResult:
        """Generate system design diagram.

        Args:
            tree: Repository structure
            content: Repository content

        Returns:
            DiagramGeneratorResult: Generated diagram result
        """
        try:
            chain = self.chain()
            result = await chain.ainvoke({
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
        # Get README content from scan result
        readme_content = ""
        scan_result = state["scan_result"]
        
        def find_readme(node: Dict[str, Any]) -> Optional[str]:
            if node["type"] == "file" and node["name"].lower() == "readme.md":
                try:
                    with open(node["path"], encoding="utf-8", errors="ignore") as f:
                        return f.read()
                except Exception as e:
                    logger.error(f"Failed to read README: {str(e)}")
                    return None
            elif node["type"] == "directory":
                for child in node["children"]:
                    result = find_readme(child)
                    if result:
                        return result
            return None
            
        readme_content = find_readme(scan_result) or ""
        
        generator = DiagramGenerator(model=state["model"])
        result = await generator.generate(
            tree=state["tree"],
            content=readme_content
        )
        logger.info("Generated system design diagram")

        return {
            "diagram": result["diagram"],
            "generated_diagram": result
        }

    except Exception as e:
        logger.error(f"Diagram node failed: {str(e)}")
        raise 