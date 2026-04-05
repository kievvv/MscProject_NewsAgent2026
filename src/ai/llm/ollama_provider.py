"""
Ollama LLM Provider
Implements local Ollama model integration
"""
import logging
from typing import List, Iterator
import ollama

from .base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLM inference"""

    def __init__(self, model: str, base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(model, **kwargs)
        self.base_url = base_url
        self.client = ollama.Client(host=base_url)
        logger.info(f"Initialized Ollama provider with model: {model}, base_url: {base_url}")

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate response from single prompt"""
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                }
            )

            return LLMResponse(
                content=response.get("response", ""),
                finish_reason=response.get("done_reason"),
                usage={
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
                },
                model=self.model,
            )
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Generate response from conversation"""
        try:
            formatted_messages = self.format_messages(messages)

            response = self.client.chat(
                model=self.model,
                messages=formatted_messages,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                }
            )

            message = response.get("message", {})

            return LLMResponse(
                content=message.get("content", ""),
                finish_reason=response.get("done_reason"),
                usage={
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                    "total_tokens": response.get("prompt_eval_count", 0) + response.get("eval_count", 0),
                },
                model=self.model,
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]:
        """Stream response chunks"""
        try:
            formatted_messages = self.format_messages(messages)

            stream = self.client.chat(
                model=self.model,
                messages=formatted_messages,
                stream=True,
                options={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens),
                }
            )

            for chunk in stream:
                message = chunk.get("message", {})
                content = message.get("content", "")
                if content:
                    yield content

        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise
