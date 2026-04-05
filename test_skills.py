"""
Test script for Phase 3 Skill System
测试所有三个技能：DailyBriefing, DeepDive, AlphaHunter
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai.skills.executor import get_skill_executor


def test_daily_briefing():
    """测试 DailyBriefing 技能"""
    print("\n" + "="*80)
    print("测试 1: DailyBriefing Skill")
    print("="*80)

    executor = get_skill_executor()

    try:
        result = executor.execute_skill('DailyBriefing')

        print(f"\n✓ 技能执行成功: {result.success}")
        print(f"✓ 开始时间: {result.started_at}")
        print(f"✓ 完成时间: {result.completed_at}")
        print(f"✓ 执行步骤数: {len(result.steps)}")

        for i, step in enumerate(result.steps, 1):
            status = "✓" if step.completed else "✗"
            print(f"  {status} 步骤 {i}: {step.name} - {step.description}")
            if step.error:
                print(f"      错误: {step.error}")

        print(f"\n生成的报告:")
        print("-"*80)
        print(result.final_report[:500] + "..." if len(result.final_report) > 500 else result.final_report)
        print("-"*80)

        return result.success

    except Exception as e:
        print(f"\n✗ 技能执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deep_dive():
    """测试 DeepDive 技能"""
    print("\n" + "="*80)
    print("测试 2: DeepDive Skill")
    print("="*80)

    executor = get_skill_executor()

    try:
        # 测试话题：Bitcoin
        params = {'topic': 'bitcoin'}
        result = executor.execute_skill('DeepDive', params)

        print(f"\n✓ 技能执行成功: {result.success}")
        print(f"✓ 分析话题: {params['topic']}")
        print(f"✓ 开始时间: {result.started_at}")
        print(f"✓ 完成时间: {result.completed_at}")
        print(f"✓ 执行步骤数: {len(result.steps)}")

        for i, step in enumerate(result.steps, 1):
            status = "✓" if step.completed else "✗"
            print(f"  {status} 步骤 {i}: {step.name} - {step.description}")
            if step.error:
                print(f"      错误: {step.error}")

        print(f"\n生成的报告:")
        print("-"*80)
        print(result.final_report[:500] + "..." if len(result.final_report) > 500 else result.final_report)
        print("-"*80)

        return result.success

    except Exception as e:
        print(f"\n✗ 技能执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alpha_hunter():
    """测试 AlphaHunter 技能"""
    print("\n" + "="*80)
    print("测试 3: AlphaHunter Skill")
    print("="*80)

    executor = get_skill_executor()

    try:
        result = executor.execute_skill('AlphaHunter')

        print(f"\n✓ 技能执行成功: {result.success}")
        print(f"✓ 开始时间: {result.started_at}")
        print(f"✓ 完成时间: {result.completed_at}")
        print(f"✓ 执行步骤数: {len(result.steps)}")

        for i, step in enumerate(result.steps, 1):
            status = "✓" if step.completed else "✗"
            print(f"  {status} 步骤 {i}: {step.name} - {step.description}")
            if step.error:
                print(f"      错误: {step.error}")

        print(f"\n生成的报告:")
        print("-"*80)
        print(result.final_report[:500] + "..." if len(result.final_report) > 500 else result.final_report)
        print("-"*80)

        return result.success

    except Exception as e:
        print(f"\n✗ 技能执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_skill_list():
    """测试技能列表"""
    print("\n" + "="*80)
    print("测试 0: 列出所有可用技能")
    print("="*80)

    executor = get_skill_executor()
    skills = executor.list_skills()

    print(f"\n找到 {len(skills)} 个技能:")
    for name, description in skills.items():
        print(f"  • {name}: {description}")

    return len(skills) == 3


if __name__ == "__main__":
    print("\n")
    print("="*80)
    print("Phase 3 Skill System 测试")
    print("="*80)

    results = []

    # 测试技能列表
    results.append(("技能列表", test_skill_list()))

    # 测试三个技能
    results.append(("DailyBriefing", test_daily_briefing()))
    results.append(("DeepDive", test_deep_dive()))
    results.append(("AlphaHunter", test_alpha_hunter()))

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print(f"\n总计: {passed}/{total} 测试通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 所有测试通过！Phase 3 完成！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要修复")
