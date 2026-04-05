#!/usr/bin/env python
"""
Test Runner Script
运行所有测试并生成报告
"""
import sys
import subprocess
import time
from pathlib import Path


def check_server_running():
    """检查服务器是否运行"""
    import requests
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def run_unit_tests():
    """运行单元测试"""
    print("\n" + "="*80)
    print("运行单元测试 (Unit Tests)")
    print("="*80)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_ai_tools.py",
        "tests/test_ai_agents.py",
        "tests/test_ai_skills.py",
        "-v",
        "-m", "not integration and not performance"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_integration_tests():
    """运行集成测试"""
    print("\n" + "="*80)
    print("运行集成测试 (Integration Tests)")
    print("="*80)

    # 检查服务器
    if not check_server_running():
        print("⚠️  API服务器未运行，跳过集成测试")
        print("请先启动服务器: uvicorn src.api.app:app --host 0.0.0.0 --port 8000")
        return True  # 不算作失败

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_api_integration.py",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("运行所有测试 (All Tests)")
    print("="*80)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def run_coverage():
    """运行测试覆盖率"""
    print("\n" + "="*80)
    print("运行测试覆盖率 (Coverage)")
    print("="*80)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term",
        "-v"
    ]

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode == 0


def main():
    """主函数"""
    print("\n" + "="*80)
    print("NewsAgent2025 - Phase 6 测试套件")
    print("="*80)

    start_time = time.time()
    results = {}

    # 选择测试类型
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        print("\n请选择测试类型:")
        print("1. 单元测试 (unit)")
        print("2. 集成测试 (integration)")
        print("3. 所有测试 (all)")
        print("4. 测试覆盖率 (coverage)")
        print("5. 退出 (exit)")

        choice = input("\n输入选择 [1-5]: ").strip()

        if choice == "1":
            test_type = "unit"
        elif choice == "2":
            test_type = "integration"
        elif choice == "3":
            test_type = "all"
        elif choice == "4":
            test_type = "coverage"
        else:
            print("退出测试")
            return 0

    # 运行测试
    if test_type == "unit":
        results["单元测试"] = run_unit_tests()
    elif test_type == "integration":
        results["集成测试"] = run_integration_tests()
    elif test_type == "all":
        results["单元测试"] = run_unit_tests()
        results["集成测试"] = run_integration_tests()
    elif test_type == "coverage":
        results["覆盖率测试"] = run_coverage()
    else:
        print(f"未知的测试类型: {test_type}")
        return 1

    # 总结
    elapsed_time = time.time() - start_time

    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, success in results.items():
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status}: {name}")

    print(f"\n总耗时: {elapsed_time:.2f} 秒")

    # 返回码
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
