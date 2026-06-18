<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'

/**
 * 时间主题检测：根据当前小时自动切换背景渐变
 * - 白天主题 (morning)：6:00–17:59
 * - 傍晚主题 (evening)：18:00–5:59
 */
const MORNING_START = 6
const EVENING_START = 18

let timeCheckTimer: ReturnType<typeof setInterval> | null = null

const getTimeTheme = (): 'morning' | 'evening' => {
  const hour = new Date().getHours()
  return hour >= MORNING_START && hour < EVENING_START ? 'morning' : 'evening'
}

const applyTimeTheme = () => {
  document.documentElement.setAttribute('data-time-theme', getTimeTheme())
}

onMounted(() => {
  applyTimeTheme()
  // 每 60 秒检查一次，在整点附近自动切换
  timeCheckTimer = setInterval(applyTimeTheme, 60_000)
})

onBeforeUnmount(() => {
  if (timeCheckTimer) {
    clearInterval(timeCheckTimer)
    timeCheckTimer = null
  }
})
</script>

<style>
/* App.vue 已无需全局样式 —— 所有设计令牌与重置已迁移至 main.css */
</style>