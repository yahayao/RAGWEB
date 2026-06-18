<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'

/**
 * 24 小时动态渐变背景
 * 根据北京时间分钟级平滑插值，背景随时间流动
 *
 * 四组关键色站，每组 3 色（浅色 / 深色各一套）：
 *   🌅 06:00 黎明 — 天蓝淡紫浅玫瑰 / 藏蓝暗靛深灰紫
 *   ☀️ 12:00 正午 — 亮蓝白 / 暗蓝灰
 *   🌇 18:00 黄昏 — 暖奶油柔粉薰衣草 / 中暗紫
 *   🌙 24:00 午夜 — 深靛蓝深海蓝深蓝紫（最深）
 */

interface StopColors {
  light: [string, string, string]
  dark: [string, string, string]
}

const KEY_STOPS: [number, StopColors][] = [
  [6,  { light: ['e0f2fe', 'f0e6ff', 'ffe4e6'], dark: ['1a2744', '1e2244', '231e3e'] }], // 黎明
  [12, { light: ['eaf6ff', 'f6f2ff', 'fff4f5'], dark: ['1f2d4a', '222848', '272448'] }], // 正午
  [18, { light: ['fef3c7', 'fde2f3', 'e0d7fe'], dark: ['1c2042', '1a1d3e', '1b183e'] }], // 黄昏
  [24, { light: ['1e1b4b', '0f172a', '0c1445'], dark: ['151331', '0a0f1e', '080d2e'] }], // 午夜
  [30, { light: ['e0f2fe', 'f0e6ff', 'ffe4e6'], dark: ['1a2744', '1e2244', '231e3e'] }], // 次日黎明（循环）
]

let timer: ReturnType<typeof setInterval> | null = null

/** 获取北京时间（含分钟），返回 0-30 的小时数 */
const getBeijingHourFloat = (): number => {
  const parts = new Date()
    .toLocaleString('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: false,
      timeZone: 'Asia/Shanghai',
    })
    .split(':')
  return parseInt(parts[0]!, 10) + parseInt(parts[1]!, 10) / 60
}

/** hex → [r, g, b] */
const hexToRgb = (hex: string): [number, number, number] => [
  parseInt(hex.slice(0, 2), 16),
  parseInt(hex.slice(2, 4), 16),
  parseInt(hex.slice(4, 6), 16),
]

/** [r, g, b] → hex */
const rgbToHex = (r: number, g: number, b: number): string =>
  [r, g, b].map((c) => Math.round(c).toString(16).padStart(2, '0')).join('')

/** 在两个 hex 色之间按 ratio (0-1) 插值 */
const lerpColor = (a: string, b: string, t: number): string => {
  const [ar, ag, ab] = hexToRgb(a)
  const [br, bg, bb] = hexToRgb(b)
  return rgbToHex(ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t)
}

/** 插值一个三色数组 */
const lerpColors = (a: [string, string, string], b: [string, string, string], t: number): [string, string, string] => [
  lerpColor(a[0], b[0], t),
  lerpColor(a[1], b[1], t),
  lerpColor(a[2], b[2], t),
]

/** 三色数组 → CSS gradient */
const toGradient = (c: [string, string, string]): string =>
  `linear-gradient(135deg, #${c[0]} 0%, #${c[1]} 50%, #${c[2]} 100%)`

const updateGradient = () => {
  const h = getBeijingHourFloat()

  // 找到当前小时所在的两个关键色站
  let prev = KEY_STOPS[0]!
  let next = KEY_STOPS[1]!
  for (let i = 1; i < KEY_STOPS.length; i++) {
    if (h < KEY_STOPS[i]![0]) {
      prev = KEY_STOPS[i - 1]!
      next = KEY_STOPS[i]!
      break
    }
  }

  const range = next[0] - prev[0]
  const t = (h - prev[0]) / range

  // 分别计算浅色和深色的动态渐变
  const lightGrad = toGradient(lerpColors(prev[1].light, next[1].light, t))
  const darkGrad = toGradient(lerpColors(prev[1].dark, next[1].dark, t))

  const root = document.documentElement
  const intHour = Math.floor(h)
  root.setAttribute('data-time-theme', intHour >= 6 && intHour < 18 ? 'morning' : 'evening')

  // 写入 CSS 自定义属性
  root.style.setProperty('--bg-gradient-dynamic', lightGrad)
  root.style.setProperty('--bg-gradient-dynamic-dark', darkGrad)
}

onMounted(() => {
  updateGradient()
  timer = setInterval(updateGradient, 30_000)
})

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style>
/* App.vue 已无需全局样式 —— 所有设计令牌与重置已迁移至 main.css */
</style>
