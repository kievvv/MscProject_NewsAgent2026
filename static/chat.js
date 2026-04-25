/**
 * Chat Page JavaScript
 * 连续研究工作区交互逻辑
 */

(function() {
    'use strict';

    const STATE = {
        currentConversationId: null,
        userId: (window.CIApp && window.CIApp.getUserId()) || 'web_user',
        isProcessing: false,
        conversations: [],
    };

    const DOM = {
        messagesContainer: document.getElementById('chat-messages'),
        inputArea: document.getElementById('chat-input'),
        sendBtn: document.getElementById('send-btn'),
        newChatBtn: document.getElementById('new-chat-btn'),
        clearChatBtn: document.getElementById('clear-chat-btn'),
        conversationList: document.getElementById('conversation-list'),
        welcomeScreen: document.getElementById('welcome-screen'),
        profileSummary: document.getElementById('chat-profile-summary'),
        onboardingBtn: document.getElementById('open-onboarding-btn'),
        chatHeader: document.querySelector('.chat-header'),
        capabilityBtn: document.getElementById('chat-capability-btn'),
    };

    function init() {
        if (!DOM.messagesContainer) return;
        STATE.currentConversationId = (window.CIApp && window.CIApp.getQueryParam('conversation_id'))
            || DOM.chatHeader?.dataset.chatConversation
            || null;
        bindEvents();
        refreshProfileSummary();
        loadConversations();
        maybeOpenOnboarding();
        if (STATE.currentConversationId) {
            loadConversation(STATE.currentConversationId);
        }
    }

    function bindEvents() {
        DOM.sendBtn?.addEventListener('click', sendMessage);
        DOM.capabilityBtn?.addEventListener('click', () => window.CIApp?.openAgentPalette(DOM.inputArea));
        DOM.inputArea?.addEventListener('keydown', (e) => {
            if (e.key === '/' && DOM.inputArea.value.trim() === '') {
                e.preventDefault();
                window.CIApp?.openAgentPalette(DOM.inputArea);
                return;
            }
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        DOM.inputArea?.addEventListener('input', () => {
            DOM.inputArea.style.height = 'auto';
            DOM.inputArea.style.height = Math.min(DOM.inputArea.scrollHeight, 150) + 'px';
        });
        DOM.newChatBtn?.addEventListener('click', startNewConversation);
        DOM.clearChatBtn?.addEventListener('click', clearCurrentConversation);
        DOM.onboardingBtn?.addEventListener('click', () => {
            window.CIApp?.openOnboarding({ onComplete: () => refreshProfileSummary() });
        });
        document.querySelectorAll('.task-card, .example-query').forEach((el) => {
            el.addEventListener('click', () => {
                const prompt = el.dataset.prompt || el.textContent.trim();
                if (DOM.inputArea) {
                    DOM.inputArea.value = prompt;
                    sendMessage();
                }
            });
        });
    }

    async function loadConversations() {
        try {
            const response = await fetch(`/api/v1/agent/conversations?user_id=${encodeURIComponent(STATE.userId)}`);
            const data = await response.json();
            STATE.conversations = data.conversations || [];
            renderConversationList();
        } catch (error) {
            console.error('加载对话列表失败:', error);
        }
    }

    function renderConversationList() {
        if (!DOM.conversationList) return;
        if (!STATE.conversations.length) {
            DOM.conversationList.innerHTML = `
                <div class="conversation-item-placeholder">
                    <p>暂无对话历史</p>
                    <p class="text-muted">从一个问题开始，系统会保留上下文</p>
                </div>
            `;
            return;
        }
        DOM.conversationList.innerHTML = STATE.conversations.map((conv) => `
            <div class="conversation-item ${String(conv.id) === String(STATE.currentConversationId) ? 'active' : ''}" data-conversation-id="${conv.id}">
                <div class="conversation-item-title">${escapeHtml(conv.title || '新对话')}</div>
                <div class="conversation-item-time">${formatTime(conv.updated_at || conv.created_at)}</div>
            </div>
        `).join('');
        DOM.conversationList.querySelectorAll('.conversation-item').forEach((item) => {
            item.addEventListener('click', () => loadConversation(item.dataset.conversationId));
        });
    }

    async function loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/v1/agent/conversations/${conversationId}`);
            const data = await response.json();
            STATE.currentConversationId = conversationId;
            syncConversationUrl();
            if (DOM.welcomeScreen) DOM.welcomeScreen.style.display = 'none';
            DOM.messagesContainer.innerHTML = '';
            (data.messages || []).forEach((msg) => addMessage(msg.content, msg.role, false));
            renderConversationList();
            scrollToBottom();
        } catch (error) {
            console.error('加载对话失败:', error);
            showError('加载对话失败');
        }
    }

    function syncConversationUrl() {
        if (!window.history || !window.CIApp) return;
        const nextUrl = STATE.currentConversationId
            ? window.CIApp.getChatUrl(STATE.currentConversationId)
            : window.CIApp.getChatUrl();
        window.history.replaceState({}, '', nextUrl);
    }

    function startNewConversation() {
        STATE.currentConversationId = null;
        syncConversationUrl();
        DOM.messagesContainer.innerHTML = '';
        if (DOM.welcomeScreen) {
            DOM.messagesContainer.appendChild(DOM.welcomeScreen);
            DOM.welcomeScreen.style.display = 'block';
        }
        renderConversationList();
        DOM.inputArea?.focus();
    }

    function clearCurrentConversation() {
        startNewConversation();
    }

    async function sendMessage() {
        const message = DOM.inputArea?.value.trim();
        if (!message || STATE.isProcessing) return;
        if (message === '/') {
            window.CIApp?.openAgentPalette(DOM.inputArea);
            return;
        }
        STATE.isProcessing = true;
        if (DOM.sendBtn) DOM.sendBtn.disabled = true;
        if (DOM.welcomeScreen) DOM.welcomeScreen.style.display = 'none';
        addMessage(message, 'user');
        DOM.inputArea.value = '';
        DOM.inputArea.style.height = 'auto';
        const loadingEl = addLoadingMessage();
        try {
            const response = await fetch('/api/v1/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    conversation_id: STATE.currentConversationId,
                    user_id: STATE.userId,
                }),
            });
            if (!response.ok) throw new Error('API请求失败');
            const data = await response.json();
            removeLoadingMessage(loadingEl);
            addAssistantResult(data);
            if (data.conversation_id) {
                STATE.currentConversationId = data.conversation_id;
                syncConversationUrl();
                await loadConversations();
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            removeLoadingMessage(loadingEl);
            showError('抱歉，发送消息时出现错误，请稍后重试。');
        } finally {
            STATE.isProcessing = false;
            if (DOM.sendBtn) DOM.sendBtn.disabled = false;
            DOM.inputArea?.focus();
        }
    }

    function addMessage(text, role, scroll = true) {
        const messageEl = document.createElement('div');
        messageEl.className = `chat-message ${role}`;
        const timeStr = formatClockTime(new Date());
        const content = role === 'assistant'
            ? (window.CIRenderMarkdown ? window.CIRenderMarkdown(text) : escapeHtml(text).replace(/\n/g, '<br>'))
            : escapeHtml(text).replace(/\n/g, '<br>');
        messageEl.innerHTML = `
            <div class="message-avatar">${role === 'assistant' ? assistantIcon() : userIcon()}</div>
            <div class="message-content">
                <div class="message-bubble ${role === 'assistant' ? 'assistant-brief ci-markdown' : ''}">${content}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
        DOM.messagesContainer.appendChild(messageEl);
        if (scroll) scrollToBottom();
    }

    function addAssistantResult(data) {
        const messageEl = document.createElement('div');
        messageEl.className = 'chat-message assistant';
        const finalAnswer = data.final_answer || data.response || data.reply || '';
        const answerBlocks = Array.isArray(data.answer_blocks) ? data.answer_blocks : [];
        const actions = Array.isArray(data.recommended_actions) ? data.recommended_actions.slice(0, 4) : [];
        const traceSummary = data.execution_trace_summary || {};
        const executionId = data.execution_id;
        messageEl.innerHTML = `
            <div class="message-avatar">${assistantIcon()}</div>
            <div class="message-content">
                <div class="message-bubble assistant-brief ci-markdown">${window.CIRenderMarkdown ? window.CIRenderMarkdown(finalAnswer) : escapeHtml(finalAnswer)}</div>
                ${renderAnswerBlocks(answerBlocks)}
                <div class="message-meta-row">
                    <span class="message-process-badge">已调用 ${escapeHtml(String(traceSummary.total_tools ?? 0))} 个能力</span>
                    ${executionId ? '<button type="button" class="mini-link trace-toggle-btn">查看过程</button>' : ''}
                </div>
                ${actions.length ? `<div class="task-result-actions message-followups">${actions.map((item) => `<button type="button" class="mini-link inline-followup-btn" data-followup="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('')}</div>` : ''}
                <div class="trace-drawer" hidden></div>
                <div class="message-time">${formatClockTime(new Date())}</div>
            </div>
        `;
        DOM.messagesContainer.appendChild(messageEl);
        bindResultEvents(messageEl, data);
        scrollToBottom();
    }

    function renderAnswerBlocks(blocks) {
        if (!blocks.length) return '';
        const cleanText = (value) => window.CIStripMarkdown ? window.CIStripMarkdown(value) : escapeHtml(value);
        return `<div class="assistant-result-stack">${blocks.map((block) => {
            if (block.type === 'news_list') {
                return `
                    <section class="task-result-card">
                        <div class="task-result-top"><h4>${escapeHtml(block.title || '新闻')}</h4></div>
                        <div class="result-news-list">
                            ${(block.items || []).map((item) => `
                                <article class="result-news-item">
                                    <button type="button" class="news-detail-btn" data-news-id="${escapeHtml(String(item.id || ''))}">${escapeHtml(cleanText(item.title || '未命名资讯'))}</button>
                                    <p>${escapeHtml(cleanText(item.summary || '').slice(0, 180))}</p>
                                    <div class="mini-actions">
                                        ${item.url ? `<a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">查看原文</a>` : ''}
                                        ${item.id ? `<button type="button" class="mini-link news-detail-btn" data-news-id="${escapeHtml(String(item.id))}">查看详情</button>` : ''}
                                        ${Array.isArray(item.keyword_list) && item.keyword_list[0] ? `<a href="/search?source=crypto&keyword=${encodeURIComponent(item.keyword_list[0])}">相关搜索</a>` : ''}
                                    </div>
                                </article>
                            `).join('')}
                        </div>
                    </section>
                `;
            }
            if (block.type === 'market_snapshot') {
                const snapshot = block.data || {};
                const coins = Array.isArray(snapshot.coins) ? snapshot.coins.slice(0, 4) : [];
                return `
                    <section class="task-result-card">
                        <div class="task-result-top"><h4>${escapeHtml(block.title || '市场快照')}</h4></div>
                        <p class="task-result-summary">${escapeHtml(block.summary || '')}</p>
                        <div class="market-inline-grid">
                            ${coins.map((item) => `<div class="market-inline-item"><strong>${escapeHtml(item.symbol || '')}</strong><span>${escapeHtml(String(item.price_change_percentage_24h ?? '—'))}%</span></div>`).join('')}
                        </div>
                    </section>
                `;
            }
            if (block.type === 'keyword_list') {
                return `
                    <section class="task-result-card">
                        <div class="task-result-top"><h4>${escapeHtml(block.title || '相关关键词')}</h4></div>
                        <div class="keyword-chip-group">
                            ${(block.items || []).map((item) => `<a class="task-pill task-pill-link" href="/search?source=crypto&keyword=${encodeURIComponent(item.keyword || '')}">${escapeHtml(item.keyword || '')}</a>`).join('')}
                        </div>
                    </section>
                `;
            }
            if (block.type === 'opportunity_list') {
                return `
                    <section class="task-result-card">
                        <div class="task-result-top"><h4>${escapeHtml(block.title || '观察名单')}</h4></div>
                        <div class="result-news-list">
                            ${(block.items || []).map((item) => `
                                <article class="result-news-item">
                                    <strong>${escapeHtml(item.symbol || '标的')}</strong>
                                    <p>${escapeHtml(item.reason || '暂无说明')}</p>
                                </article>
                            `).join('')}
                        </div>
                    </section>
                `;
            }
            return '';
        }).join('')}</div>`;
    }

    function bindResultEvents(messageEl, data) {
        messageEl.querySelectorAll('.inline-followup-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                DOM.inputArea.value = btn.dataset.followup || '';
                DOM.inputArea.focus();
            });
        });
        const traceBtn = messageEl.querySelector('.trace-toggle-btn');
        const drawer = messageEl.querySelector('.trace-drawer');
        if (traceBtn && drawer && data.execution_id) {
            traceBtn.addEventListener('click', async () => {
                if (!drawer.hidden) {
                    drawer.hidden = true;
                    traceBtn.textContent = '查看过程';
                    return;
                }
                traceBtn.textContent = '加载中...';
                try {
                    const response = await fetch(`/api/v1/agent/executions/${encodeURIComponent(data.execution_id)}`);
                    const payload = await response.json();
                    drawer.innerHTML = renderExecutionTrace(payload.execution || {});
                    drawer.hidden = false;
                    traceBtn.textContent = '收起过程';
                } catch (error) {
                    drawer.innerHTML = '<div class="capability-loading">过程信息暂不可用</div>';
                    drawer.hidden = false;
                    traceBtn.textContent = '收起过程';
                }
            });
        }
    }

    function renderExecutionTrace(execution) {
        const toolCalls = Array.isArray(execution.tool_calls) ? execution.tool_calls : [];
        return `
            <section class="trace-panel">
                <h4>执行过程</h4>
                <ol class="trace-list">
                    ${toolCalls.map((call) => `
                        <li>
                            <div class="trace-title-row">
                                <strong>${escapeHtml(call.title || call.tool_id || '工具')}</strong>
                                <span>${escapeHtml(call.status || '')} · ${escapeHtml(String(call.duration_ms ?? '—'))}ms</span>
                            </div>
                            <p>${escapeHtml(call.input_preview || '')}</p>
                            ${call.output_preview ? `<small>${escapeHtml(call.output_preview)}</small>` : ''}
                        </li>
                    `).join('') || '<li>暂无过程数据</li>'}
                </ol>
            </section>
        `;
    }

    function addLoadingMessage() {
        const messageEl = document.createElement('div');
        messageEl.className = 'chat-message assistant';
        messageEl.innerHTML = `
            <div class="message-avatar">${assistantIcon()}</div>
            <div class="message-content">
                <div class="message-bubble assistant-brief">
                    <div class="message-loading"><span></span><span></span><span></span></div>
                    <div class="message-status-text" data-loading-status>正在解析请求</div>
                </div>
            </div>
        `;
        DOM.messagesContainer.appendChild(messageEl);
        const statuses = ['正在解析请求', '正在检索数据', '正在整理回答'];
        let index = 0;
        const label = messageEl.querySelector('[data-loading-status]');
        const timer = window.setInterval(() => {
            index = (index + 1) % statuses.length;
            if (label) label.textContent = statuses[index];
        }, 900);
        messageEl.dataset.loadingTimer = String(timer);
        scrollToBottom();
        return messageEl;
    }

    function removeLoadingMessage(loadingEl) {
        if (!loadingEl) return;
        const timer = Number(loadingEl.dataset.loadingTimer);
        if (timer) window.clearInterval(timer);
        loadingEl.remove();
    }

    function showError(message) {
        addMessage(message, 'assistant');
    }

    async function refreshProfileSummary() {
        try {
            const data = await window.CIApp?.fetchProfile();
            const summary = data?.profile?.summary?.summary || '围绕一个问题开始';
            if (DOM.profileSummary) DOM.profileSummary.textContent = summary;
        } catch (error) {
            console.error('加载画像摘要失败:', error);
        }
    }

    function maybeOpenOnboarding() {
        const shouldOpen = (window.CIApp && window.CIApp.getQueryParam('open_onboarding')) === '1'
            || DOM.chatHeader?.dataset.openOnboarding === '1';
        if (shouldOpen) {
            window.CIApp?.openOnboarding({ onComplete: () => refreshProfileSummary() });
            return;
        }
        window.CIApp?.ensureOnboarding({ onComplete: () => refreshProfileSummary() })
            .catch((error) => console.error('检查 onboarding 失败:', error));
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

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

    function formatClockTime(date) {
        return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    }

    function assistantIcon() {
        return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>';
    }

    function userIcon() {
        return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
    }

    function scrollToBottom() {
        DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
