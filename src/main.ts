import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'
import { applyGradients } from './utils/gradient'

// 在 app 挂载前同步设置初始渐变值，消除刷新/首屏闪烁
applyGradients()

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')