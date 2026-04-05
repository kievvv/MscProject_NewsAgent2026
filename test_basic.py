"""
基础功能测试脚本
测试重构后的核心功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("NewsAgent2025 重构版 - 基础功能测试")
print("=" * 60)
print()

# 1. 测试配置加载
print("✅ 测试 1: 配置加载")
from config.settings import settings
print(f"   项目根目录: {settings.PROJECT_ROOT}")
print(f"   数据库路径: {settings.DATABASE_PATH}")
print()

# 2. 测试核心模型
print("✅ 测试 2: 核心模型导入")
from src.core.models import NewsSource, News
print(f"   NewsSource.CRYPTO: {NewsSource.CRYPTO}")
print(f"   NewsSource.HKSTOCKS: {NewsSource.HKSTOCKS}")
print()

# 3. 测试数据库
print("✅ 测试 3: 数据库连接")
from src.data.database import get_db_manager
db_manager = get_db_manager()
print(f"   数据库管理器: {db_manager}")
print()

# 4. 测试Repository（直接插入SQL）
print("✅ 测试 4: 数据库操作（直接SQL）")
from src.data.repositories.news import NewsRepository
repo = NewsRepository(source=NewsSource.CRYPTO)
print(f"   Repository表名: {repo.table_name}")
print(f"   Repository DB路径: {repo.db_path}")

# 直接使用SQL插入数据
query = """INSERT INTO messages (channel_id, message_id, text, date)
           VALUES (?, ?, ?, ?)"""
db_manager.execute_update(query, (
    'test_channel',
    '99999',
    '这是一条直接SQL插入的测试新闻',
    '2026-03-20'
), repo.db_path)
print("   ✅ 成功插入测试数据")

# 查询数据
all_news = repo.get_all(limit=5)
print(f"   当前新闻数: {len(all_news)}")
if all_news:
    print(f"   最新一条: {all_news[0].text[:50]}...")
print()

# 5. 测试API导入
print("✅ 测试 5: API模块导入")
from src.api.app import app
print(f"   FastAPI应用: {app}")
print(f"   应用标题: {app.title}")
print()

# 6. 测试爬虫导入
print("✅ 测试 6: 爬虫模块导入")
from src.crawlers.hkstocks import HKStocksScraper
print(f"   港股爬虫: {HKStocksScraper}")
print()

# 7. 统计信息
print("=" * 60)
print("测试完成统计")
print("=" * 60)
print("✅ 所有基础模块导入成功")
print("✅ 数据库连接正常")
print("✅ 可以进行SQL操作")
print()
print("⚠️  注意: 完整功能需要以下依赖:")
print("   - spaCy中文模型: python -m spacy download zh_core_web_sm")
print("   - KeyBERT模型会自动下载（首次使用时）")
print()
print("🚀 下一步:")
print("   - 启动API服务: python src/api/app.py")
print("   - 运行港股爬虫: python scripts/run_hkstocks_crawler.py --max-count 10")
print("   - 查看API文档: http://localhost:8000/docs")
