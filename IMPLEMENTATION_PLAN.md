# 分步实施计划

## 总览

```
阶段一: 分析器层 (2-3天)    ████████░░░░░░░░ 50%
阶段二: 服务层 (2-3天)      ████░░░░░░░░░░░░ 25%
阶段三: API层 (2-3天)       ██░░░░░░░░░░░░░░ 12%
阶段四: 爬虫层 (2天)        ██░░░░░░░░░░░░░░ 12%
阶段五: 完善与测试 (2天)    ░░░░░░░░░░░░░░░░  1%
```

## 阶段一：分析器层 (优先级 P0)

### 目标
将原项目的分析功能重构为独立的分析器模块

### 任务清单

#### Step 1.1: 关键词提取器 ⭐⭐⭐⭐⭐
**文件**: `src/analyzers/keyword_extractor.py`
**参考**: `src/crypto_analysis/crypto_analyzer.py`
**功能**:
- KeyBERT 关键词提取
- 币种识别（crypto）
- 行业识别（hkstocks）
- 批量提取优化

**预计时间**: 2小时
**代码量**: ~300行

#### Step 1.2: 相似度分析器 ⭐⭐⭐⭐⭐
**文件**: `src/analyzers/similarity.py`
**参考**: `src/crypto_analysis/similarity_analyzer.py`
**功能**:
- 关键词相似度计算
- 币种/行业统计
- 支持双数据源
- 相似词推荐

**预计时间**: 2小时
**代码量**: ~400行

#### Step 1.3: 摘要生成器 ⭐⭐⭐⭐
**文件**: `src/analyzers/summarizer.py`
**参考**: `src/crypto_analysis/summarizer.py`, `news_search.py` (generate_summary)
**功能**:
- mT5 模型摘要生成
- 多语言支持
- 摘要缓存
- 简单摘要fallback

**预计时间**: 1.5小时
**代码量**: ~200行

#### Step 1.4: 趋势分析器 ⭐⭐⭐⭐
**文件**: `src/analyzers/trend.py`
**参考**: `src/trend_analysis/trend_analyzer.py`, `src/trend_analysis/advanced_trend_analyzer.py`
**功能**:
- 热度趋势分析
- 异常检测
- 关联词分析
- 可视化支持

**预计时间**: 2小时
**代码量**: ~500行

**阶段一总计**: ~7.5小时, ~1400行代码

---

## 阶段二：服务层 (优先级 P0)

### 目标
封装业务逻辑，整合 Repository 和 Analyzer

### 任务清单

#### Step 2.1: 新闻服务 ⭐⭐⭐⭐⭐
**文件**: `src/services/news_service.py`
**功能**:
- 新闻创建（含关键词提取）
- 新闻更新
- 新闻查询（封装Repository）
- 摘要生成
- 批量处理

**预计时间**: 2小时
**代码量**: ~300行

#### Step 2.2: 搜索服务 ⭐⭐⭐⭐⭐
**文件**: `src/services/search_service.py`
**参考**: `news_search.py`, `hkstocks_search.py`
**功能**:
- 统一搜索接口（双数据源）
- TF-IDF 相似度搜索
- 关键词搜索
- 搜索结果排序

**预计时间**: 2.5小时
**代码量**: ~400行

#### Step 2.3: 趋势服务 ⭐⭐⭐⭐
**文件**: `src/services/trend_service.py`
**功能**:
- 趋势分析（调用TrendAnalyzer）
- 趋势缓存管理
- 热门关键词统计
- 趋势对比

**预计时间**: 1.5小时
**代码量**: ~250行

#### Step 2.4: 推送服务 ⭐⭐⭐⭐
**文件**: `src/services/push_service.py`
**参考**: `src/push_system/push_manager.py`
**功能**:
- 订阅管理
- 新闻匹配
- Telegram推送
- 推送历史记录

**预计时间**: 2小时
**代码量**: ~300行

#### Step 2.5: 市场数据服务 ⭐⭐⭐
**文件**: `src/services/market_service.py`
**参考**: `web_app.py` (fetch_crypto_market_board, fetch_fear_greed_index)
**功能**:
- CoinGecko市场数据
- 恐慌贪婪指数
- 数据缓存
- 币种统计

**预计时间**: 1.5小时
**代码量**: ~250行

**阶段二总计**: ~9.5小时, ~1500行代码

---

## 阶段三：API层 (优先级 P1)

### 目标
重构 FastAPI 应用，拆分 web_app.py 的 950 行代码

### 任务清单

#### Step 3.1: FastAPI 应用入口 ⭐⭐⭐⭐⭐
**文件**: `api/main.py`
**参考**: `web_app.py`
**功能**:
- FastAPI 应用初始化
- 路由注册
- 中间件配置
- 错误处理
- CORS 配置

**预计时间**: 1.5小时
**代码量**: ~150行

#### Step 3.2: 依赖注入 ⭐⭐⭐⭐
**文件**: `api/dependencies.py`
**功能**:
- Service 依赖注入
- Repository 依赖注入
- 配置依赖注入
- 认证依赖（预留）

**预计时间**: 1小时
**代码量**: ~100行

#### Step 3.3: 新闻路由 ⭐⭐⭐⭐⭐
**文件**: `api/routers/news.py`
**参考**: `web_app.py` (news相关接口)
**功能**:
- GET /api/news/search
- GET /api/news/recent
- GET /api/news/{id}
- GET /api/news/statistics

**预计时间**: 1.5小时
**代码量**: ~200行

#### Step 3.4: 搜索路由 ⭐⭐⭐⭐⭐
**文件**: `api/routers/search.py`
**参考**: `web_app.py` (search相关)
**功能**:
- GET /search (Web页面)
- POST /search_action
- 关键词趋势图表
- TradingView集成

**预计时间**: 2小时
**代码量**: ~250行

#### Step 3.5: 趋势分析路由 ⭐⭐⭐⭐
**文件**: `api/routers/trend.py`
**参考**: `web_app.py` (trend相关)
**功能**:
- GET /api/trend/keyword
- POST /api/trend/compare
- GET /api/trend/hot-dates
- GET /api/trend/visualize

**预计时间**: 1.5小时
**代码量**: ~200行

#### Step 3.6: 分析器路由 ⭐⭐⭐⭐
**文件**: `api/routers/analyzer.py`
**参考**: `web_app.py` (analyzer相关)
**功能**:
- GET /analyzer (页面)
- POST /api/analyze
- POST /api/query-keyword
- GET /api/channels

**预计时间**: 1.5小时
**代码量**: ~200行

#### Step 3.7: 订阅路由 ⭐⭐⭐
**文件**: `api/routers/subscription.py`
**功能**:
- POST /api/subscription
- DELETE /api/subscription/{id}
- GET /api/subscription/list/{user_id}

**预计时间**: 1小时
**代码量**: ~150行

#### Step 3.8: 首页路由 ⭐⭐⭐⭐
**文件**: `api/routers/home.py`
**参考**: `web_app.py` (root, dashboard)
**功能**:
- GET / (首页)
- GET /api/dashboard
- 市场数据展示
- 热门新闻

**预计时间**: 1小时
**代码量**: ~150行

**阶段三总计**: ~11小时, ~1400行代码

---

## 阶段四：爬虫层 (优先级 P1)

### 目标
重构爬虫模块，保持功能不变

### 任务清单

#### Step 4.1: 爬虫基类 ⭐⭐⭐⭐
**文件**: `src/crawlers/base.py`
**功能**:
- 抽象爬虫接口
- 通用爬虫逻辑
- 错误处理
- 日志记录

**预计时间**: 1小时
**代码量**: ~150行

#### Step 4.2: Telegram爬虫 ⭐⭐⭐⭐⭐
**文件**:
- `src/crawlers/crypto_news/producer.py`
- `src/crawlers/crypto_news/consumer.py`
- `src/crawlers/crypto_news/analyzer.py`

**参考**: `src/crawler/crpyto_news/`
**功能**:
- Telethon 生产者
- Redis 消费者
- 币种分析
- 实时推送

**预计时间**: 3小时
**代码量**: ~500行

#### Step 4.3: 港股爬虫 ⭐⭐⭐⭐
**文件**:
- `src/crawlers/hkstocks/scraper.py`
- `src/crawlers/hkstocks/analyzer.py`

**参考**: `src/crawler/HKStocks/`
**功能**:
- AAStocks 爬虫
- Selenium 支持
- 行业分析
- 去重处理

**预计时间**: 2小时
**代码量**: ~400行

**阶段四总计**: ~6小时, ~1050行代码

---

## 阶段五：工具与完善 (优先级 P2)

### 任务清单

#### Step 5.1: 工具模块 ⭐⭐⭐
**文件**:
- `src/utils/text_processing.py` - 文本处理
- `src/utils/date_utils.py` - 日期工具
- `src/utils/logger.py` - 日志配置

**预计时间**: 2小时
**代码量**: ~300行

#### Step 5.2: 脚本工具 ⭐⭐⭐
**文件**:
- `scripts/init_db.py` - 数据库初始化
- `scripts/run_crawler.py` - 运行爬虫
- `scripts/migrate.py` - 数据迁移
- `main.py` - CLI入口

**预计时间**: 2小时
**代码量**: ~400行

#### Step 5.3: 测试用例 ⭐⭐
**文件**:
- `tests/unit/` - 单元测试
- `tests/integration/` - 集成测试
- `tests/conftest.py` - pytest配置

**预计时间**: 4小时
**代码量**: ~800行

#### Step 5.4: 文档完善 ⭐⭐
**文件**:
- API文档
- 开发者文档
- 部署文档

**预计时间**: 2小时

**阶段五总计**: ~10小时, ~1500行代码

---

## 总体统计

```
总预计时间: 44小时 (约5-6个工作日)
总代码量: ~6,850行

已完成: ~2,500行 (数据层)
待完成: ~6,850行 (业务层)
总计: ~9,350行

原项目主要代码: ~8,000行 (估算)
重构后: ~9,350行 (+文档和测试)
代码质量提升: 显著 (类型安全、模块化、可测试)
```

---

## 分步实施建议

### 第一天 (8小时)
✅ **上午**: 阶段一 Step 1.1-1.2 (关键词提取器 + 相似度分析器) - 4小时
✅ **下午**: 阶段一 Step 1.3-1.4 (摘要生成器 + 趋势分析器) - 4小时

### 第二天 (8小时)
✅ **上午**: 阶段二 Step 2.1-2.2 (新闻服务 + 搜索服务) - 4.5小时
✅ **下午**: 阶段二 Step 2.3-2.5 (趋势服务 + 推送服务 + 市场服务) - 3.5小时

### 第三天 (8小时)
✅ **上午**: 阶段三 Step 3.1-3.3 (FastAPI入口 + 依赖注入 + 新闻路由) - 4小时
✅ **下午**: 阶段三 Step 3.4-3.5 (搜索路由 + 趋势路由) - 3.5小时

### 第四天 (8小时)
✅ **上午**: 阶段三 Step 3.6-3.8 (分析器路由 + 订阅路由 + 首页路由) - 3.5小时
✅ **下午**: 阶段四 Step 4.1-4.2 (爬虫基类 + Telegram爬虫) - 4小时

### 第五天 (8小时)
✅ **上午**: 阶段四 Step 4.3 (港股爬虫) - 2小时
✅ **下午**: 阶段五 Step 5.1-5.2 (工具模块 + 脚本) - 4小时
✅ **测试与调试**: 2小时

### 第六天 (4小时) - 可选
✅ **测试与文档**: 阶段五 Step 5.3-5.4

---

## 优先级说明

⭐⭐⭐⭐⭐ - 核心功能，必须实现
⭐⭐⭐⭐ - 重要功能，优先实现
⭐⭐⭐ - 一般功能，可以推迟
⭐⭐ - 锦上添花，时间允许再做

---

## 立即开始：阶段一 Step 1.1

现在开始实现第一个模块：**关键词提取器**

继续吗？
