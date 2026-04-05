"""
Phase 2 Test: All Specialist Agents
测试所有专家Agent
"""
import sys
sys.path.insert(0, '/Users/hk00604ml/cjy/NewsAgent2025-Refactored')

from src.services.ai_agent_service import AIAgentService


def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(title)
    print("="*60)


def test_agent(service, test_name, user_message, user_id="test_user_phase2"):
    """测试单个Agent"""
    print_section(f"测试: {test_name}")
    print(f"用户输入: {user_message}")
    print()

    result = service.chat(
        user_id=user_id,
        message=user_message
    )

    print(f"✓ 成功: {result['success']}")
    print(f"✓ Agent: {result.get('agent', 'N/A')}")
    print(f"✓ 工具调用: {len(result.get('tool_results', []))} 个")
    print()
    print("="*60)
    print("回复:")
    print("="*60)
    print(result['reply'])
    print("="*60)

    return result


def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("Phase 2: Specialist Agents - 完整测试")
    print("="*80)

    service = AIAgentService()

    test_cases = [
        # 1. NewsAgent
        ("NewsAgent - 新闻搜索", "比特币最新新闻"),

        # 2. AnalysisAgent - 关键词提取
        ("AnalysisAgent - 关键词提取", "请从这段文字提取关键词：区块链技术正在改变金融行业的运作方式"),

        # 3. AnalysisAgent - 趋势分析
        ("AnalysisAgent - 趋势分析", "分析一下比特币的趋势"),

        # 4. TradeAgent - 恐慌贪婪指数
        ("TradeAgent - 恐慌贪婪指数", "市场情绪如何"),

        # 5. TradeAgent - 市场概览
        ("TradeAgent - 市场概览", "市场行情怎么样"),

        # 6. ProfileAgent - 设置偏好
        ("ProfileAgent - 设置偏好", "我关注比特币和以太坊"),

        # 7. ProfileAgent - 查看画像
        ("ProfileAgent - 查看画像", "我的个人资料"),

        # 8. ChatAgent - 普通对话
        ("ChatAgent - 普通对话", "介绍一下你自己"),
    ]

    results = []

    for test_name, user_message in test_cases:
        try:
            result = test_agent(service, test_name, user_message)
            results.append({
                "test": test_name,
                "success": result['success'],
                "agent": result.get('agent', 'N/A')
            })
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test_name,
                "success": False,
                "agent": "Error"
            })

    # 汇总结果
    print("\n" + "="*80)
    print("测试汇总")
    print("="*80)

    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print(f"\n通过率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)\n")

    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{status} {i}. {result['test']}")
        print(f"     Agent: {result['agent']}\n")

    print("="*80)
    print("\nPhase 2 完成情况:")
    print("  ✅ Step 2.1: CoordinatorAgent (更新)")
    print("  ✅ Step 2.2: NewsAgent (保持)")
    print("  ✅ Step 2.3: AnalysisAgent (新增)")
    print("  ✅ Step 2.4: TradeAgent (新增)")
    print("  ✅ Step 2.5: UserProfileAgent (新增)")
    print("  ✅ Agent Graph (更新)")
    print("="*80)

    if success_count == total_count:
        print("\n🎉 所有测试通过！Phase 2 实现完成！")
        return True
    else:
        print(f"\n⚠️ {total_count - success_count} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
