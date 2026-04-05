/**
 * Skills JavaScript
 * 技能执行通用工具函数
 */

(function(window) {
    'use strict';

    const Skills = {
        /**
         * 执行技能
         * @param {string} skillName - 技能名称
         * @param {object} params - 技能参数
         * @param {string} userId - 用户ID
         * @returns {Promise<object>} - 技能执行结果
         */
        async execute(skillName, params = {}, userId = 'default_user') {
            try {
                const response = await fetch('/api/v1/agent/skills/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        skill_name: skillName,
                        user_id: userId,
                        params: params
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail || '技能执行失败');
                }

                return await response.json();
            } catch (error) {
                console.error(`技能 ${skillName} 执行失败:`, error);
                throw error;
            }
        },

        /**
         * 获取可用技能列表
         * @returns {Promise<object>} - 技能列表
         */
        async list() {
            try {
                const response = await fetch('/api/v1/agent/skills');
                if (!response.ok) {
                    throw new Error('获取技能列表失败');
                }
                return await response.json();
            } catch (error) {
                console.error('获取技能列表失败:', error);
                throw error;
            }
        },

        /**
         * 获取技能信息
         * @param {string} skillName - 技能名称
         * @returns {Promise<object>} - 技能信息
         */
        async getInfo(skillName) {
            try {
                const response = await fetch(`/api/v1/agent/skills/${skillName}`);
                if (!response.ok) {
                    throw new Error('获取技能信息失败');
                }
                return await response.json();
            } catch (error) {
                console.error(`获取技能 ${skillName} 信息失败:`, error);
                throw error;
            }
        },

        /**
         * 技能名称映射（中英文）
         */
        nameMap: {
            'DailyBriefing': {
                zh: '每日简报',
                icon: '📊',
                description: '市场概览 + 热门新闻'
            },
            'DeepDive': {
                zh: '深度分析',
                icon: '🔍',
                description: '话题深度挖掘'
            },
            'AlphaHunter': {
                zh: 'Alpha挖掘',
                icon: '🎯',
                description: '发现潜在机会'
            }
        },

        /**
         * 获取技能中文名称
         * @param {string} skillName - 技能英文名
         * @returns {string} - 技能中文名
         */
        getZhName(skillName) {
            return this.nameMap[skillName]?.zh || skillName;
        },

        /**
         * 获取技能图标
         * @param {string} skillName - 技能名称
         * @returns {string} - 技能图标
         */
        getIcon(skillName) {
            return this.nameMap[skillName]?.icon || '📋';
        },

        /**
         * 格式化技能报告（Markdown转HTML）
         * @param {string} report - Markdown格式的报告
         * @returns {string} - HTML格式的报告
         */
        formatReport(report) {
            if (!report) return '';

            // 简单的Markdown转换
            let html = report;

            // 标题
            html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
            html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
            html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

            // 粗体
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

            // 换行
            html = html.replace(/\n/g, '<br>');

            // 列表
            html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
            html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

            // 分割线
            html = html.replace(/^---$/gim, '<hr>');

            return html;
        }
    };

    // 导出到全局
    window.Skills = Skills;

})(window);
