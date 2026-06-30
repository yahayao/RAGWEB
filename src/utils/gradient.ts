/**
 * 24 小时动态渐变背景工具
 * 根据本地时间分钟级平滑插值，背景随时间流动
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
  // 🌅 06:00 黎明
  [6,  { light: ['dbeafe', 'ede9fe', 'fce7f3'], dark: ['3b5998', '1a2744', '0c1422'] }],
  // ☀️ 12:00 正午
  [12, { light: ['f0f9ff', 'faf5ff', 'fff5f5'], dark: ['4a6080', '222d4a', '0f172a'] }],
  // 🌇 18:00 黄昏
  [18, { light: ['fde68a', 'fbcfe8', 'c4b5fd'], dark: ['5a3a5e', '1f1830', '0b0814'] }],
  // 🌙 24:00 午夜
  [24, { light: ['1a1333', '0c081a', '090618'], dark: ['1e1840', '0a0818', '030208'] }],
  // 🔁 30:00 = 次日 06:00，循环闭合
  [30, { light: ['dbeafe', 'ede9fe', 'fce7f3'], dark: ['3b5998', '1a2744', '0c1422'] }],
]

/** 获取本地时间（含秒），返回 0-24 的小时数 */
export const getLocalHourFloat = (): number => {
  const now = new Date()
  return now.getHours() + now.getMinutes() / 60 + now.getSeconds() / 3600
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
const lerpColors = (
  a: [string, string, string],
  b: [string, string, string],
  t: number,
): [string, string, string] => [
  lerpColor(a[0], b[0], t),
  lerpColor(a[1], b[1], t),
  lerpColor(a[2], b[2], t),
]

/** 三色数组 → CSS gradient */
const toGradient = (c: [string, string, string]): string =>
  `linear-gradient(135deg, #${c[0]} 0%, #${c[1]} 50%, #${c[2]} 100%)`

export interface GradientResult {
  lightGrad: string
  darkGrad: string
  intHour: number
}

/** 根据当前小时数计算渐变值 */
export const computeGradients = (hourFloat?: number): GradientResult => {
  let h = hourFloat ?? getLocalHourFloat()

  // 凌晨 0:00–6:00：h+24 映射到 24~30 区间，利用 KEY_STOPS 的环绕节点
  if (h < KEY_STOPS[0]![0]) {
    h += 24
  }

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

  // 映射回真实小时数（0-23），用于 data-time-theme 判断
  const intHour = Math.floor(h) % 24

  return {
    lightGrad: toGradient(lerpColors(prev[1].light, next[1].light, t)),
    darkGrad: toGradient(lerpColors(prev[1].dark, next[1].dark, t)),
    intHour,
  }
}

/** 将渐变结果写入 DOM（在 app 挂载前调用可消除闪烁） */
export const applyGradients = (): GradientResult => {
  const { lightGrad, darkGrad, intHour } = computeGradients()
  const isMorning = intHour >= 6 && intHour < 18

  const root = document.documentElement
  root.setAttribute('data-time-theme', isMorning ? 'morning' : 'evening')

  // JS 直接设置 CSS 变量，绕过 CSS 属性选择器加载时序问题
  root.style.setProperty('--bg-gradient-dynamic', lightGrad)
  root.style.setProperty('--bg-gradient-dynamic-dark', darkGrad)
  root.style.setProperty('--color-bg-gradient', `var(--bg-gradient-dynamic, var(--bg-gradient-morning))`)
  root.style.setProperty('--color-bg-gradient-dark', `var(--bg-gradient-dynamic-dark, var(--bg-gradient-dark-evening))`)

  return { lightGrad, darkGrad, intHour }
}
