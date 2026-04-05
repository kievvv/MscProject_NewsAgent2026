"""
Quick test script for LLM providers
"""
import sys
sys.path.insert(0, '/Users/hk00604ml/cjy/NewsAgent2025-Refactored')

from src.ai.llm.factory import get_llm_provider
from src.ai.llm.base import LLMMessage


def test_ollama():
    """Test Ollama provider"""
    print("Testing Ollama provider...")
    print("-" * 60)

    try:
        provider = get_llm_provider(provider="ollama")
        print(f"✓ Provider created: {provider.__class__.__name__}")
        print(f"  Model: {provider.model}")
        print(f"  Base URL: {provider.base_url}")

        # Test simple generation
        print("\nSending test message...")
        messages = [
            LLMMessage(role="user", content="Say 'Hello from Ollama!' in one sentence")
        ]

        response = provider.chat(messages)
        print(f"✓ Response received:")
        print(f"  Content: {response.content[:100]}...")
        print(f"  Model: {response.model}")
        print(f"  Usage: {response.usage}")

        print("\n✓ Ollama test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Ollama test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("LLM Provider Test")
    print("=" * 60)
    print()

    # Test Ollama (requires ollama running locally)
    success = test_ollama()

    print()
    print("=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Make sure Ollama is running:")
        print("  $ ollama serve")
        print("  $ ollama pull llama3.2:3b")
    print("=" * 60)
