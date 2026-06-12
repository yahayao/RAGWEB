<template>
  <div class="settings-container" :class="{ 'dark-theme': chatStore.isDarkTheme }">
    <div class="settings-header">
      <h1>设置</h1>
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
          <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
        返回主页
      </button>
    </div>

    <div class="setting-item">
      <label>API 地址</label>
      <input v-model="apiUrl" type="text" placeholder="http://localhost:8000/api" />
    </div>

    <div class="setting-item">
      <label>模型选择</label>
      <select v-model="selectedModel">
        <option value="Qwen3-14B">Qwen3-14B</option>
        <option value="Qwen3.6-35B-A3B">Qwen3.6-35B-A3B</option>
      </select>
    </div>

    <!-- 流式输出开关 -->
    <div class="setting-item setting-item--row">
      <div class="setting-label-group">
        <label>流式输出</label>
        <span class="setting-desc">开启后 AI 回复将逐字实时显示</span>
      </div>
      <button class="toggle-btn" :class="{ 'toggle-btn--on': chatStore.isStreaming }"
        @click="chatStore.toggleStreaming()" :aria-label="chatStore.isStreaming ? '关闭流式输出' : '开启流式输出'">
        <span class="toggle-track">
          <span class="toggle-thumb"></span>
        </span>
        <span class="toggle-text">{{ chatStore.isStreaming ? '已开启' : '已关闭' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../store/chat'

const router = useRouter()

const chatStore = useChatStore()

const apiUrl = ref(import.meta.env.VITE_API_BASE_URL)
const selectedModel = ref('gpt-3.5-turbo')
</script>

<style scoped>
/* ============================================
   SettingsView — 设置页面新视觉
   ============================================ */

.settings-container {
  max-width: 620px;
  margin: 48px auto;
  padding: 0 20px;
}

/* ---- 顶部标题栏 ---- */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
}

.settings-header h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.5px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 18px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  text-decoration: none;
}

.back-btn:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.back-btn:active {
  transform: scale(0.97);
}

/* ---- 设置卡片组 ---- */
.setting-item {
  background: #fff;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 14px;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-xs);
}

.setting-item:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-sm);
}

.setting-item--row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

/* ---- 标签组 ---- */
.setting-label-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

label {
  display: block;
  font-weight: 600;
  font-size: 14.5px;
  color: var(--color-text-primary);
  margin-bottom: 0;
}

.setting-desc {
  font-size: 12.5px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* ---- 输入 & 选择框 ---- */
input,
select {
  width: 100%;
  padding: 11px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  outline: none;
  transition: all var(--duration-fast) var(--ease-out);
  margin-top: 10px;
}

input:focus,
select:focus {
  border-color: var(--color-primary);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

/* ---- 开关按钮 ---- */
.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  border: none;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-track {
  position: relative;
  display: inline-block;
  width: 46px;
  height: 26px;
  border-radius: 13px;
  background: #d1d5db;
  transition: background var(--duration-fast) var(--ease-out);
}

.toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform var(--duration-fast) var(--ease-out);
}

.toggle-btn--on .toggle-track {
  background: var(--color-primary);
}

.toggle-btn--on .toggle-thumb {
  transform: translateX(20px);
}

.toggle-text {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-text-secondary);
  min-width: 44px;
}

.toggle-btn--on .toggle-text {
  color: var(--color-primary);
}

/* ---- 深色模式 ---- */
.settings-container.dark-theme {
  --color-bg: #0f172a;
  --color-surface: #1e293b;
  --color-border: #334155;
  --color-border-light: #1e293b;
  --color-text-primary: #f1f5f9;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #64748b;
  --color-primary-light: rgba(99, 102, 241, 0.12);
}

.settings-container.dark-theme .setting-item {
  background: var(--color-surface);
}

.settings-container.dark-theme .back-btn {
  background: var(--color-surface);
}

.settings-container.dark-theme input,
.settings-container.dark-theme select {
  background: var(--color-bg);
}

.settings-container.dark-theme input:focus,
.settings-container.dark-theme select:focus {
  background: var(--color-surface);
}

.settings-container.dark-theme .toggle-track {
  background: #475569;
}

/* ---- 响应式 ---- */
@media (max-width: 640px) {
  .settings-container {
    margin: 24px auto;
    padding: 0 14px;
  }

  .setting-item {
    padding: 16px 18px;
  }

  .settings-header h1 {
    font-size: 22px;
  }
}
</style>
