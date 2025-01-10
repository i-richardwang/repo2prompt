import os
import logging
from typing import Any, Optional, Type

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_language_model(
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs: Any,
) -> ChatOpenAI:
    """
    Initialize language model using OpenAI configuration.

    Args:
        temperature: Model output temperature, controls randomness. Default is 0.1.
        api_key: Optional API key. If not provided, uses OPENAI_API_KEY environment variable.
        base_url: Optional API base URL. If not provided, uses OPENAI_API_BASE environment variable.
        model_name: Optional model name. If not provided, uses MODEL_NAME environment variable.
        **kwargs: Additional optional parameters passed to model initialization.

    Returns:
        Initialized language model instance.

    Raises:
        ValueError: When required configuration is missing.
    """
    # Get API key from argument or environment
    openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OpenAI API key is required. Provide it via argument or OPENAI_API_KEY environment variable.")

    # Get other configurations
    openai_api_base = base_url or os.getenv("OPENAI_API_BASE")
    if not openai_api_base:
        raise ValueError("OpenAI API base URL is required. Provide it via argument or OPENAI_API_BASE environment variable.")

    model = model_name or os.getenv("MODEL_NAME", "gpt-4")
    logger.info(f"Using model: {model}")

    model_params = {
        "model": model,
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
        self, model_cls: Type[BaseModel], sys_msg: str, user_msg: str, model: Any
    ):
        """
        Initialize a LanguageModelChain instance.

        Args:
            model_cls: Pydantic model class defining output structure.
            sys_msg: System message.
            user_msg: User message.
            model: Language model instance.

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
