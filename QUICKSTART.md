# 🚀 快速开始

## 环境要求
- Python 3.9+
- Redis（可选，用于Telegram爬虫）

## 安装步骤

### 1. 使用uv创建虚拟环境（推荐）
```bash
# 安装uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
cd NewsAgent2025-Refactored
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
uv pip install -r requirements.txt
```

### 2. 或使用传统方式
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 下载spaCy中文模型
```bash
python -m spacy download zh_core_web_sm
python -m spacy download zh_core_web_md  # 可选，用于相似度分析
```

### 4. 配置环境变量（可选）
```bash
cp .env.example .env
# 编辑.env文件，配置Telegram API等
```

## 运行测试

### 1. 测试API服务
```bash
# 启动API服务
python src/api/app.py

# 访问文档
# http://localhost:8000/docs
```

### 2. 测试新闻服务
```python
from src.services import get_news_service
from src.core.models import NewsSource

# 创建服务
service = get_news_service(source=NewsSource.CRYPTO)

# 创建新闻
news = service.create_news(
    title="测试新闻",
    content="这是一条测试新闻，用于验证关键词提取功能。比特币价格上涨。",
)

print(f"新闻ID: {news.id}")
print(f"关键词: {news.keywords}")

# 获取统计
stats = service.get_statistics()
print(f"总新闻数: {stats['total_count']}")
```

### 3. 测试关键词提取
```python
from src.analyzers import get_keyword_extractor

extractor = get_keyword_extractor()
text = "比特币价格今日突破65000美元，市场情绪乐观"
keywords = extractor.extract_keywords(text)

print("关键词:", keywords)
```

### 4. 测试港股爬虫
```bash
python scripts/run_hkstocks_crawler.py --days 1 --max-count 10
```

### 5. 测试Telegram爬虫（需要配置）
```bash
# 先配置.env文件中的TELEGRAM_API_ID和TELEGRAM_API_HASH
python scripts/run_crypto_crawler.py -mode history --limit 10
```

## API端点示例

### 创建新闻
```bash
curl -X POST "http://localhost:8000/api/v1/news/" \
  -H "Content-Type: application/json" \
  -H "X-News-Source: crypto" \
  -d '{
    "title": "比特币突破65000美元",
    "content": "比特币价格今日突破65000美元大关..."
  }'
```

### 搜索新闻
```bash
curl "http://localhost:8000/api/v1/search/keyword?keyword=比特币&limit=20" \
  -H "X-News-Source: crypto"
```

### 趋势分析
```bash
curl -X POST "http://localhost:8000/api/v1/trend/analyze" \
  -H "Content-Type: application/json" \
  -H "X-News-Source: crypto" \
  -d '{
    "keyword": "比特币",
    "granularity": "day"
  }'
```

## 常见问题

### 1. spaCy模型未安装
```bash
python -m spacy download zh_core_web_sm
```

### 2. KeyBERT模型下载慢
设置环境变量使用镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 3. 数据库文件路径
默认路径：`data/databases/news_analysis.db`
可在`.env`中配置：
```
DATABASE_PATH=data/databases/news_analysis.db
```

### 4. Redis连接失败
如果不使用Telegram爬虫，可以忽略Redis错误。
如果需要使用，请确保Redis服务已启动：
```bash
redis-server
```

## 项目结构
```
NewsAgent2025-Refactored/
├── config/              # 配置文件
├── src/
│   ├── core/           # 核心模型
│   ├── data/           # 数据层
│   ├── analyzers/      # 分析器
│   ├── services/       # 服务层
│   ├── api/            # API层
│   └── crawlers/       # 爬虫
├── scripts/            # 启动脚本
├── data/               # 数据目录
└── tests/              # 测试
```

## 下一步

- 查看完整文档：`STAGE1-4_COMPLETE.md`
- API文档：访问 http://localhost:8000/docs
- 查看重构总结：`REFACTORING_REVIEW.md`
