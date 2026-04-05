# AI Agent 前端测试指南

## 🚀 快速启动

### 1. 确保Ollama正在运行
```bash
# 检查Ollama状态
curl http://localhost:11434/api/tags

# 如果没有运行，启动Ollama
ollama serve
```

### 2. 启动Web服务器
```bash
# 激活虚拟环境
source /Users/hk00604ml/cjy/MscProject-NewsAgent2025/.venv/bin/activate

# 进入项目目录
cd /Users/hk00604ml/cjy/NewsAgent2025-Refactored

# 启动服务器
python run_with_ai.py
```

### 3. 访问网页
打开浏览器，访问：http://localhost:8000/

---

## 🤖 AI Agent 功能

### 在网页上使用

1. **打开聊天窗口**
   - 点击右下角的 `🤖 AI助手` 按钮

2. **开始对话**
   - 在输入框输入消息
   - 或点击快捷问题按钮

3. **试试这些问题**：
   - "比特币最新新闻"
   - "市场情绪如何"
   - "分析以太坊趋势"
   - "从这段文字提取关键词：区块链技术正在改变金融行业"
   - "我关注比特币和以太坊"
   - "我的个人资料"

---

## 🎯 功能演示

### 1. NewsAgent - 新闻搜索
**问**: "比特币最新新闻"
**效果**: 搜索并返回比特币相关新闻

### 2. AnalysisAgent - 关键词提取
**问**: "请从这段文字提取关键词：区块链技术正在改变金融行业"
**效果**: 返回10个关键词及相关度

### 3. AnalysisAgent - 趋势分析
**问**: "分析以太坊的趋势"
**效果**: 显示30天统计数据和走势

### 4. TradeAgent - 市场情绪
**问**: "市场情绪如何"
**效果**: 显示恐慌贪婪指数和解读

### 5. TradeAgent - 市场概览
**问**: "市场行情怎么样"
**效果**: 显示Top 10币种价格和涨跌

### 6. ProfileAgent - 设置偏好
**问**: "我关注比特币和以太坊"
**效果**: 保存用户偏好设置

### 7. ProfileAgent - 查看画像
**问**: "我的个人资料"
**效果**: 显示用户统计和偏好

### 8. ChatAgent - 普通对话
**问**: "你好"或"介绍一下自己"
**效果**: 友好的聊天回复

---

## 🔧 API测试

### 使用curl测试

```bash
# 测试新闻搜索
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "比特币最新新闻",
    "user_id": "test_user"
  }'

# 测试市场情绪
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "市场情绪如何",
    "user_id": "test_user"
  }'

# 测试趋势分析
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "分析比特币的趋势",
    "user_id": "test_user"
  }'

# 查看对话历史
curl http://localhost:8000/api/v1/agent/conversations?user_id=test_user
```

---

## 📊 UI功能

### 聊天窗口特性

- ✅ 漂亮的渐变色设计
- ✅ 毛玻璃效果背景
- ✅ 思考中动画
- ✅ 消息角色区分（用户/助手/系统）
- ✅ 快捷问题按钮
- ✅ 自动滚动到最新消息
- ✅ 回车发送消息
- ✅ 显示当前Agent名称

### 样式特点

- 用户消息：紫色渐变气泡，右对齐
- AI消息：灰色气泡，左对齐
- 系统消息：蓝色气泡，居中（如"思考中..."）

---

## 🐛 常见问题

### 1. 点击按钮没反应
**解决**: 检查浏览器控制台是否有JavaScript错误

### 2. AI回复很慢
**解决**: 正常，本地Ollama模型需要时间推理（3-10秒）

### 3. 显示"连接服务器失败"
**解决**:
- 检查后端是否运行：`http://localhost:8000/api/health`
- 检查Ollama是否运行：`curl http://localhost:11434/api/tags`

### 4. 新闻搜索无结果
**解决**: 数据库中可能没有测试数据，这是正常的

### 5. 市场数据获取失败
**解决**: 外部API可能超时或不可用，稍后再试

---

## 📝 技术细节

### 前端实现
- 纯JavaScript（无框架依赖）
- Fetch API调用后端
- 简洁的CSS样式
- 响应式设计

### 后端实现
- FastAPI路由：`/api/v1/agent/chat`
- LangGraph状态机
- 6个专家Agent
- 7个工具包装

### 数据流
```
用户输入 → 前端JavaScript → POST /api/v1/agent/chat
  → AIAgentService → LangGraph → Coordinator
  → [NewsAgent | AnalysisAgent | TradeAgent | ProfileAgent | ChatAgent]
  → 工具调用 → 生成回复 → 返回前端 → 显示
```

---

## 🎨 自定义

### 修改聊天窗口样式
编辑 `templates_UI/home.html` 中的 `<style>` 部分

### 修改快捷问题
编辑 `templates_UI/home.html` 中的 `.chat-suggestions` 部分

### 添加新的Agent
在 `src/ai/agents/` 中创建新Agent并更新 `graph.py`

---

## 📸 截图指南

### 推荐测试场景

1. **首次打开** - 显示欢迎消息
2. **新闻搜索** - 输入"比特币最新新闻"
3. **市场分析** - 输入"市场情绪如何"
4. **趋势分析** - 输入"分析以太坊趋势"
5. **用户设置** - 输入"我关注比特币"
6. **多轮对话** - 连续提问展示上下文

---

## ✅ 测试清单

- [ ] 聊天窗口可以打开/关闭
- [ ] 快捷问题按钮工作
- [ ] 可以发送消息（输入框 + 发送按钮）
- [ ] 回车发送消息
- [ ] 显示"思考中..."状态
- [ ] AI回复正常显示
- [ ] 消息滚动正常
- [ ] Agent名称显示（系统消息）
- [ ] 新闻搜索功能
- [ ] 趋势分析功能
- [ ] 市场数据功能
- [ ] 用户偏好功能

---

## 🚀 下一步

### 可选改进
1. 添加消息时间戳
2. 支持Markdown渲染
3. 添加代码高亮
4. 支持图片显示
5. 添加对话历史列表
6. 支持多会话切换
7. 添加语音输入
8. 添加数据可视化

---

**准备好了吗？开始测试吧！** 🎉

有任何问题，查看浏览器控制台或后端日志。
