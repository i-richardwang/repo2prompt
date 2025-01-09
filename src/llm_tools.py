import os
import logging
from typing import Any, Dict, List, Tuple, Optional, Type, Union

from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from .schemas import LLMConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_language_model(
    temperature: float = 0.1,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    llm_config: Optional[LLMConfig] = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    Initialize language model, supporting OpenAI and other model providers.

    Args:
        temperature: Model output temperature, controls randomness. Default is 0.0.
        provider: Optional model provider, overrides environment variable.
        model_name: Optional model name, overrides environment variable.
        llm_config: Optional custom LLM configuration from request.
        **kwargs: Additional optional parameters passed to model initialization.

    Returns:
        Initialized language model instance.

    Raises:
        ValueError: When provided parameters are invalid or required configuration is missing.
    """
    if llm_config:
        # Use user-provided configuration
        logger.info(f"Using custom LLM configuration with model: {llm_config.model_name}")
        model_params = {
            "model": llm_config.model_name,
            "openai_api_key": llm_config.api_key,
            "openai_api_base": llm_config.api_base,
            "temperature": temperature,
            **kwargs,
        }
    else:
        # Use environment variable configuration
        provider = (
            provider.lower() if provider else os.getenv("LLM_PROVIDER", "openai").lower()
        )
        model_name = model_name or os.getenv("LLM_MODEL", "gpt-4")
        logger.info(f"Using environment configuration with provider: {provider}, model: {model_name}")

        api_key_env_var = f"OPENAI_API_KEY_{provider.upper()}"
        api_base_env_var = f"OPENAI_API_BASE_{provider.upper()}"

        openai_api_key = os.environ.get(api_key_env_var)
        openai_api_base = os.environ.get(api_base_env_var)

        if not openai_api_key or not openai_api_base:
            raise ValueError(
                f"Could not find API key or base URL for {provider}. Please check environment variables."
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
    Language model chain for processing input and generating output conforming to specified schema.

    Attributes:
        model_cls: Pydantic model class defining output structure.
        parser: JSON output parser.
        prompt_template: Chat prompt template.
        chain: Complete processing chain.
    """

    def __init__(
        self, model_cls: Type[BaseModel], sys_msg: str, user_msg: str, model: Any, llm_config: Optional[LLMConfig] = None
    ):
        """
        Initialize a LanguageModelChain instance.

        Args:
            model_cls: Pydantic model class defining output structure.
            sys_msg: System message.
            user_msg: User message.
            model: Language model instance.
            llm_config: Optional custom LLM configuration.

        Raises:
            ValueError: When provided parameters are invalid.
        """
        if not issubclass(model_cls, BaseModel):
            raise ValueError("model_cls must be a subclass of Pydantic BaseModel")
        if not isinstance(sys_msg, str) or not isinstance(user_msg, str):
            raise ValueError("sys_msg and user_msg must be strings")
        if not callable(model):
            raise ValueError("model must be a callable object")

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
        Call the processing chain.

        Returns:
            Output from the processing chain.
        """
        return self.chain
