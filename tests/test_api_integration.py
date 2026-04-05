"""
API Integration Tests
测试API集成
"""
import pytest
import requests
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000"
TEST_USER_ID = "integration_test_user"


class TestAPIHealth:
    """测试API健康检查"""

    def test_health_check(self):
        """测试健康检查端点"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_api_status(self):
        """测试API状态端点"""
        response = requests.get(f"{BASE_URL}/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["name"] == "NewsAgent API"


class TestChatAPI:
    """测试聊天API"""

    def test_chat_new_conversation(self):
        """测试新建对话"""
        payload = {
            "message": "你好，这是集成测试",
            "user_id": TEST_USER_ID,
            "conversation_id": None
        }

        response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["response"] is not None
        assert data["conversation_id"] is not None
        assert isinstance(data["conversation_id"], int)

        return data["conversation_id"]

    def test_chat_continue_conversation(self):
        """测试续接对话"""
        # 先创建一个对话
        conv_id = self.test_chat_new_conversation()

        # 续接对话
        payload = {
            "message": "请继续",
            "user_id": TEST_USER_ID,
            "conversation_id": conv_id
        }

        response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["conversation_id"] == conv_id

    def test_chat_missing_message(self):
        """测试缺少消息"""
        payload = {
            "message": "",
            "user_id": TEST_USER_ID
        }

        response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=payload)
        # 应该返回400或者在响应中标记错误
        # 具体取决于实现


class TestConversationsAPI:
    """测试对话API"""

    def test_get_conversations(self):
        """测试获取对话列表"""
        response = requests.get(
            f"{BASE_URL}/api/v1/agent/conversations",
            params={"user_id": TEST_USER_ID, "limit": 10}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "conversations" in data
        assert isinstance(data["conversations"], list)

    def test_get_conversation_detail(self):
        """测试获取对话详情"""
        # 先创建一个对话
        chat_payload = {
            "message": "测试对话详情",
            "user_id": TEST_USER_ID
        }
        chat_response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=chat_payload)
        conv_id = chat_response.json()["conversation_id"]

        # 获取详情
        response = requests.get(f"{BASE_URL}/api/v1/agent/conversations/{conv_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) >= 2  # 至少有用户消息和助手回复

    def test_add_message_to_conversation(self):
        """测试向对话添加消息"""
        # 先创建一个对话
        chat_payload = {
            "message": "初始消息",
            "user_id": TEST_USER_ID
        }
        chat_response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=chat_payload)
        conv_id = chat_response.json()["conversation_id"]

        # 添加消息
        add_payload = {
            "message": "追加消息",
            "user_id": TEST_USER_ID
        }
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/conversations/{conv_id}/messages",
            json=add_payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestSkillsAPI:
    """测试技能API"""

    def test_list_skills(self):
        """测试列出技能"""
        response = requests.get(f"{BASE_URL}/api/v1/agent/skills")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "skills" in data
        assert len(data["skills"]) >= 3

        # 验证技能结构
        for skill in data["skills"]:
            assert "name" in skill
            assert "description" in skill

    def test_get_skill_info(self):
        """测试获取技能信息"""
        response = requests.get(f"{BASE_URL}/api/v1/agent/skills/DailyBriefing")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["skill"]["name"] == "DailyBriefing"

    def test_get_nonexistent_skill(self):
        """测试获取不存在的技能"""
        response = requests.get(f"{BASE_URL}/api/v1/agent/skills/NonExistent")
        assert response.status_code == 404

    def test_execute_daily_briefing(self):
        """测试执行每日简报"""
        payload = {
            "skill_name": "DailyBriefing",
            "user_id": TEST_USER_ID,
            "params": {}
        }

        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/agent/skills/execute", json=payload)
        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 30  # 应该在30秒内完成

        data = response.json()
        assert data["success"] is True
        assert data["skill_name"] == "DailyBriefing"
        assert "final_report" in data
        assert "steps" in data
        assert len(data["steps"]) == 4

    def test_execute_deep_dive(self):
        """测试执行深度分析"""
        payload = {
            "skill_name": "DeepDive",
            "user_id": TEST_USER_ID,
            "params": {"topic": "ethereum"}
        }

        response = requests.post(f"{BASE_URL}/api/v1/agent/skills/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "ethereum" in data["final_report"].lower()

    def test_execute_alpha_hunter(self):
        """测试执行Alpha挖掘"""
        payload = {
            "skill_name": "AlphaHunter",
            "user_id": TEST_USER_ID,
            "params": {}
        }

        response = requests.post(f"{BASE_URL}/api/v1/agent/skills/execute", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["skill_name"] == "AlphaHunter"


class TestUserProfileAPI:
    """测试用户配置API"""

    def test_get_profile(self):
        """测试获取用户配置"""
        response = requests.get(
            f"{BASE_URL}/api/v1/agent/profile",
            params={"user_id": TEST_USER_ID}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "profile" in data
        assert data["profile"]["user_id"] == TEST_USER_ID

    def test_update_profile(self):
        """测试更新用户配置"""
        payload = {
            "preferences": {
                "theme": "light",
                "language": "en-US",
                "notifications": True
            }
        }

        response = requests.put(
            f"{BASE_URL}/api/v1/agent/profile",
            params={"user_id": TEST_USER_ID},
            json=payload
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["profile"]["preferences"]["theme"] == "light"

        # 验证更新
        get_response = requests.get(
            f"{BASE_URL}/api/v1/agent/profile",
            params={"user_id": TEST_USER_ID}
        )
        get_data = get_response.json()
        assert get_data["profile"]["preferences"]["theme"] == "light"


class TestEndToEndWorkflow:
    """测试端到端工作流"""

    def test_complete_workflow(self):
        """测试完整工作流"""
        user_id = f"e2e_test_{int(time.time())}"

        # 1. 创建对话
        chat_payload = {
            "message": "你好，我想了解比特币",
            "user_id": user_id
        }
        chat_response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=chat_payload)
        assert chat_response.status_code == 200
        conv_id = chat_response.json()["conversation_id"]

        # 2. 执行技能
        skill_payload = {
            "skill_name": "DailyBriefing",
            "user_id": user_id,
            "params": {}
        }
        skill_response = requests.post(
            f"{BASE_URL}/api/v1/agent/skills/execute",
            json=skill_payload
        )
        assert skill_response.status_code == 200

        # 3. 继续对话
        continue_payload = {
            "message": "给我详细分析一下",
            "user_id": user_id,
            "conversation_id": conv_id
        }
        continue_response = requests.post(
            f"{BASE_URL}/api/v1/agent/chat",
            json=continue_payload
        )
        assert continue_response.status_code == 200

        # 4. 获取对话历史
        history_response = requests.get(
            f"{BASE_URL}/api/v1/agent/conversations/{conv_id}"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert len(history_data["messages"]) >= 4

        # 5. 更新用户配置
        profile_payload = {
            "preferences": {"favorite_topics": ["bitcoin", "ethereum"]}
        }
        profile_response = requests.put(
            f"{BASE_URL}/api/v1/agent/profile",
            params={"user_id": user_id},
            json=profile_payload
        )
        assert profile_response.status_code == 200


# Pytest configuration
@pytest.fixture(scope="module")
def api_server():
    """确保API服务器运行"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert response.status_code == 200
    except Exception as e:
        pytest.skip(f"API server not running: {e}")


@pytest.mark.integration
class TestAPIPerformance:
    """测试API性能"""

    def test_chat_response_time(self):
        """测试聊天响应时间"""
        payload = {
            "message": "性能测试消息",
            "user_id": "perf_test_user"
        }

        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=payload)
        response_time = time.time() - start_time

        assert response.status_code == 200
        assert response_time < 5.0  # 应该在5秒内响应

    def test_skill_execution_time(self):
        """测试技能执行时间"""
        payload = {
            "skill_name": "DailyBriefing",
            "user_id": "perf_test_user",
            "params": {}
        }

        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/v1/agent/skills/execute", json=payload)
        execution_time = time.time() - start_time

        assert response.status_code == 200
        assert execution_time < 15.0  # 应该在15秒内完成

    def test_concurrent_requests(self):
        """测试并发请求"""
        import concurrent.futures

        def make_request(i):
            payload = {
                "message": f"并发测试消息 {i}",
                "user_id": f"concurrent_user_{i}"
            }
            response = requests.post(f"{BASE_URL}/api/v1/agent/chat", json=payload)
            return response.status_code

        # 发送10个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # 验证所有请求都成功
        assert all(status == 200 for status in results)
