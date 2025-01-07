import os
import logging
from typing import Any, Dict, List, Tuple, Optional, Type, Union

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_language_model(
    temperature: float = 0.1,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    初始化语言模型，支持OpenAI模型和其他模型供应商。

    Args:
        temperature: 模型输出的温度，控制随机性。默认为0.0。
        provider: 可选的模型供应商，优先于环境变量。
        model_name: 可选的模型名称，优先于环境变量。
        **kwargs: 其他可选参数，将传递给模型初始化。

    Returns:
        初始化后的语言模型实例。

    Raises:
        ValueError: 当提供的参数无效或缺少必要的配置时抛出。
    """
    provider = (
        provider.lower() if provider else os.getenv("LLM_PROVIDER", "openai").lower()
    )
    model_name = model_name or os.getenv("LLM_MODEL", "gpt-4")

    api_key_env_var = f"OPENAI_API_KEY_{provider.upper()}"
    api_base_env_var = f"OPENAI_API_BASE_{provider.upper()}"

    openai_api_key = os.environ.get(api_key_env_var)
    openai_api_base = os.environ.get(api_base_env_var)

    if not openai_api_key or not openai_api_base:
        raise ValueError(
            f"无法找到 {provider} 的 API 密钥或基础 URL。请检查环境变量设置。"
        )

    model_params = {
        "model": model_name,
        "openai_api_key": openai_api_key,
        "openai_api_base": openai_api_base,
        "temperature": temperature,
        **kwargs,
    }

    return ChatOpenAI(**model_params)


class LanguageModelChain:
    """
    语言模型链，用于处理输入并生成符合指定模式的输出。

    Attributes:
        model_cls: Pydantic 模型类，定义输出的结构。
        parser: JSON 输出解析器。
        prompt_template: 聊天提示模板。
        chain: 完整的处理链。
    """

    def __init__(
        self, model_cls: Type[BaseModel], sys_msg: str, user_msg: str, model: Any
    ):
        """
        初始化 LanguageModelChain 实例。

        Args:
            model_cls: Pydantic 模型类，定义输出的结构。
            sys_msg: 系统消息。
            user_msg: 用户消息。
            model: 语言模型实例。

        Raises:
            ValueError: 当提供的参数无效时抛出。
        """
        if not issubclass(model_cls, BaseModel):
            raise ValueError("model_cls 必须是 Pydantic BaseModel 的子类")
        if not isinstance(sys_msg, str) or not isinstance(user_msg, str):
            raise ValueError("sys_msg 和 user_msg 必须是字符串类型")
        if not callable(model):
            raise ValueError("model 必须是可调用对象")

        self.model_cls = model_cls
        self.parser = JsonOutputParser(pydantic_object=model_cls)

        format_instructions = """
Output your answer as a JSON object that conforms to the following schema:
```json
{schema}
```

Important instructions:
1. Ensure your JSON is valid and properly formatted.
2. Do not include the schema definition in your answer.
3. Only output the data instance that matches the schema.
4. Do not include any explanations or comments within the JSON output.
        """

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", sys_msg + format_instructions),
                ("human", user_msg),
            ]
        ).partial(schema=model_cls.model_json_schema())

        self.chain = self.prompt_template | model | self.parser

    def __call__(self) -> Any:
        """
        调用处理链。

        Returns:
            处理链的输出。
        """
        return self.chain
