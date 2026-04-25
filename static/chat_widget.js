/**
 * Chat Widget JavaScript
 * 全局 Agent 小组件
 */

(function() {
    'use strict';

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
        const fullLink = document.querySelector('.chat-widget-fullscreen');

        if (!widget || !btn || !messagesContainer || !inputArea || !sendBtn) return;

        let currentConversationId = null;
        let isProcessing = false;
        const userId = (window.CIApp && window.CIApp.getUserId()) || 'widget_user';

        if (fullLink && window.CIApp) {
            fullLink.href = window.CIApp.getChatUrl();
        }

        btn.addEventListener('click', () => {
            widget.classList.toggle('active');
            if (widget.classList.contains('active')) {
                inputArea.focus();
            }
        });

        closeBtn?.addEventListener('click', () => {
            widget.classList.remove('active');
        });

        sendBtn.addEventListener('click', sendMessage);

        inputArea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        inputArea.addEventListener('input', () => {
            inputArea.style.height = 'auto';
            inputArea.style.height = Math.min(inputArea.scrollHeight, 100) + 'px';
        });

        quickActionBtns.forEach(button => {
            button.addEventListener('click', () => {
                const action = button.dataset.action;
                const promptMap = {
                    daily: '生成一份适合我的个性化市场简报',
                    trending: '分析一下今天的市场局势，给我3个最重要的结论',
                    alpha: '帮我筛出过去6小时更适合短线关注的高波动机会'
                };
                const prompt = promptMap[action];
                if (prompt) {
                    inputArea.value = prompt;
                    sendMessage();
                }
            });
        });

        async function sendMessage() {
            const message = inputArea.value.trim();
            if (!message || isProcessing) return;

            isProcessing = true;
            sendBtn.disabled = true;

            addMessage(message, 'user');
            inputArea.value = '';
            inputArea.style.height = 'auto';

            const loadingEl = addLoadingMessage();

            try {
                const response = await fetch('/api/v1/agent/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message,
                        conversation_id: currentConversationId,
                        user_id: userId
                    })
                });

                if (!response.ok) {
                    throw new Error('API请求失败');
                }

                const data = await response.json();
                removeLoadingMessage(loadingEl);
                addAgentResponse(data);

                if (data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    if (fullLink && window.CIApp) {
                        fullLink.href = window.CIApp.getChatUrl(currentConversationId);
                    }
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

        function addAgentResponse(data) {
            if (!data) return;
            addMessage(data.response || '已完成当前任务。', 'assistant');

            const blocks = Array.isArray(data.result_blocks) ? data.result_blocks : [];
            if (!blocks.length) return;

            const messageEl = document.createElement('div');
            messageEl.className = 'chat-message assistant';

            const avatarEl = document.createElement('div');
            avatarEl.className = 'message-avatar';
            avatarEl.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>';

            const contentEl = document.createElement('div');
            contentEl.className = 'message-content';
            contentEl.innerHTML = blocks.slice(0, 2).map((block) => `
                <div style="margin-top:8px;padding:10px 12px;border-radius:12px;background:rgba(99,102,241,0.08);">
                    <p style="margin:0 0 6px;"><strong>${escapeHtml(block.title || '任务结果')}</strong></p>
                    <p style="margin:0;color:#475569;">${escapeHtml(block.summary || '')}</p>
                </div>
            `).join('') + `<p style="margin-top: 8px;"><a href="${window.CIApp ? window.CIApp.getChatUrl(currentConversationId) : '/chat'}" style="color: #667eea;">进入研究工作区继续追问 →</a></p>`;

            messageEl.appendChild(avatarEl);
            messageEl.appendChild(contentEl);
            messagesContainer.appendChild(messageEl);
            scrollToBottom();
        }

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

        function removeLoadingMessage(loadingEl) {
            if (loadingEl && loadingEl.parentNode) {
                loadingEl.parentNode.removeChild(loadingEl);
            }
        }

        function formatMessage(text) {
            return escapeHtml(text).replace(/\n/g, '<br>');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text || '';
            return div.innerHTML;
        }

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
})();
