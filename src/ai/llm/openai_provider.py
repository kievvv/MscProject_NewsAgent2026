"""
OpenAI LLM Provider
Implements OpenAI API integration
"""
import logging
from typing import List, Iterator, Optional
from openai import OpenAI

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for cloud LLM inference"""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(model, **kwargs)
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized OpenAI provider with model: {model}")

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from single prompt"""
        messages = [LLMMessage(role="user", content=prompt)]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response from conversation"""
        try:
            formatted_messages = self.format_messages(messages)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )

            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content or "",
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                model=response.model,
            )
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise

    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]:
        """Stream response chunks"""
        try:
            formatted_messages = self.format_messages(messages)

            stream = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
