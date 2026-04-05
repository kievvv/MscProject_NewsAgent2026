"""
Phase 5 API Endpoints 测试脚本
测试所有新增的API端点
"""
import requests
import json

BASE_URL = "http://localhost:8000"
USER_ID = "test_user"


def test_health():
    """测试健康检查"""
    print("\n" + "="*80)
    print("测试 1: Health Check")
    print("="*80)

    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✓ Health check passed")
    return True


def test_list_skills():
    """测试获取技能列表"""
    print("\n" + "="*80)
    print("测试 2: List Skills")
    print("="*80)

    response = requests.get(f"{BASE_URL}/api/v1/agent/skills")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    assert response.status_code == 200
    assert data["success"] == True
    assert len(data["skills"]) > 0
    print(f"✓ Found {len(data['skills'])} skills")
    return True


def test_get_skill_info():
    """测试获取技能详情"""
    print("\n" + "="*80)
    print("测试 3: Get Skill Info")
    print("="*80)

    skill_name = "DailyBriefing"
    response = requests.get(f"{BASE_URL}/api/v1/agent/skills/{skill_name}")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    assert response.status_code == 200
    assert data["success"] == True
    assert data["skill"]["name"] == skill_name
    print(f"✓ Skill info retrieved: {skill_name}")
    return True


def test_execute_skill():
    """测试执行技能"""
    print("\n" + "="*80)
    print("测试 4: Execute Skill")
    print("="*80)

    payload = {
        "skill_name": "DailyBriefing",
        "user_id": USER_ID,
        "params": {}
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/agent/skills/execute",
        json=payload
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Skill: {data.get('skill_name')}")
    print(f"Steps: {len(data.get('steps', []))}")

    report_preview = data.get('final_report', '')[:200]
    print(f"Report preview: {report_preview}...")

    assert response.status_code == 200
    assert data["success"] == True
    assert data["skill_name"] == "DailyBriefing"
    print("✓ Skill executed successfully")
    return True


def test_chat():
    """测试聊天功能"""
    print("\n" + "="*80)
    print("测试 5: Chat")
    print("="*80)

    payload = {
        "message": "你好，请介绍一下你自己",
        "user_id": USER_ID,
        "conversation_id": None
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/agent/chat",
        json=payload
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Conversation ID: {data.get('conversation_id')}")
    print(f"Agent: {data.get('agent_name')}")
    print(f"Response: {data.get('response', '')[:100]}...")

    assert response.status_code == 200
    assert data["success"] == True
    assert data["conversation_id"] is not None
    print("✓ Chat successful")

    return data["conversation_id"]


def test_get_conversations(user_id):
    """测试获取对话列表"""
    print("\n" + "="*80)
    print("测试 6: Get Conversations")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/api/v1/agent/conversations",
        params={"user_id": user_id}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Conversations: {len(data.get('conversations', []))}")

    if data.get('conversations'):
        for conv in data['conversations'][:3]:
            print(f"  - ID: {conv.get('id')}, Title: {conv.get('title', '')[:50]}")

    assert response.status_code == 200
    assert data["success"] == True
    print("✓ Conversations retrieved")
    return True


def test_get_conversation_detail(conversation_id):
    """测试获取对话详情"""
    print("\n" + "="*80)
    print("测试 7: Get Conversation Detail")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/api/v1/agent/conversations/{conversation_id}"
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Conversation ID: {data.get('conversation', {}).get('id')}")
    print(f"Messages: {len(data.get('messages', []))}")

    if data.get('messages'):
        for msg in data['messages']:
            role = msg.get('role')
            content = msg.get('content', '')[:50]
            print(f"  - {role}: {content}...")

    assert response.status_code == 200
    assert data["success"] == True
    assert len(data["messages"]) > 0
    print("✓ Conversation detail retrieved")
    return True


def test_get_profile():
    """测试获取用户配置"""
    print("\n" + "="*80)
    print("测试 8: Get User Profile")
    print("="*80)

    response = requests.get(
        f"{BASE_URL}/api/v1/agent/profile",
        params={"user_id": USER_ID}
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"User ID: {data.get('profile', {}).get('user_id')}")
    print(f"Preferences: {data.get('profile', {}).get('preferences')}")

    assert response.status_code == 200
    assert data["success"] == True
    print("✓ User profile retrieved")
    return True


def test_update_profile():
    """测试更新用户配置"""
    print("\n" + "="*80)
    print("测试 9: Update User Profile")
    print("="*80)

    payload = {
        "preferences": {
            "theme": "dark",
            "language": "zh-CN",
            "default_skills": ["DailyBriefing", "AlphaHunter"]
        }
    }

    response = requests.put(
        f"{BASE_URL}/api/v1/agent/profile",
        params={"user_id": USER_ID},
        json=payload
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Updated preferences: {data.get('profile', {}).get('preferences')}")

    assert response.status_code == 200
    assert data["success"] == True
    print("✓ User profile updated")
    return True


def test_add_message_to_conversation(conversation_id):
    """测试向对话添加消息"""
    print("\n" + "="*80)
    print("测试 10: Add Message to Conversation")
    print("="*80)

    payload = {
        "message": "给我分析一下比特币的趋势",
        "user_id": USER_ID
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/agent/conversations/{conversation_id}/messages",
        json=payload
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"Response: {data.get('response', '')[:100]}...")

    assert response.status_code == 200
    assert data["success"] == True
    print("✓ Message added to conversation")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*80)
    print("Phase 5 API Endpoints 测试")
    print("="*80)

    results = []
    conversation_id = None

    try:
        # 基础测试
        results.append(("Health Check", test_health()))

        # Skills API 测试
        results.append(("List Skills", test_list_skills()))
        results.append(("Get Skill Info", test_get_skill_info()))
        results.append(("Execute Skill", test_execute_skill()))

        # Chat API 测试
        conversation_id = test_chat()
        results.append(("Chat", conversation_id is not None))

        # Conversations API 测试
        results.append(("Get Conversations", test_get_conversations(USER_ID)))

        if conversation_id:
            results.append(("Get Conversation Detail", test_get_conversation_detail(conversation_id)))
            results.append(("Add Message", test_add_message_to_conversation(conversation_id)))

        # User Profile API 测试
        results.append(("Get Profile", test_get_profile()))
        results.append(("Update Profile", test_update_profile()))

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

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
        print("\n🎉 所有测试通过！Phase 5 完成！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要修复")


if __name__ == "__main__":
    run_all_tests()
