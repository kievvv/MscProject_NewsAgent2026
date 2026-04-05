# NewsAgent2025 - 重构版

> 一个专业的、模块化的新闻分析系统，支持加密货币和港股新闻的采集、分析和推送。

## 项目特点

### 🏗️ 清晰的架构设计
- **分层架构**：Model-Repository-Service-API 四层分离
- **设计模式**：Repository、Strategy、Factory、Singleton
- **依赖注入**：松耦合，易于测试和扩展

### 🚀 核心功能
- **双数据源支持**：加密货币新闻（Telegram）+ 港股新闻（AAStocks）
- **智能分析**：关键词提取、相似度分析、趋势分析
- **实时推送**：基于关键词订阅的 Telegram 推送
- **Web 界面**：基于 FastAPI 的现代化 Web UI
- **市场数据**：实时加密货币行情和恐慌指数

### 💡 技术亮点
- **类型安全**：完整的 Type Hints
- **配置管理**：基于 Pydantic-settings 的配置管理
- **错误处理**：统一的异常处理体系
- **代码质量**：遵循 SOLID 原则

## 快速开始

### 环境要求
- Python 3.9+
- SQLite 3
- Redis（可选，用于实时爬虫）

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd NewsAgent2025-Refactored

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入必要的配置
nano .env
```

主要配置项：
```env
# 数据库路径
DATABASE_PATH=data/databases/news_analysis.db
HISTORY_DB_PATH=testdb_history.db
CRYPTO_DB_PATH=testdb_cryptonews.db

# Telegram 配置
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash

# API 配置
API_HOST=127.0.0.1
API_PORT=8000
```

### 初始化数据库

```bash
python scripts/init_db.py
```

### 运行

```bash
# 启动 API 服务
python main.py api

# 运行爬虫
python scripts/run_crawler.py --source crypto

# 交互式模式
python main.py interactive
```

## 项目结构

```
NewsAgent2025-Refactored/
├── config/                     # 配置管理
│   └── settings.py            # 统一配置
│
├── src/                       # 核心业务逻辑
│   ├── core/                  # 核心领域模型
│   │   ├── models.py         # 数据模型
│   │   └── exceptions.py     # 异常定义
│   │
│   ├── data/                  # 数据访问层
│   │   ├── database.py       # 数据库管理
│   │   ├── schema.py         # 表结构
│   │   └── repositories/     # 仓储模式
│   │
│   ├── analyzers/             # 分析器模块
│   │   ├── keyword_extractor.py
│   │   ├── similarity.py
│   │   └── trend.py
│   │
│   ├── services/              # 业务服务层
│   │   ├── news_service.py
│   │   ├── search_service.py
│   │   └── trend_service.py
│   │
│   └── crawlers/              # 爬虫模块
│       ├── crypto_news/
│       └── hkstocks/
│
├── api/                       # API层
│   ├── main.py               # FastAPI应用
│   └── routers/              # 路由模块
│
├── web/                       # Web界面
│   ├── static/               # 静态资源
│   └── templates/            # HTML模板
│
├── scripts/                   # 工具脚本
├── tests/                     # 测试代码
└── docs/                      # 文档
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要端点

#### 新闻相关
```
GET  /api/news/search          # 搜索新闻
GET  /api/news/{id}            # 获取新闻详情
GET  /api/news/recent          # 获取最新新闻
```

#### 趋势分析
```
GET  /api/trend/keyword        # 关键词热度趋势
POST /api/trend/compare        # 对比多个关键词
GET  /api/trend/hot-dates      # 获取最热门日期
```

#### 订阅管理
```
POST   /api/subscription       # 创建订阅
DELETE /api/subscription/{id}  # 取消订阅
GET    /api/subscription/list  # 获取订阅列表
```

## 开发指南

### 添加新数据源

1. 在 `NewsSource` 枚举中添加新数据源
2. 创建对应的 Repository（继承 BaseRepository）
3. 实现爬虫类（继承 BaseCrawler）
4. 在服务层添加相应的业务逻辑

示例：
```python
# 1. 添加枚举
class NewsSource(str, Enum):
    CRYPTO = "crypto"
    HKSTOCKS = "hkstocks"
    NEW_SOURCE = "new_source"  # 新数据源

# 2. 创建Repository
class NewSourceRepository(BaseRepository[News]):
    @property
    def table_name(self) -> str:
        return "new_source_table"
    # 实现其他方法...

# 3. 创建爬虫
class NewSourceCrawler(BaseCrawler):
    async def fetch_news(self) -> List[News]:
        # 实现爬取逻辑
        pass
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_news_repository.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码规范

```bash
# 格式化代码
black src/

# 检查代码
flake8 src/

# 类型检查
mypy src/
```

## 核心模块说明

### 数据模型层（src/core/models.py）
定义了系统中的核心数据结构：
- `News`: 新闻模型
- `Keyword`: 关键词模型
- `Subscription`: 订阅模型
- `TrendAnalysis`: 趋势分析结果

### 数据访问层（src/data/repositories/）
使用 Repository 模式统一数据访问：
- `NewsRepository`: 新闻数据访问
- `KeywordRepository`: 关键词数据访问
- `SubscriptionRepository`: 订阅数据访问

### 服务层（src/services/）
封装业务逻辑：
- `NewsService`: 新闻管理服务
- `SearchService`: 搜索服务
- `TrendService`: 趋势分析服务
- `PushService`: 推送服务

### 分析器层（src/analyzers/）
各种分析功能：
- `KeywordExtractor`: 关键词提取
- `SimilarityAnalyzer`: 相似度分析
- `TrendAnalyzer`: 趋势分析
- `Summarizer`: 摘要生成

## 与原项目对比

| 特性 | 原项目 | 重构项目 |
|------|--------|----------|
| 代码组织 | 15+ 个根目录文件 | 清晰的分层结构 |
| 代码重复 | 严重 | 通过抽象层消除 |
| 配置管理 | 分散 | 统一管理 |
| 数据访问 | 直接 SQL | Repository 模式 |
| 可测试性 | 困难 | 良好（依赖注入） |
| 扩展性 | 差 | 优秀（设计模式） |
| 类型安全 | 无 | 完整的 Type Hints |

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 文档

- [重构方案](REFACTORING_PLAN.md) - 详细的重构计划和架构设计
- [进度报告](PROGRESS.md) - 当前进度和待办事项
- [API 文档](http://localhost:8000/docs) - 自动生成的 API 文档

## 许可证

本项目为学术项目，仅供学习使用。

## 致谢

感谢原项目团队的辛勤工作，本重构项目在原有功能基础上进行了架构优化和代码重组。
