import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { chatApiPlugin } from './vite-plugin-chat-api'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const chatBackendTarget = env.VITE_CHAT_BACKEND_URL || 'http://localhost:9000'
  const usePythonChatBackend = (env.VITE_USE_PYTHON_CHAT_BACKEND ?? 'true').toLowerCase() !== 'false'

  const serverProxy: Record<string, { target: string; changeOrigin: boolean; secure: boolean; xfwd?: boolean; ws?: boolean }> = {
    '/api/rag': {
      target: chatBackendTarget,
      changeOrigin: true,
      secure: false,
    },
  }

  if (usePythonChatBackend) {
    serverProxy['/api/chat'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      xfwd: true,
      secure: false,
    }
    // 人工介入告警接口
    serverProxy['/api/alert'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      xfwd: true,
      secure: false,
    }
    // 数据大屏 API
    serverProxy['/api/dashboard'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      xfwd: true,
      secure: false,
    }
    // 数据大屏 WebSocket
    serverProxy['/ws/dashboard'] = {
      target: chatBackendTarget.replace(/^http/, 'ws'),
      ws: true,
      changeOrigin: true,
      secure: false,
    }
    // 数据大屏页面
    serverProxy['/dashboard'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      secure: false,
    }
    // 统计 API
    serverProxy['/api/statistic'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      xfwd: true,
      secure: false,
    }
    // IP 查询 API
    serverProxy['/api/ip'] = {
      target: chatBackendTarget,
      changeOrigin: true,
      xfwd: true,
      secure: false,
    }
  }

  return {
    base: '/RAGWEB/',
    plugins: [
      vue(),
      vueDevTools(),
      ...(!usePythonChatBackend ? [chatApiPlugin()] : []),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
    server: {
      proxy: serverProxy,
    },
    preview: {
      proxy: serverProxy,
    },
  }
})
