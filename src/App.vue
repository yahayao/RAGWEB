<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { applyGradients } from './utils/gradient'

let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // 初始值已在 main.ts 中同步设置，此处确保组件挂载后与当前时间同步
  applyGradients()
  timer = setInterval(applyGradients, 1_000)
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
