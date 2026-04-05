"""
Base LLM Provider Interface
Abstract base class for all LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Standard message format"""
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Standard response format"""
    content: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""

    def __init__(self, model: str, temperature: float = 0.7, max_tokens: int = 2000, **kwargs):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_params = kwargs

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate a response from a single prompt

        Args:
            prompt: Input prompt string
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    def chat(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """
        Generate a response from a conversation

        Args:
            messages: List of LLMMessage objects
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]:
        """
        Stream response chunks

        Args:
            messages: List of LLMMessage objects
            **kwargs: Additional generation parameters

        Yields:
            Response chunks as strings
        """
        pass

    def format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        """Convert LLMMessage objects to provider-specific format"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {})
            }
            for msg in messages
        ]
