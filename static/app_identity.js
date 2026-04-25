(function () {
    'use strict';

    const STORAGE_KEY = 'crypto_insight_user_id';
    const QUERY_CACHE = new URLSearchParams(window.location.search || '');

    function getQueryParam(name) {
        return QUERY_CACHE.get(name);
    }

    function ensureUserId() {
        const fromQuery = getQueryParam('user_id');
        if (fromQuery) {
            localStorage.setItem(STORAGE_KEY, fromQuery);
            return fromQuery;
        }
        const existing = localStorage.getItem(STORAGE_KEY);
        if (existing) return existing;
        const generated = `web_user_${Math.random().toString(36).slice(2, 10)}`;
        localStorage.setItem(STORAGE_KEY, generated);
        return generated;
    }

    function getChatUrl(conversationId) {
        const url = new URL('/chat', window.location.origin);
        url.searchParams.set('user_id', ensureUserId());
        if (conversationId) {
            url.searchParams.set('conversation_id', String(conversationId));
        }
        return url.pathname + url.search;
    }

    async function fetchOnboardingStatus() {
        const userId = ensureUserId();
        const resp = await fetch(`/api/v1/agent/onboarding/status?user_id=${encodeURIComponent(userId)}`);
        if (!resp.ok) {
            throw new Error('failed to fetch onboarding status');
        }
        return resp.json();
    }

    async function fetchProfile() {
        const userId = ensureUserId();
        const resp = await fetch(`/api/v1/agent/profile?user_id=${encodeURIComponent(userId)}`);
        if (!resp.ok) {
            throw new Error('failed to fetch profile');
        }
        return resp.json();
    }

    async function fetchQuestions() {
        const resp = await fetch('/api/v1/agent/onboarding/questions');
        if (!resp.ok) {
            throw new Error('failed to fetch onboarding questions');
        }
        return resp.json();
    }

    function ensureModalShell() {
        let root = document.getElementById('global-onboarding-modal');
        if (root) return root;

        root = document.createElement('div');
        root.id = 'global-onboarding-modal';
        root.className = 'onboarding-modal';
        root.hidden = true;
        root.innerHTML = `
            <div class="onboarding-dialog">
                <div class="onboarding-header">
                    <div>
                        <span class="profile-chip">画像配置</span>
                        <h3>先告诉 Agent 你的投资风格</h3>
                        <p>系统会基于你的偏好，调整新闻推荐、报告风格与后续任务结果。</p>
                    </div>
                    <button type="button" class="onboarding-close" aria-label="关闭">×</button>
                </div>
                <div class="onboarding-questions"></div>
                <div class="onboarding-footer">
                    <div class="onboarding-status">完成这组轻量问题后，首页和聊天页都会变成个性化工作区。</div>
                    <div class="agent-input-actions">
                        <button type="button" class="btn btn-secondary onboarding-close-btn">稍后再说</button>
                        <button type="button" class="btn btn-primary onboarding-submit-btn">保存画像</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(root);

        root.querySelectorAll('.onboarding-close, .onboarding-close-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                root.hidden = true;
            });
        });
        root.addEventListener('click', (event) => {
            if (event.target === root) {
                root.hidden = true;
            }
        });

        return root;
    }

    function renderQuestions(root, questions, currentAnswers) {
        const container = root.querySelector('.onboarding-questions');
        container.innerHTML = '';

        questions.forEach((question) => {
            const card = document.createElement('section');
            card.className = 'onboarding-question';
            const selected = currentAnswers[question.id] || (question.type === 'multi' ? [] : null);
            card.innerHTML = `<h4>${question.title}</h4>`;
            const optionsWrap = document.createElement('div');
            optionsWrap.className = 'onboarding-options';

            question.options.forEach((option) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'onboarding-option';
                button.textContent = option.label;
                const isActive = Array.isArray(selected)
                    ? selected.includes(option.value)
                    : selected === option.value;
                if (isActive) button.classList.add('active');
                button.addEventListener('click', () => {
                    if (question.type === 'multi') {
                        const existing = Array.isArray(currentAnswers[question.id]) ? [...currentAnswers[question.id]] : [];
                        const idx = existing.indexOf(option.value);
                        if (idx >= 0) {
                            existing.splice(idx, 1);
                            button.classList.remove('active');
                        } else {
                            existing.push(option.value);
                            button.classList.add('active');
                        }
                        currentAnswers[question.id] = existing;
                    } else {
                        currentAnswers[question.id] = option.value;
                        optionsWrap.querySelectorAll('.onboarding-option').forEach((item) => item.classList.remove('active'));
                        button.classList.add('active');
                    }
                });
                optionsWrap.appendChild(button);
            });

            card.appendChild(optionsWrap);
            container.appendChild(card);
        });
    }

    async function openOnboarding(options = {}) {
        const root = ensureModalShell();
        const userId = ensureUserId();
        const currentAnswers = {};
        root.hidden = false;

        const [questionPayload, statusPayload] = await Promise.all([
            fetchQuestions(),
            fetchOnboardingStatus().catch(() => ({ summary: { preferences: {} } })),
        ]);
        const existingPrefs = (((statusPayload || {}).summary || {}).preferences) || {};
        Object.assign(currentAnswers, existingPrefs);
        renderQuestions(root, questionPayload.questions || [], currentAnswers);

        const submitBtn = root.querySelector('.onboarding-submit-btn');
        submitBtn.disabled = false;
        submitBtn.textContent = '保存画像';
        submitBtn.onclick = async () => {
            submitBtn.disabled = true;
            submitBtn.textContent = '保存中...';
            try {
                const resp = await fetch('/api/v1/agent/onboarding/complete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, answers: currentAnswers }),
                });
                if (!resp.ok) {
                    throw new Error('failed to save onboarding');
                }
                const data = await resp.json();
                root.hidden = true;
                if (typeof options.onComplete === 'function') {
                    options.onComplete(data.profile);
                }
            } catch (error) {
                console.error('onboarding 保存失败', error);
                submitBtn.disabled = false;
                submitBtn.textContent = '重试保存';
            }
        };
    }

    async function ensureOnboarding(options = {}) {
        const payload = await fetchOnboardingStatus().catch(() => null);
        if (payload && !payload.profile_initialized) {
            return openOnboarding(options);
        }
        return payload;
    }

    window.CIApp = {
        getUserId: ensureUserId,
        getQueryParam,
        getChatUrl,
        fetchOnboardingStatus,
        fetchProfile,
        openOnboarding,
        ensureOnboarding,
    };
})();
