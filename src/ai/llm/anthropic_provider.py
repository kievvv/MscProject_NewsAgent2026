"""
Anthropic LLM Provider
Implements Claude API integration
"""
import logging
from typing import List, Iterator
from anthropic import Anthropic

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider for Claude API"""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, **kwargs)
        self.client = Anthropic(api_key=api_key)
        logger.info(f"Initialized Anthropic provider with model: {model}")

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from single prompt"""
        messages = [LLMMessage(role="user", content=prompt)]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response from conversation"""
        try:
            # Separate system message if present
            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    user_messages.append(msg)

            formatted_messages = self.format_messages(user_messages)

            response = self.client.messages.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_message,
            )

            return LLMResponse(
                content=response.content[0].text if response.content else "",
                finish_reason=response.stop_reason,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                model=response.model,
            )
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            raise

    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]:
        """Stream response chunks"""
        try:
            # Separate system message if present
            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    user_messages.append(msg)

            formatted_messages = self.format_messages(user_messages)

            with self.client.messages.stream(
                model=self.model,
                messages=formatted_messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                system=system_message,
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise
