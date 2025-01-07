# src/nodes/pattern.py
import logging
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..schemas import State, PatternGeneratorResult
from ..llm_tools import init_language_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
作为一个Git仓库分析专家，你需要帮助用户根据其需求生成合适的文件匹配模式。请遵循以下规则：

1. 根据用户需求选择更合适的方式：
   - 如果用户想要查看特定部分内容，使用 "include" 模式更简单
   - 如果用户想要排除某些内容，使用 "exclude" 模式更合适
   - 选择能用最少规则实现用户需求的方式

2. 生成符合glob模式的匹配规则，可以包含：
   - 文件名匹配：如 *.py, *.js
   - 目录匹配：如 tests/*, docs/*
   - 具体路径匹配：如 src/main.py

3. 规则说明：
   - 只能使用字母、数字、下划线(_)、短横线(-)、点(.)、斜杠(/)、加号(+)和星号(*)
   - 目录匹配需要以 /* 结尾
   - 不要使用 ** 或其他高级glob语法

4. 需要同时考虑：
   - 用户的具体需求
   - 项目的目录结构
   - 常见的开发规范和最佳实践

请务必选择最简单有效的方式来满足用户需求。

Output your answer as a JSON object that conforms to the following schema:
{schema}

Important instructions:
1. Ensure your JSON is valid and properly formatted.
2. Do not include the schema definition in your answer.
3. Only output the data instance that matches the schema.
4. Do not include any explanations or comments within the JSON output.
"""

USER_PROMPT = """
项目目录结构：
{tree}

用户需求：
{query}

请根据用户需求和项目结构生成相应的文件匹配模式。
"""

class PatternGenerator:
    """使用LLM生成文件匹配模式的工具类。"""
    
    def __init__(self):
        self.model = init_language_model(provider="siliconcloud", model_name="Qwen/Qwen2.5-72B-Instruct")
        self.parser = JsonOutputParser(pydantic_object=PatternGeneratorResult)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ]).partial(schema=PatternGeneratorResult.model_json_schema())
        
        self.chain = self.prompt | self.model | self.parser
    
    async def generate(self, tree: str, query: str) -> PatternGeneratorResult:
        """生成文件匹配模式。

        Args:
            tree: 项目目录结构
            query: 用户的自然语言查询

        Returns:
            PatternGeneratorResult: 生成的模式结果
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
    """模式生成节点。"""
    try:
        if not state.get("should_generate_patterns"):
            return {}

        generator = PatternGenerator()
        result = await generator.generate(
            tree=state["tree"],
            query=state["user_query"]
        )
        # result 是一个字典，使用字典访问方式
        logger.info(f"Generated patterns: {result['patterns']}")

        return {
            "pattern_type": result["pattern_type"],
            "patterns": result["patterns"],
            "generated_patterns": result
        }

    except Exception as e:
        logger.error(f"Pattern node failed: {str(e)}")
        raise