#!/usr/bin/env python
"""
启动带AI Agent的Web服务器
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from src.api.app import app

    print("=" * 80)
    print("🚀 启动 NewsAgent2025 with AI Agent")
    print("=" * 80)
    print()
    print("📍 服务地址:")
    print("   • 首页: http://localhost:8000/")
    print("   • API文档: http://localhost:8000/docs")
    print()
    print("🤖 AI Agent功能:")
    print("   • 点击右下角 '🤖 AI助手' 按钮")
    print("   • 或访问 API: POST /api/v1/agent/chat")
    print()
    print("💡 测试命令:")
    print("   • 比特币最新新闻")
    print("   • 市场情绪如何")
    print("   • 分析以太坊趋势")
    print("   • 我关注比特币和以太坊")
    print()
    print("=" * 80)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
