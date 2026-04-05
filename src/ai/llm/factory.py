"""
LLM Provider Factory
Creates the appropriate LLM provider based on configuration
"""
import logging
from typing import Optional
from config.settings import settings
from .base import BaseLLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider

    Args:
        provider: Provider name (ollama, openai, anthropic). If None, uses settings.DEFAULT_LLM_PROVIDER
        model: Model name. If None, uses provider-specific default from settings
        **kwargs: Additional provider-specific parameters

    Returns:
        BaseLLMProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    provider = provider or settings.DEFAULT_LLM_PROVIDER
    provider = provider.lower()

    logger.info(f"Creating LLM provider: {provider}")

    try:
        if provider == "ollama":
            return OllamaProvider(
                model=model or settings.OLLAMA_MODEL,
                base_url=kwargs.get("base_url", settings.OLLAMA_BASE_URL),
                temperature=kwargs.get("temperature", settings.AGENT_TEMPERATURE),
                max_tokens=kwargs.get("max_tokens", settings.AGENT_MAX_TOKENS),
            )

        elif provider == "openai":
            api_key = kwargs.get("api_key", settings.OPENAI_API_KEY)
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            return OpenAIProvider(
                model=model or settings.OPENAI_MODEL,
                api_key=api_key,
                base_url=kwargs.get("base_url", settings.OPENAI_BASE_URL),
                temperature=kwargs.get("temperature", settings.AGENT_TEMPERATURE),
                max_tokens=kwargs.get("max_tokens", settings.AGENT_MAX_TOKENS),
            )

        elif provider == "anthropic":
            api_key = kwargs.get("api_key", settings.ANTHROPIC_API_KEY)
            if not api_key:
                raise ValueError("Anthropic API key not provided")

            return AnthropicProvider(
                model=model or settings.ANTHROPIC_MODEL,
                api_key=api_key,
                temperature=kwargs.get("temperature", settings.AGENT_TEMPERATURE),
                max_tokens=kwargs.get("max_tokens", settings.AGENT_MAX_TOKENS),
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    except Exception as e:
        logger.error(f"Failed to create LLM provider: {e}")
        raise


# Convenience function for getting the default provider
def get_default_provider(**kwargs) -> BaseLLMProvider:
    """Get the default LLM provider from settings"""
    return get_llm_provider(**kwargs)
