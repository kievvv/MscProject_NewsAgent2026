/**
 * Chat Page JavaScript
 * 聊天页面交互逻辑
 */

(function() {
    'use strict';

    const STATE = {
        currentConversationId: null,
        userId: 'default_user',
        isProcessing: false,
        conversations: []
    };

    const DOM = {
        messagesContainer: document.getElementById('chat-messages'),
        inputArea: document.getElementById('chat-input'),
        sendBtn: document.getElementById('send-btn'),
        newChatBtn: document.getElementById('new-chat-btn'),
        clearChatBtn: document.getElementById('clear-chat-btn'),
        conversationList: document.getElementById('conversation-list'),
        welcomeScreen: document.getElementById('welcome-screen'),
        chatTitle: document.getElementById('chat-title')
    };

    // 初始化
    function init() {
        if (!DOM.messagesContainer) return;

        bindEvents();
        loadConversations();
    }

    // 绑定事件
    function bindEvents() {
        // 发送消息
        DOM.sendBtn?.addEventListener('click', sendMessage);

        // Enter发送，Shift+Enter换行
        DOM.inputArea?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // 自动调整输入框高度
        DOM.inputArea?.addEventListener('input', () => {
            DOM.inputArea.style.height = 'auto';
            DOM.inputArea.style.height = Math.min(DOM.inputArea.scrollHeight, 150) + 'px';
        });

        // 新建对话
        DOM.newChatBtn?.addEventListener('click', startNewConversation);

        // 清空对话
        DOM.clearChatBtn?.addEventListener('click', clearCurrentConversation);

        // 技能卡片点击
        document.querySelectorAll('.skill-card').forEach(card => {
            card.addEventListener('click', () => {
                const skillName = card.dataset.skill;
                executeSkill(skillName);
            });
        });

        // 示例查询点击
        document.querySelectorAll('.example-query').forEach(btn => {
            btn.addEventListener('click', () => {
                const query = btn.textContent.trim();
                DOM.inputArea.value = query;
                sendMessage();
            });
        });
    }

    // 加载对话列表
    async function loadConversations() {
        try {
            const response = await fetch(`/api/v1/agent/conversations?user_id=${STATE.userId}`);
            if (!response.ok) throw new Error('Failed to load conversations');

            const data = await response.json();
            STATE.conversations = data.conversations || [];

            renderConversationList();
        } catch (error) {
            console.error('加载对话列表失败:', error);
        }
    }

    // 渲染对话列表
    function renderConversationList() {
        if (!DOM.conversationList) return;

        if (STATE.conversations.length === 0) {
            DOM.conversationList.innerHTML = `
                <div class="conversation-item-placeholder">
                    <p>暂无对话历史</p>
                    <p class="text-muted">开始新对话来使用AI助手</p>
                </div>
            `;
            return;
        }

        DOM.conversationList.innerHTML = STATE.conversations.map(conv => `
            <div class="conversation-item ${conv.id === STATE.currentConversationId ? 'active' : ''}"
                 data-conversation-id="${conv.id}">
                <div class="conversation-item-title">${escapeHtml(conv.title || '新对话')}</div>
                <div class="conversation-item-time">${formatTime(conv.updated_at || conv.created_at)}</div>
            </div>
        `).join('');

        // 绑定点击事件
        DOM.conversationList.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => {
                const convId = item.dataset.conversationId;
                loadConversation(convId);
            });
        });
    }

    // 加载对话
    async function loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/v1/agent/conversations/${conversationId}`);
            if (!response.ok) throw new Error('Failed to load conversation');

            const data = await response.json();
            STATE.currentConversationId = conversationId;

            // 隐藏欢迎屏幕
            if (DOM.welcomeScreen) {
                DOM.welcomeScreen.style.display = 'none';
            }

            // 清空消息容器
            DOM.messagesContainer.innerHTML = '';

            // 渲染消息
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    addMessage(msg.content, msg.role, false);
                });
            }

            // 更新对话列表选中状态
            renderConversationList();

        } catch (error) {
            console.error('加载对话失败:', error);
            showError('加载对话失败');
        }
    }

    // 开始新对话
    function startNewConversation() {
        STATE.currentConversationId = null;

        // 清空消息
        DOM.messagesContainer.innerHTML = '';

        // 显示欢迎屏幕
        if (DOM.welcomeScreen) {
            DOM.messagesContainer.appendChild(DOM.welcomeScreen);
            DOM.welcomeScreen.style.display = 'block';
        }

        // 更新对话列表
        renderConversationList();

        // 聚焦输入框
        DOM.inputArea?.focus();
    }

    // 清空当前对话
    function clearCurrentConversation() {
        if (!STATE.currentConversationId) {
            startNewConversation();
            return;
        }

        if (confirm('确定要清空当前对话吗？')) {
            startNewConversation();
        }
    }

    // 发送消息
    async function sendMessage() {
        const message = DOM.inputArea.value.trim();
        if (!message || STATE.isProcessing) return;

        STATE.isProcessing = true;
        DOM.sendBtn.disabled = true;

        // 隐藏欢迎屏幕
        if (DOM.welcomeScreen) {
            DOM.welcomeScreen.style.display = 'none';
        }

        // 添加用户消息
        addMessage(message, 'user');

        // 清空输入框
        DOM.inputArea.value = '';
        DOM.inputArea.style.height = 'auto';

        // 显示加载动画
        const loadingEl = addLoadingMessage();

        try {
            const response = await fetch('/api/v1/agent/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: STATE.currentConversationId,
                    user_id: STATE.userId
                })
            });

            if (!response.ok) {
                throw new Error('API请求失败');
            }

            const data = await response.json();

            // 移除加载动画
            removeLoadingMessage(loadingEl);

            // 添加AI回复
            if (data.response) {
                addMessage(data.response, 'assistant');
            }

            // 保存会话ID
            if (data.conversation_id) {
                STATE.currentConversationId = data.conversation_id;
                // 重新加载对话列表
                await loadConversations();
            }

        } catch (error) {
            console.error('发送消息失败:', error);
            removeLoadingMessage(loadingEl);
            showError('抱歉，发送消息时出现错误，请稍后重试。');
        } finally {
            STATE.isProcessing = false;
            DOM.sendBtn.disabled = false;
            DOM.inputArea?.focus();
        }
    }

    // 执行技能
    async function executeSkill(skillName) {
        if (STATE.isProcessing) return;

        STATE.isProcessing = true;

        // 隐藏欢迎屏幕
        if (DOM.welcomeScreen) {
            DOM.welcomeScreen.style.display = 'none';
        }

        // 添加用户消息
        const skillMessages = {
            'DailyBriefing': '生成今日市场简报',
            'DeepDive': '进行深度话题分析',
            'AlphaHunter': '挖掘Alpha机会'
        };
        addMessage(skillMessages[skillName] || `执行${skillName}技能`, 'user');

        // 显示加载动画
        const loadingEl = addLoadingMessage();

        try {
            const response = await fetch('/api/v1/agent/skills/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    skill_name: skillName,
                    user_id: STATE.userId,
                    params: skillName === 'DeepDive' ? { topic: 'bitcoin' } : {}
                })
            });

            if (!response.ok) {
                throw new Error('技能执行失败');
            }

            const data = await response.json();

            // 移除加载动画
            removeLoadingMessage(loadingEl);

            // 添加技能报告
            if (data.final_report) {
                addSkillReport(data.final_report, skillName);
            }

        } catch (error) {
            console.error('技能执行失败:', error);
            removeLoadingMessage(loadingEl);
            showError('技能执行失败，请稍后重试。');
        } finally {
            STATE.isProcessing = false;
        }
    }

    // 添加消息到界面
    function addMessage(text, role, scroll = true) {
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${role}`;

        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        messageEl.innerHTML = `
            <div class="message-avatar">
                ${role === 'assistant'
                    ? '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
                    : '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'}
            </div>
            <div class="message-content">
                <div class="message-bubble">${formatMessage(text)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;

        DOM.messagesContainer.appendChild(messageEl);
        if (scroll) scrollToBottom();
    }

    // 添加技能报告
    function addSkillReport(report, skillName) {
        const messageEl = document.createElement('div');
        messageEl.className = 'chat-message assistant';

        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        const skillIcons = {
            'DailyBriefing': '📊',
            'DeepDive': '🔍',
            'AlphaHunter': '🎯'
        };

        messageEl.innerHTML = `
            <div class="message-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
            </div>
            <div class="message-content">
                <div class="skill-report-card">
                    <div class="skill-report-header">
                        <div class="skill-report-title">
                            <span>${skillIcons[skillName] || '📋'}</span>
                            ${skillName} 报告
                        </div>
                    </div>
                    <div class="skill-report-content">${escapeHtml(report)}</div>
                </div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;

        DOM.messagesContainer.appendChild(messageEl);
        scrollToBottom();
    }

    // 添加加载动画
    function addLoadingMessage() {
        const messageEl = document.createElement('div');
        messageEl.className = 'chat-message assistant';

        messageEl.innerHTML = `
            <div class="message-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="message-loading"><span></span><span></span><span></span></div>
                </div>
            </div>
        `;

        DOM.messagesContainer.appendChild(messageEl);
        scrollToBottom();

        return messageEl;
    }

    // 移除加载动画
    function removeLoadingMessage(loadingEl) {
        if (loadingEl && loadingEl.parentNode) {
            loadingEl.parentNode.removeChild(loadingEl);
        }
    }

    // 显示错误
    function showError(message) {
        addMessage(message, 'assistant');
    }

    // 格式化消息
    function formatMessage(text) {
        return escapeHtml(text).replace(/\n/g, '<br>');
    }

    // HTML转义
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // 格式化时间
    function formatTime(dateStr) {
        if (!dateStr) return '';

        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return '刚刚';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;

        return date.toLocaleDateString('zh-CN');
    }

    // 滚动到底部
    function scrollToBottom() {
        DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
