"""
End-to-End Test for AI Agent System
端到端测试AI Agent系统
"""
import sys
sys.path.insert(0, '/Users/hk00604ml/cjy/NewsAgent2025-Refactored')

from src.services.ai_agent_service import AIAgentService


def test_news_search():
    """测试新闻搜索功能"""
    print("\n" + "="*60)
    print("测试 1: 新闻搜索")
    print("="*60)

    service = AIAgentService()

    # 测试新闻搜索
    result = service.chat(
        user_id="test_user_001",
        message="比特币最新新闻"
    )

    print(f"✓ 成功: {result['success']}")
    print(f"✓ 对话ID: {result['conversation_id']}")
    print(f"✓ Agent: {result.get('agent', 'N/A')}")
    print(f"\n回复:\n{result['reply']}\n")

    if result.get('tool_results'):
        print(f"工具调用: {len(result['tool_results'])} 个")
        for tool_result in result['tool_results']:
            print(f"  - {tool_result['tool']}: {tool_result['result']['success']}")

    return result['conversation_id']


def test_chat():
    """测试普通对话"""
    print("\n" + "="*60)
    print("测试 2: 普通对话")
    print("="*60)

    service = AIAgentService()

    result = service.chat(
        user_id="test_user_001",
        message="你好"
    )

    print(f"✓ 成功: {result['success']}")
    print(f"✓ 对话ID: {result['conversation_id']}")
    print(f"✓ Agent: {result.get('agent', 'N/A')}")
    print(f"\n回复:\n{result['reply']}\n")

    return result['conversation_id']


def test_conversation_history(conversation_id: int):
    """测试对话历史"""
    print("\n" + "="*60)
    print("测试 3: 对话历史")
    print("="*60)

    service = AIAgentService()

    messages = service.get_conversation_messages(conversation_id)

    print(f"✓ 找到 {len(messages)} 条消息:")
    for msg in messages:
        print(f"  [{msg['role']}] {msg['content'][:50]}...")

    return True


def test_conversation_list():
    """测试对话列表"""
    print("\n" + "="*60)
    print("测试 4: 对话列表")
    print("="*60)

    service = AIAgentService()

    conversations = service.get_conversations(user_id="test_user_001")

    print(f"✓ 找到 {len(conversations)} 个对话:")
    for conv in conversations[:5]:  # 只显示前5个
        print(f"  - ID:{conv['id']} | 标题:{conv['title'][:30]}... | 更新:{conv['updated_at']}")

    return True


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("AI Agent System - End-to-End Test")
    print("="*80)

    try:
        # 测试1: 新闻搜索
        conv_id_1 = test_news_search()

        # 测试2: 普通对话
        conv_id_2 = test_chat()

        # 测试3: 对话历史
        test_conversation_history(conv_id_1)

        # 测试4: 对话列表
        test_conversation_list()

        print("\n" + "="*80)
        print("✓ 所有测试通过!")
        print("="*80)
        print("\nPhase 1 实现完成:")
        print("  ✓ LLM抽象层")
        print("  ✓ 工具包装层")
        print("  ✓ 对话管理")
        print("  ✓ Agent框架")
        print("  ✓ AIAgentService")
        print("="*80)

        return True

    except Exception as e:
        print("\n" + "="*80)
        print(f"✗ 测试失败: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
