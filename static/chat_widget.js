/**
 * Chat Widget JavaScript
 * 聊天小部件交互逻辑
 */

(function() {
    'use strict';

    // 等待DOM加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatWidget);
    } else {
        initChatWidget();
    }

    function initChatWidget() {
        const widget = document.getElementById('chat-widget');
        const btn = document.getElementById('chat-widget-btn');
        const closeBtn = document.querySelector('.chat-widget-close');
        const messagesContainer = document.getElementById('chat-widget-messages');
        const inputArea = document.getElementById('chat-widget-input');
        const sendBtn = document.getElementById('chat-widget-send');
        const quickActionBtns = document.querySelectorAll('.quick-action-btn');

        if (!widget || !btn) return;

        let currentConversationId = null;
        let isProcessing = false;

        // 切换聊天面板
        btn.addEventListener('click', () => {
            widget.classList.toggle('active');
            if (widget.classList.contains('active')) {
                inputArea.focus();
            }
        });

        // 关闭聊天面板
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                widget.classList.remove('active');
            });
        }

        // 发送消息
        sendBtn.addEventListener('click', sendMessage);

        // Enter发送，Shift+Enter换行
        inputArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // 自动调整输入框高度
        inputArea.addEventListener('input', () => {
            inputArea.style.height = 'auto';
            inputArea.style.height = Math.min(inputArea.scrollHeight, 100) + 'px';
        });

        // 快捷操作按钮
        quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                handleQuickAction(action);
            });
        });

        // 发送消息函数
        async function sendMessage() {
            const message = inputArea.value.trim();
            if (!message || isProcessing) return;

            isProcessing = true;
            sendBtn.disabled = true;

            // 添加用户消息到界面
            addMessage(message, 'user');

            // 清空输入框
            inputArea.value = '';
            inputArea.style.height = 'auto';

            // 显示加载动画
            const loadingEl = addLoadingMessage();

            try {
                // 调用API
                const response = await fetch('/api/v1/agent/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        conversation_id: currentConversationId,
                        user_id: 'widget_user'
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
                    currentConversationId = data.conversation_id;
                }

            } catch (error) {
                console.error('发送消息失败:', error);
                removeLoadingMessage(loadingEl);
                addMessage('抱歉，发送消息时出现错误，请稍后重试。', 'assistant');
            } finally {
                isProcessing = false;
                sendBtn.disabled = false;
                inputArea.focus();
            }
        }

        // 处理快捷操作
        async function handleQuickAction(action) {
            let skillName = '';
            let message = '';

            switch (action) {
                case 'daily':
                    skillName = 'DailyBriefing';
                    message = '生成今日市场简报';
                    break;
                case 'trending':
                    message = '最近有什么热门趋势？';
                    break;
                case 'alpha':
                    skillName = 'AlphaHunter';
                    message = '帮我找找Alpha机会';
                    break;
                default:
                    return;
            }

            if (isProcessing) return;

            isProcessing = true;

            // 添加用户消息
            addMessage(message, 'user');

            // 显示加载动画
            const loadingEl = addLoadingMessage();

            try {
                let response, data;

                if (skillName) {
                    // 执行技能
                    response = await fetch('/api/v1/agent/skills/execute', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            skill_name: skillName,
                            user_id: 'widget_user',
                            params: {}
                        })
                    });

                    if (!response.ok) {
                        throw new Error('技能执行失败');
                    }

                    data = await response.json();

                    // 移除加载动画
                    removeLoadingMessage(loadingEl);

                    // 添加技能报告
                    if (data.final_report) {
                        addSkillReport(data.final_report, skillName);
                    }

                } else {
                    // 普通聊天
                    response = await fetch('/api/v1/agent/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            conversation_id: currentConversationId,
                            user_id: 'widget_user'
                        })
                    });

                    if (!response.ok) {
                        throw new Error('API请求失败');
                    }

                    data = await response.json();

                    // 移除加载动画
                    removeLoadingMessage(loadingEl);

                    // 添加AI回复
                    if (data.response) {
                        addMessage(data.response, 'assistant');
                    }

                    // 保存会话ID
                    if (data.conversation_id) {
                        currentConversationId = data.conversation_id;
                    }
                }

            } catch (error) {
                console.error('快捷操作失败:', error);
                removeLoadingMessage(loadingEl);
                addMessage('抱歉，操作失败，请稍后重试。', 'assistant');
            } finally {
                isProcessing = false;
            }
        }

        // 添加消息到界面
        function addMessage(text, role) {
            const messageEl = document.createElement('div');
            messageEl.className = `chat-message ${role}`;

            const avatarEl = document.createElement('div');
            avatarEl.className = 'message-avatar';
            avatarEl.innerHTML = role === 'assistant'
                ? '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
                : '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';

            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.innerHTML = formatMessage(text);

            messageEl.appendChild(avatarEl);
            messageEl.appendChild(contentEl);

            messagesContainer.appendChild(messageEl);
            scrollToBottom();
        }

        // 添加技能报告
        function addSkillReport(report, skillName) {
            const messageEl = document.createElement('div');
            messageEl.className = 'chat-message assistant';

            const avatarEl = document.createElement('div');
            avatarEl.className = 'message-avatar';
            avatarEl.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>';

            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';

            // 简化报告显示（只显示前300个字符）
            const shortReport = report.length > 300 ? report.substring(0, 300) + '...' : report;

            contentEl.innerHTML = `
                <p><strong>📊 ${skillName} 报告已生成</strong></p>
                <pre style="white-space: pre-wrap; font-size: 12px; margin: 8px 0;">${escapeHtml(shortReport)}</pre>
                <p style="margin-top: 8px;"><a href="/chat" style="color: #667eea;">查看完整报告 →</a></p>
            `;

            messageEl.appendChild(avatarEl);
            messageEl.appendChild(contentEl);

            messagesContainer.appendChild(messageEl);
            scrollToBottom();
        }

        // 添加加载动画
        function addLoadingMessage() {
            const messageEl = document.createElement('div');
            messageEl.className = 'chat-message assistant';

            const avatarEl = document.createElement('div');
            avatarEl.className = 'message-avatar';
            avatarEl.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>';

            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.innerHTML = '<div class="message-loading"><span></span><span></span><span></span></div>';

            messageEl.appendChild(avatarEl);
            messageEl.appendChild(contentEl);

            messagesContainer.appendChild(messageEl);
            scrollToBottom();

            return messageEl;
        }

        // 移除加载动画
        function removeLoadingMessage(loadingEl) {
            if (loadingEl && loadingEl.parentNode) {
                loadingEl.parentNode.removeChild(loadingEl);
            }
        }

        // 格式化消息
        function formatMessage(text) {
            // 简单的换行处理
            return escapeHtml(text).replace(/\n/g, '<br>');
        }

        // HTML转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // 滚动到底部
        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
})();
