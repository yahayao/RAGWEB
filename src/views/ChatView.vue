<template>
  <div class="chat-container" :class="{ 'dark-theme': chatStore.isDarkTheme }">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <img class="brand-icon" src="/asset/avatar/AI.jpg" alt="AI" />
        <span class="brand-name">BNBU招生问答助手</span>
      </div>

      <button class="new-session-btn" @click="chatStore.createNewSession()">
        <span class="btn-icon">+</span>
        <span>新对话</span>
      </button>

      <div class="session-section-title">最近对话</div>
      <div class="session-list">
        <div v-for="session in chatStore.sessions" :key="session.id"
          :class="['session-item', { active: session.id === chatStore.currentSessionId }]"
          @click="chatStore.switchSession(session.id)">
          <span class="session-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="13" height="13">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor"
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span class="session-title">{{ session.title }}</span>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-info-bar">
          <div class="user-avatar-small">{{ (chatStore.currentDisplayName || chatStore.currentUserId).charAt(0).toUpperCase() }}</div>
          <span class="user-name-text">{{ chatStore.currentDisplayName || chatStore.currentUserId }}</span>
        </div>
        <button class="theme-toggle-btn" @click="chatStore.toggleTheme()">
          <span class="theme-icon">
            <svg v-if="chatStore.isDarkTheme" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"
              width="14" height="14">
              <circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2" />
              <path
                d="M12 2v2M12 20v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M2 12h2M20 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="14" height="14">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span>{{ chatStore.isDarkTheme ? '浅色模式' : '深色模式' }}</span>
        </button>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="chat-main">
      <!-- 顶部标题栏 -->
      <div class="chat-header">
        <div class="header-title">
          <img class="header-avatar" src="/asset/avatar/AI.jpg" alt="AI" />
          <div>
            <div class="header-name">BNBU招生问答助手</div>
            <div class="header-status">
              <span class="status-dot"></span>
              在线
            </div>
          </div>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <div v-for="message in chatStore.messages" :key="message.id" :class="['message-row', message.role]">
          <img v-if="message.role === 'assistant'" class="avatar assistant-avatar" src="/asset/avatar/AI.jpg"
            alt="AI" />
          <div class="bubble-wrapper">
            <div class="thinking-indicator"
              v-if="message.role === 'assistant' && isCurrentStreamingAssistantMessage(message) && !message.content">
              思考中
            </div>
            <div class="message-bubble" :class="{ 'markdown-body': message.role === 'assistant' }"
              v-if="message.role === 'assistant'" v-html="renderMarkdown(message.content)"></div>
            <div class="message-bubble" v-else>{{ message.content }}</div>
          </div>
          <div v-if="message.role === 'user'" class="avatar user-avatar">你</div>
        </div>

        <!-- 非流式等待动画 -->
        <div v-if="chatStore.isCurrentSessionLoading && !chatStore.isStreaming" class="message-row assistant">
          <img class="avatar assistant-avatar" src="/asset/avatar/AI.jpg" alt="AI" />
          <div class="bubble-wrapper">
            <div class="thinking-indicator">思考中</div>
            <div class="message-bubble loading-bubble">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
        <div v-if="showContextLimitTip" class="context-limit-tip">对话轮次已达到上限，请开启新对话</div>
      </div>

      <!-- 底部输入区 -->
      <div class="input-wrapper">
        <div v-if="chatStore.contactModalState === 'dismissed'" class="quick-contact-banner">
          找不到人工入口？<a href="#" @click.prevent="openContactModal">点击这里联系招生老师</a>
        </div>
        <div class="input-box">
          <textarea v-model="inputText" placeholder="发送消息给 AI 助手..." @keydown.enter.exact.prevent="handleSend"
            rows="1"></textarea>
          <!-- 新增的麦克风按钮 -->
          <button class="send-btn" style="margin-right: 8px;" :class="{ 'recording': isRecording }"
            @click="toggleRecording" :title="isRecording ? '停止录音' : '语音输入'">
            <svg v-if="!isRecording" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="16"
              height="16">
              <path d="M12 2C10.9 2 10 2.9 10 4V12C10 13.1 10.9 14 12 14C13.1 14 14 13.1 14 12V4C14 2.9 13.1 2 12 2Z"
                fill="currentColor" />
              <path
                d="M19 10V12C19 15.9 15.9 19 12 19C8.1 19 5 15.9 5 12V10H7V12C7 14.8 9.2 17 12 17C14.8 17 17 14.8 17 12V10H19Z"
                fill="currentColor" />
              <path d="M11 19V21H13V19H11Z" fill="currentColor" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
              <rect x="6" y="6" width="12" height="12" fill="currentColor" />
            </svg>
          </button>
          <button class="send-btn" @click="handleSend" :disabled="!inputText.trim() || chatStore.isCurrentSessionLoading"
            title="发送 (Enter)">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" />
            </svg>
          </button>
        </div>
        <div class="input-hint">按 Enter 发送，Shift+Enter 换行</div>
      </div>
    </main>

    <!-- 用户设置弹窗（仅首次使用） -->
    <div v-if="showUserModal" class="modal-overlay">
      <div class="modal-box">
        <div class="modal-title">欢迎使用BNBU招生问答助手</div>
        <p class="modal-desc">请输入您的称呼，用于保存和恢复对话记录</p>
        <input class="modal-input" v-model="userIdInput" placeholder="输入您的称呼（如：张三）"
          @keydown.enter="confirmUserId" maxlength="30" />
        <div class="modal-actions">
          <button class="modal-confirm-btn" :disabled="!userIdInput.trim()" @click="confirmUserId">
            开始使用
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="showContactModal" class="modal-overlay" @click.self="closeModal">
    <div class="modal-box">
      <div class="modal-title">📞 老师将尽快联系您</div>
      <p class="modal-desc">请输入您的联系方式，我们将安排招生老师为您详细解答。</p>
      <div class="modal-input-group">
        <input v-model="contactForm.phone" type="tel" placeholder="手机号 (必填)" class="modal-input"
          :class="{ 'input-error-border': phoneError }" @keydown.enter="submitContactForm"
          @input="validatePhoneOnInput" />
        <p v-if="phoneError" class="phone-error-text">{{ phoneError }}</p>
      </div>
      <div class="modal-actions">
        <button class="modal-cancel-btn" @click="handleModalCancel">取消</button>
        <button class="modal-confirm-btn" @click="submitContactForm" :disabled="!isPhoneValid">
          提交并联系老师
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { useChatStore } from '../store/chat'
import { sendMessage, sendMessageStream } from '../api/chat'
import type { Message, ChatRequest, HistoryItem } from '../types'
import RecordRTC from 'recordrtc'
import { marked } from 'marked'
import DOMPurify from 'dompurify'


// ===== 新增代码（仅加这两行）=====
import { saveChatRecord, registerUser } from '../api/chat' // 导入保存数据库的接口
import type { ChatRecord } from '../types/chat' // 导入数据库记录类型
import { sendAlertToTeacher } from '../api/chat'

marked.setOptions({ breaks: true, gfm: true })

const markdownLinkPattern = /\[[^\]]+\]\([^)]+\)/g
const rawUrlPattern = /https?:\/\/[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%]+/g
const trailingUrlPunctuationPattern = /[),.?!;:，。；：！？）】》]+$/u
const showContactModal = ref(false)
const contactForm = ref({
  phone: ''
})

const phoneError = ref('')

const validatePhone = (phone: string): string => {
  const cleaned = phone.replace(/\s+/g, '')
  if (!cleaned) return ''
  if (!/^1\d{10}$/.test(cleaned)) return '请输入正确的11位手机号'
  return ''
}

const isPhoneValid = computed(() => {
  if (!contactForm.value.phone) return false
  return !validatePhone(contactForm.value.phone)
})

const validatePhoneOnInput = () => {
  phoneError.value = validatePhone(contactForm.value.phone)
}


// ===== 关键词常量定义 =====
const KEYWORDS = {
  HIGH_INTENT: [
    '第一志愿', '第一选择', '很想来', '想把贵校', '冲一冲', '稳录', '保底',
    '能报吗', '有希望吗', '机会大吗', '能上吗', '能进吗', '能被录取', '稳不稳',
    '加微信', '加老师', '电话', '联系方式'
  ],
  URGENT: [
    '投诉', '举报', '不合理', '不一样', '有问题', '不满意', '离谱', '欺骗',
    '截止', '马上', '着急', '来不及', '报错', '失败', '申诉', '人工'
  ]
}

const checkForKeywords = (text: string): { match: boolean; type: 'high_intent' | 'urgent'; words: string[] } => {
  let foundWords: string[] = []

  const highIntentMatches = KEYWORDS.HIGH_INTENT.filter(word => text.includes(word))
  if (highIntentMatches.length > 0) {
    foundWords = foundWords.concat(highIntentMatches)
  }

  const urgentMatches = KEYWORDS.URGENT.filter(word => text.includes(word))
  if (urgentMatches.length > 0) {
    foundWords = foundWords.concat(urgentMatches)
  }

  if (foundWords.length > 0) {
    const type = urgentMatches.length > 0 ? 'urgent' : 'high_intent'
    return { match: true, type, words: foundWords }
  }

  return { match: false, type: 'high_intent', words: [] }
}

const linkifyPlainTextUrls = (plainText: string): string => {
  return plainText.replace(rawUrlPattern, (matched: string, offset: number, source: string) => {
    const prevChar = offset > 0 ? source[offset - 1] : ''
    const nextChar = offset + matched.length < source.length ? source[offset + matched.length] : ''

    // 保留 <https://example.com> 这类已显式包裹的 URL，不重复改写
    if (prevChar === '<' && nextChar === '>') {
      return matched
    }

    const trimmed = matched.replace(trailingUrlPunctuationPattern, '')
    const trailing = matched.slice(trimmed.length)

    if (!trimmed) {
      return matched
    }

    return `[${trimmed}](${trimmed})${trailing}`
  })
}

const linkifyRawUrls = (content: string): string => {
  let result = ''
  let lastIndex = 0

  for (const match of content.matchAll(markdownLinkPattern)) {
    const matchText = match[0]
    const matchIndex = match.index ?? 0
    result += linkifyPlainTextUrls(content.slice(lastIndex, matchIndex))
    result += matchText
    lastIndex = matchIndex + matchText.length
  }

  result += linkifyPlainTextUrls(content.slice(lastIndex))
  return result
}

const renderMarkdown = (content: string): string => {
  if (!content) return ''
  const normalizedContent = linkifyRawUrls(content)
  const raw = marked.parse(normalizedContent) as string
  return DOMPurify.sanitize(raw)
}

const chatStore = useChatStore()
const inputText = ref('')
const showUserModal = ref(false)
const userIdInput = ref('')
const userIp = ref('')
const showContextLimitTip = ref(false)
const contextOverflowMessage = '输入内容过长，已超过模型上下文长度上限，请精简后重试。'

const getUserIp = async () => {
  try {
    const response = await fetch('/api/ip/lookup')
    const data = await response.json()
    if (data.code === 200 && data.data) {
      userIp.value = data.data.ip
    } else {
      userIp.value = '未知 IP'
    }
  } catch (error) {
    console.error('获取用户 IP 失败:', error)
    userIp.value = '未知 IP'
  }
}

const confirmUserId = async () => {
  const name = userIdInput.value.trim()
  if (!name) return
  try {
    const { data } = await registerUser(name)
    if (data.code === 200) {
      chatStore.setUserInfo(String(data.data.id), data.data.username)
    } else {
      alert(data.message || '注册失败，请重试')
      return
    }
  } catch {
    alert('网络错误，请重试')
    return
  }
  showUserModal.value = false
  userIdInput.value = ''
  await initAfterLogin()
}

const initAfterLogin = async () => {
  await chatStore.loadSessionsFromDB()
  if (chatStore.messages.length === 0) {
    chatStore.addMessage({
      id: 'welcome',
      content: '您好！我是 AI 助手，有什么我能帮您的吗？',
      role: 'assistant',
      timestamp: Date.now(),
    })
  }
  scrollToBottom()
}

const isRecording = ref(false)
const isRecordingToggling = ref(false)
let recorder: RecordRTC | null = null
let audioStream: MediaStream | null = null   // 新增：用于保存音频流

const toggleRecording = async () => {
  // 防止在录音状态切换过程中被并发重复触发
  if (isRecordingToggling.value) {
    return
  }
  isRecordingToggling.value = true
  try {
    if (isRecording.value) {
      await stopRecording()
    } else {
      // 如果 recorder 或 audioStream 还存在，强制清理
      if (recorder || audioStream) {
        if (audioStream) {
          audioStream.getTracks().forEach(track => track.stop())
          audioStream = null
        }
        if (recorder) {
          // 尝试停止 recorder（避免残留）
          try { recorder.stopRecording() } catch (e) { }
          recorder = null
        }
      }
      await startRecording()
    }
  } finally {
    isRecordingToggling.value = false
  }
}

const startRecording = async () => {
  //console.log('startRecording called')
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true })   // 保存到 audioStream
    //console.log('Got stream')
    recorder = new RecordRTC(audioStream, {   // 使用 audioStream 创建 recorder
      type: 'audio',
      mimeType: 'audio/wav',
      recorderType: RecordRTC.StereoAudioRecorder,
      numberOfAudioChannels: 1,
      desiredSampRate: 16000,
      checkForInactiveTracks: true,
    })
    recorder.startRecording()
    isRecording.value = true
    //console.log('Recording started')
  } catch (err) {
    console.error('startRecording error:', err)
    alert('无法访问麦克风，请检查权限')
  }
}

const stopRecording = () => {
  //console.log('stopRecording called')
  return new Promise<void>((resolve) => {
    if (!recorder) {
      //console.log('No recorder, resolving')
      return resolve()
    }
    const currentRecorder = recorder
    currentRecorder.stopRecording(async () => {
      //console.log('Recording stopped')
      const blob = currentRecorder.getBlob()
      const text = await sendAudioToWhisper(blob)
      if (text) {
        inputText.value = text
        // handleSend() // 可取消注释自动发送
      }
      // 关闭音频轨道（使用 audioStream）
      if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop())
        audioStream = null
      }
      recorder = null
      isRecording.value = false
      //console.log('Cleanup done')
      resolve()
    })
  })
}

const sendAudioToWhisper = async (audioBlob: Blob): Promise<string> => {
  const formData = new FormData()
  // 后端通常通过 file 字段接收 UploadFile
  formData.append('file', audioBlob, `recording-${Date.now()}.wav`)

  // 使用 AbortController 为 fetch 添加超时控制，避免网络异常时长时间挂起
  const controller = new AbortController()
  // 可以根据需要调整超时时长（毫秒）
  const TIMEOUT_MS = 15000
  const timeoutId = setTimeout(() => {
    controller.abort()
  }, TIMEOUT_MS)

  try {
    const WHISPER_URL = 'http://localhost:7860/transcribe'
    console.log('Whisper URL:', WHISPER_URL)
    const response = await fetch(WHISPER_URL, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    })
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    const data = await response.json()
    if (data.text) {
      return data.text
    } else {
      chatStore.addMessage({
        id: Date.now().toString(),
        content: '语音识别失败：' + (data.error || '未知错误'),
        role: 'assistant',
        timestamp: Date.now(),
      })
      return ''
    }
  } catch (err: unknown) {
    console.error('语音识别服务错误:', err)
    // 区分超时取消与其他错误，提示信息更明确
    const isAbortError = err instanceof DOMException && err.name === 'AbortError'
    const message =
      isAbortError
        ? '语音识别请求超时，请稍后重试。'
        : '无法连接到语音识别服务，请确保服务已启动。'
    chatStore.addMessage({
      id: Date.now().toString(),
      content: message,
      role: 'assistant',
      timestamp: Date.now(),
    })
    return ''
  } finally {
    clearTimeout(timeoutId)
  }
}

const messageListRef = ref<HTMLElement | null>(null)

const isThinkingInProgress = (content: string) => {
  const start = content.indexOf('<think>')
  if (start === -1) return false
  return content.indexOf('</think>', start) === -1
}

const isCurrentStreamingAssistantMessage = (message: Message) => {
  if (!chatStore.isCurrentSessionLoading || !chatStore.isStreaming) return false
  if (message.role !== 'assistant') return false

  const lastMessage = chatStore.messages[chatStore.messages.length - 1]
  if (!lastMessage) return false
  return lastMessage.id === message.id
}

const isContextLengthExceededError = (errorMsg: string) => {
  return /CONTEXT_OVERFLOW|context_length_exceeded|maximum\s+context\s+length|max\s*context\s*length|context\s*window|too\s+many\s+tokens|token\s+limit|input\s+is\s+too\s+long|prompt\s+is\s+too\s+long|超出.{0,8}上下文|上下文.{0,8}(超|长|限)|输入内容过长|轮次上限/i.test(
    errorMsg,
  )
}

const getDisplayContent = (content: string) => content.trim()

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const handleSend = async () => {
  // 1. 先检查输入和加载状态（仅检查当前会话），若不满足直接返回
  if (!inputText.value.trim() || chatStore.isCurrentSessionLoading) return

  // 记录发送时的会话上下文，回调中直接操作目标 session 数组
  const sessionIdAtSend = chatStore.currentSessionId
  const sessionAtSend = chatStore.sessions.find(s => s.id === sessionIdAtSend)
  const sessionMessagesAtSend: Message[] = sessionAtSend?.messages ?? []

  showContextLimitTip.value = false

  // 2. 立即设置当前会话的加载状态
  chatStore.setSessionLoading(sessionIdAtSend, true)

  // 3. 构建并添加用户消息
  const userMessage: Message = {
    id: Date.now().toString(),
    content: inputText.value,
    role: 'user',
    timestamp: Date.now(),
  }

  chatStore.addMessage(userMessage)

  // 4. 清空输入框并滚动到底部
  const userinput = inputText.value
  inputText.value = ''
  scrollToBottom()

  // 5. 构建历史记录和请求参数
  const allMessages = chatStore.messages
  const history: HistoryItem[] = allMessages
    .slice(0, -1)
    .filter((m) => m.id !== 'welcome')
    .map((m) => ({ role: m.role, content: m.content }))

  const requestData: ChatRequest = {
    question: userMessage.content,
    history: history.length > 0 ? history : undefined,
  }

  const checkAndShowAlert = () => {
    console.log("【DEBUG】当前 contactModalState:", chatStore.contactModalState);
    const userInputCheck = checkForKeywords(userinput)
    console.log("【DEBUG】关键词匹配结果:", userInputCheck);
    if (userInputCheck.match) {
      if (chatStore.contactModalState === 'idle') {
        chatStore.setPendingAlert(userInputCheck.type, userinput)
        showContactModal.value = true
      }
    }
  };

  // 6. 区分流式/普通模式处理
  if (chatStore.isStreaming) {
    // 流式模式：先添加空的 AI 消息，再逐步更新内容
    const assistantMessage: Message = {
      id: `stream-${Date.now()}`,
      content: '',
      role: 'assistant',
      timestamp: Date.now(),
    }
    chatStore.addMessage(assistantMessage)
    const msgId = assistantMessage.id
    let streamedContent = ''

    sendMessageStream(
      requestData,
      (chunk: string) => {
        streamedContent += chunk
        // 直接写目标 session 的 messages 数组，不受视图切换影响
        const target = sessionMessagesAtSend.find(m => m.id === msgId)
        if (target) target.content = streamedContent
        // 如果当前仍在查看该会话，同步更新视图（保持与 switchSession 后的引用一致）
        if (chatStore.currentSessionId === sessionIdAtSend) {
          const viewMsg = chatStore.messages.find(m => m.id === msgId)
          if (viewMsg) viewMsg.content = streamedContent
        }
        scrollToBottom()
      },
      () => {
        // 使用发送时的 sessionId，而非回调执行时的 currentSessionId
        (async () => {
          try {
            const chatRecord: ChatRecord = {
              user_id: chatStore.currentUserId,
              session_id: sessionIdAtSend,
              question: userMessage.content,
              answer: streamedContent,
            }
            await saveChatRecord(chatRecord)
            console.log('✅ 对话轮次（流式）已提交到数据库接口')
          } catch (error) {
            console.error('❌ 保存消息失败：', error)
          }
        })()

        checkAndShowAlert();
        showContextLimitTip.value = false
        chatStore.setSessionLoading(sessionIdAtSend, false)
        scrollToBottom()
      },
      (error: Error) => {
        console.error('流式传输错误:', error)
        const isContextOverflow = isContextLengthExceededError(error.message)
        showContextLimitTip.value = isContextOverflow
        if (!streamedContent) {
          if (isContextOverflow) {
            chatStore.removeMessage(msgId)
            chatStore.setSessionLoading(sessionIdAtSend, false)
            scrollToBottom()
            return
          }

          const isTimeout = /超时|timeout/i.test(error.message)
          chatStore.updateMessageContent(
            msgId,
            isTimeout
              ? '请求超时，请检查网络后重试。'
              : '抱歉，发送失败了，请稍后再试。'
          )
        }
        chatStore.setSessionLoading(sessionIdAtSend, false)
        scrollToBottom()
      }
    )
  } else {
    // 普通模式：等待接口响应后添加 AI 消息
    try {
      const response = await sendMessage(requestData)
      const assistantMessage: Message = {
        id: Date.now().toString(),
        content: response.choices[0]?.message?.content ?? '（无响应内容）',
        role: 'assistant',
        timestamp: Date.now(),
      }
      chatStore.addMessage(assistantMessage)
      showContextLimitTip.value = false
      scrollToBottom()

      checkAndShowAlert();

      // ===== 修改：只有成功获得AI响应才保存用户和AI消息到数据库 =====
      try {
        const chatRecord: ChatRecord = {
          user_id: chatStore.currentUserId,
          session_id: sessionIdAtSend,
          question: userMessage.content,
          answer: assistantMessage.content,
        }
        await saveChatRecord(chatRecord)
        console.log('✅ 对话轮次（普通）已提交到数据库接口')
      } catch (error) {
        console.error('❌ 保存消息失败：', error)
      }

    } catch (error) {
      console.error('发送消息失败:', error)
      const errorMsg = error instanceof Error ? error.message : String(error)
      const isContextOverflow = isContextLengthExceededError(errorMsg)
      showContextLimitTip.value = isContextOverflow
      const isTimeout = /超时|timeout|ECONNABORTED/i.test(errorMsg)
      if (!isContextOverflow) {
        chatStore.addMessage({
          id: Date.now().toString(),
          content: isTimeout
            ? '请求超时，请检查网络后重试。'
            : '抱歉，发送失败了，请稍后再试。',
          role: 'assistant',
          timestamp: Date.now(),
        })
      }
      scrollToBottom()
    } finally {
      chatStore.setSessionLoading(sessionIdAtSend, false)
    }
  }

}

const submitContactForm = async () => {
  const err = validatePhone(contactForm.value.phone)
  phoneError.value = err
  if (err || !contactForm.value.phone) return

  try {
    await sendAlertToTeacher({
      contact: contactForm.value.phone,
      sessionId: chatStore.currentSessionId,
      intentType: chatStore.pendingAlertType || 'high_intent',
      messageSnippet: '用户触发了高意向关键词',
      studentName: chatStore.currentDisplayName || chatStore.currentUserId,
    })
    contactForm.value.phone = ''
  } catch (error) {
    alert('提交失败，请稍后重试')
  }
}

const openContactModal = () => {
  showContactModal.value = true
}

const handleModalCancel = () => {
  showContactModal.value = false
  chatStore.markContactDismissed()
}

const closeModal = () => {
  showContactModal.value = false
  // 可选：清空已输入的手机号，下次打开是干净的
  contactForm.value.phone = ''
}

onMounted(async () => {
  if (!chatStore.currentUserId) {
    showUserModal.value = true
  } else if (!chatStore.currentDisplayName) {
    // 旧版本用户：localStorage 有 chat_user_id 但没有 chat_display_name
    // 需要重新注册
    showUserModal.value = true
  } else {
    await initAfterLogin()
  }
})

onBeforeUnmount(() => {
  // 如果正在录音，立即停止并关闭轨道
  if (recorder && isRecording.value) {
    try {
      recorder.stopRecording(); // 尝试停止录制（可能来不及完成，但尽力）
    } catch (e) { }
  }
  // 无论是否正在录音，关闭音频轨道
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
    audioStream = null;
  }
  recorder = null;
  isRecording.value = false;
});

watch(
  () => chatStore.isDarkTheme,
  (newVal) => {
    if (newVal) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
  { immediate: true }
)

watch(
  () => chatStore.currentSessionId,
  () => {
    showContextLimitTip.value = false
  },
)
</script>

<style scoped>
/* ============================================
   ChatView — 精修视觉
   深海侧边栏 + 柔和主区域 + 靛蓝点缀
   ============================================ */

/* ---- 布局容器 ---- */
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-primary);
  background: var(--color-bg-gradient);
  transition: background 0.8s var(--ease-in-out);
}

/* ---- 深色模式 —— 覆盖颜色变量 ---- */
/* 深色基础（夜晚默认，18:00–6:00 最深） */
.chat-container.dark-theme {
  --color-bg: #0b1120;
  --color-bg-gradient: var(--bg-gradient-dark-evening);
  --color-surface: #111827;
  --color-border: #1f2937;
  --color-border-light: #1a2236;
  --color-text-primary: #f1f5f9;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #64748b;
  --color-primary-light: rgba(99, 102, 241, 0.1);
  --color-sidebar-bg: rgba(23, 28, 45, 0.78);
  --color-sidebar-text: #cbd5e1;
  --color-sidebar-text-muted: #4b5563;
  --color-sidebar-hover: rgba(99, 102, 241, 0.08);
  --color-sidebar-active: rgba(99, 102, 241, 0.14);
  --color-sidebar-border: rgba(255, 255, 255, 0.06);
}

/* 深色-白天 (6:00–18:00)：藏蓝 → 暗靛 → 深灰紫，偏亮 */
[data-time-theme="morning"] .chat-container.dark-theme {
  --color-bg-gradient: var(--bg-gradient-dark-daytime);
}

/* 深色-夜晚 (18:00–6:00)：显式覆盖确保不变 */
[data-time-theme="evening"] .chat-container.dark-theme {
  --color-bg-gradient: var(--bg-gradient-dark-evening);
}

/* ========================================
   左侧边栏 — 浅色模式
   ======================================== */
.chat-container:not(.dark-theme) .sidebar {
  background: rgba(237, 243, 252, 0.68);
  border-right-color: rgba(193, 207, 232, 0.45);
}

.chat-container:not(.dark-theme) .sidebar-brand {
  border-bottom-color: #e2e8f0;
}

.chat-container:not(.dark-theme) .brand-name {
  color: #1e293b;
}

.chat-container:not(.dark-theme) .new-session-btn {
  background: rgba(99, 102, 241, 0.08);
  color: #4f46e5;
  border-color: rgba(99, 102, 241, 0.15);
}

.chat-container:not(.dark-theme) .new-session-btn:hover {
  background: rgba(99, 102, 241, 0.16);
  color: #4338ca;
  border-color: rgba(99, 102, 241, 0.3);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12);
}

.chat-container:not(.dark-theme) .session-section-title {
  color: #94a3b8;
}

.chat-container:not(.dark-theme) .session-item {
  color: #475569;
}

.chat-container:not(.dark-theme) .session-item:hover {
  background: rgba(99, 102, 241, 0.06);
  color: #334155;
}

.chat-container:not(.dark-theme) .session-item.active {
  background: rgba(99, 102, 241, 0.1);
  color: #4338ca;
}

.chat-container:not(.dark-theme) .session-icon {
  opacity: 0.4;
}

.chat-container:not(.dark-theme) .session-item.active .session-icon {
  opacity: 0.8;
}

.chat-container:not(.dark-theme) .sidebar-footer {
  border-top-color: #e2e8f0;
}

.chat-container:not(.dark-theme) .user-info-bar:hover {
  background: rgba(99, 102, 241, 0.06);
}

.chat-container:not(.dark-theme) .user-name-text {
  color: #475569;
}

/* ========================================
   左侧边栏（深色基础）
   ======================================== */
.sidebar {
  width: 272px;
  min-width: 272px;
  background: var(--color-sidebar-bg);
  backdrop-filter: blur(24px) saturate(1.3);
  -webkit-backdrop-filter: blur(24px) saturate(1.3);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  gap: 4px;
  user-select: none;
  border-right: 1px solid var(--color-sidebar-border);
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.06), 1px 0 4px rgba(0, 0, 0, 0.04);
  z-index: 5;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 2px 8px 16px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--color-sidebar-border);
}

.brand-icon {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.45);
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: #f1f5f9;
  letter-spacing: -0.2px;
}

/* 新对话按钮 */
.new-session-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: rgba(99, 102, 241, 0.12);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-md);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.new-session-btn:hover {
  background: rgba(99, 102, 241, 0.22);
  color: #c7d2fe;
  border-color: rgba(99, 102, 241, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
}

.new-session-btn:active {
  transform: translateY(0) scale(0.98);
}

.btn-icon {
  font-size: 18px;
  line-height: 1;
  font-weight: 300;
}

/* 会话标题 */
.session-section-title {
  font-size: 10.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  color: var(--color-sidebar-text-muted);
  padding: 14px 10px 6px;
}

/* 会话列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13.5px;
  color: var(--color-sidebar-text);
  transition: all var(--duration-fast) var(--ease-out);
  overflow: hidden;
  position: relative;
}

.session-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 20px;
  border-radius: 0 3px 3px 0;
  background: var(--color-primary);
  transition: transform var(--duration-fast) var(--ease-out-back);
}

.session-item:hover {
  background: var(--color-sidebar-hover);
  color: #e2e8f0;
}

.session-item.active {
  background: var(--color-sidebar-active);
  color: #c7d2fe;
  font-weight: 600;
}

.session-item.active::before {
  transform: translateY(-50%) scaleY(1);
}

.session-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  opacity: 0.45;
}

.session-item.active .session-icon {
  opacity: 0.85;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 侧边栏底部 */
.sidebar-footer {
  border-top: 1px solid var(--color-sidebar-border);
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 用户信息栏（仅展示） */
.user-info-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.user-avatar-small {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary-gradient);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-name-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-sidebar-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 主题切换按钮 */
.theme-toggle-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 14px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: var(--radius-md);
  color: #a5b4fc;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.theme-toggle-btn:hover {
  background: rgba(99, 102, 241, 0.18);
  color: #c7d2fe;
  border-color: rgba(99, 102, 241, 0.35);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.2);
  transform: translateY(-1px);
}

.theme-toggle-btn:active {
  transform: translateY(0) scale(0.97);
}

/* 浅色模式下主题按钮样式 */
.chat-container:not(.dark-theme) .theme-toggle-btn {
  background: rgba(99, 102, 241, 0.06);
  color: #4f46e5;
  border-color: rgba(99, 102, 241, 0.2);
}

.chat-container:not(.dark-theme) .theme-toggle-btn:hover {
  background: rgba(99, 102, 241, 0.14);
  color: #4338ca;
  border-color: rgba(99, 102, 241, 0.4);
  box-shadow: 0 2px 14px rgba(99, 102, 241, 0.18);
}

.theme-icon {
  display: flex;
  align-items: center;
  opacity: 0.8;
  flex-shrink: 0;
}

/* ========================================
   主聊天区
   ======================================== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
  min-width: 0;
}

/* ---- 顶部标题栏 ---- */
.chat-header {
  padding: 12px 28px;
  border-bottom: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(1.6);
  -webkit-backdrop-filter: blur(20px) saturate(1.6);
  display: flex;
  align-items: center;
  z-index: 10;
  box-shadow: var(--shadow-md);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.header-name {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.2px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: #22c55e;
  border-radius: 50%;
  animation: pulse-dot 2s infinite;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
}

@keyframes pulse-dot {

  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.4;
    transform: scale(1.5);
  }
}

/* ========================================
   消息列表
   ======================================== */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

/* ---- 消息行 ---- */
.message-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  animation: msg-in 0.35s var(--ease-out-back);
  max-width: 75%;
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.97);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.message-row.user {
  margin-left: auto;
}

.message-row.assistant {
  margin-right: auto;
}

/* ---- 头像 ---- */
.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.assistant-avatar {
  object-fit: cover;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.user-avatar {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: #fff;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.4);
}

/* ---- 气泡包装 ---- */
.bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 100%;
  min-width: 0;
}

/* 思考内容 */
.thinking-context {
  margin-bottom: 8px;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-primary-light);
  color: var(--color-text-secondary);
  font-size: 12.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.thinking-indicator {
  align-self: flex-start;
  margin-bottom: 4px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary);
  font-size: 11.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.2px;
}

.thinking-indicator::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse-dot 1.2s infinite;
}

/* ---- 消息气泡 ---- */
.message-bubble {
  padding: 12px 18px;
  border-radius: var(--radius-lg);
  font-size: 15px;
  line-height: 1.68;
  word-wrap: break-word;
  white-space: pre-wrap;
  text-wrap: pretty;
}

/* 用户气泡：靛蓝渐变 + 右下角收尖 */
.message-row.user .message-bubble {
  background: var(--color-primary-gradient);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.35), 0 1px 4px rgba(99, 102, 241, 0.2);
}

/* AI 气泡：柔和卡片 + 细腻阴影 */
.message-row.assistant .message-bubble {
  background: #fff;
  color: var(--color-text-primary);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm), 0 0 0 1px rgba(0, 0, 0, 0.02);
}

/* ========================================
   Markdown 渲染样式
   ======================================== */
.message-bubble.markdown-body {
  white-space: normal;
}

.message-bubble.markdown-body :deep(p) {
  margin: 0 0 0.55em;
}

.message-bubble.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble.markdown-body :deep(h1),
.message-bubble.markdown-body :deep(h2),
.message-bubble.markdown-body :deep(h3),
.message-bubble.markdown-body :deep(h4) {
  margin: 0.75em 0 0.35em;
  font-weight: 700;
  line-height: 1.3;
}

.message-bubble.markdown-body :deep(ul),
.message-bubble.markdown-body :deep(ol) {
  margin: 0.35em 0 0.55em;
  padding-left: 1.4em;
}

.message-bubble.markdown-body :deep(li) {
  margin-bottom: 0.2em;
}

.message-bubble.markdown-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.875em;
  padding: 0.15em 0.45em;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.06);
}

.message-row.user .message-bubble.markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.message-bubble.markdown-body :deep(pre) {
  margin: 0.55em 0;
  border-radius: var(--radius-md);
  overflow-x: auto;
  background: #1a1b26;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.message-bubble.markdown-body :deep(pre code) {
  display: block;
  padding: 1em 1.2em;
  background: transparent;
  color: #c0caf5;
  font-size: 0.83em;
  line-height: 1.65;
  white-space: pre;
}

.message-bubble.markdown-body :deep(blockquote) {
  margin: 0.45em 0;
  padding: 0.45em 0.85em;
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-light);
  border-radius: 0 6px 6px 0;
  color: var(--color-text-secondary);
}

.message-bubble.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.55em 0;
  font-size: 0.9em;
}

.message-bubble.markdown-body :deep(th),
.message-bubble.markdown-body :deep(td) {
  border: 1px solid var(--color-border);
  padding: 7px 12px;
  text-align: left;
}

.message-bubble.markdown-body :deep(th) {
  background: var(--color-primary-light);
  font-weight: 600;
}

.message-bubble.markdown-body :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.message-row.user .message-bubble.markdown-body :deep(a) {
  color: #fff;
}

.message-bubble.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 0.7em 0;
}

.message-bubble.markdown-body :deep(strong) {
  font-weight: 700;
}

.message-bubble.markdown-body :deep(em) {
  font-style: italic;
}

/* ========================================
   加载动画
   ======================================== */
.loading-bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 14px 18px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0.5);
    opacity: 0.25;
  }

  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ========================================
   底部输入区
   ======================================== */
.input-wrapper {
  padding: 16px 28px 20px;
  background: linear-gradient(180deg, transparent 0%, rgba(255, 255, 255, 0.5) 25%);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #fff;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 6px 6px 6px 14px;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-md);
}

.input-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08), var(--shadow-md);
}

/* 深度思考按钮 */
.deep-think-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out);
}

.deep-think-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.deep-think-btn.active {
  background: var(--color-primary-gradient);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 2px 10px rgba(99, 102, 241, 0.4);
}

.btn-label {
  font-size: 12px;
}

/* 文本域 */
textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 15px;
  font-family: var(--font-sans);
  line-height: 1.6;
  resize: none;
  min-height: 24px;
  max-height: 160px;
  overflow-y: auto;
  padding: 6px 0;
}

textarea::placeholder {
  color: var(--color-text-muted);
}

/* 发送 & 麦克风按钮 */
.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary-gradient);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out-back);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
}

.send-btn svg {
  width: 16px;
  height: 16px;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.1);
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.5);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.92);
}

.send-btn:disabled {
  background: var(--color-border);
  box-shadow: none;
  cursor: not-allowed;
  color: var(--color-text-muted);
}

.send-btn.recording {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.2);
  animation: record-pulse 1.5s infinite;
}

@keyframes record-pulse {

  0%,
  100% {
    box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.2);
  }

  50% {
    box-shadow: 0 0 0 12px rgba(239, 68, 68, 0);
  }
}

/* 输入提示 */
.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 8px;
  letter-spacing: 0.2px;
}

/* 上下文超限提示 */
.context-limit-tip {
  margin-bottom: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: rgba(239, 68, 68, 0.08);
  text-align: center;
  font-size: 13px;
  color: #ef4444;
  font-weight: 500;
}

/* ========================================
   弹窗（用户设置）
   ======================================== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fade-in 0.2s var(--ease-out);
}

@keyframes fade-in {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

.modal-box {
  background: #fff;
  border-radius: var(--radius-xl);
  padding: 32px 28px 24px;
  width: 400px;
  max-width: 92vw;
  box-shadow: var(--shadow-xl), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 14px;
  animation: modal-in 0.3s var(--ease-out-back);
}

@keyframes modal-in {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.95);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-title {
  font-size: 19px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.modal-desc {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.modal-input {
  width: 100%;
  padding: 11px 14px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #fff;
  color: var(--color-text-primary);
  font-size: 14px;
  font-family: var(--font-sans);
  outline: none;
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 6px;
}

.modal-confirm-btn {
  padding: 10px 22px;
  background: var(--color-primary-gradient);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.modal-confirm-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45);
}

.modal-confirm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.modal-cancel-btn {
  padding: 10px 18px;
  background: transparent;
  color: var(--color-text-secondary);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-cancel-btn:hover {
  background: var(--color-bg);
  border-color: var(--color-text-muted);
}

/* ========================================
   深色模式 — 元素覆盖
   ======================================== */
.chat-container.dark-theme .chat-header {
  background: rgba(11, 17, 32, 0.82);
  backdrop-filter: blur(20px) saturate(1.4);
  -webkit-backdrop-filter: blur(20px) saturate(1.4);
  border-bottom-color: var(--color-border);
  box-shadow: var(--shadow-md);
}

.chat-container.dark-theme .message-row.assistant .message-bubble {
  background: var(--color-surface);
  border-color: var(--color-border);
}

.chat-container.dark-theme .input-wrapper {
  background: linear-gradient(180deg, transparent 0%, rgba(11, 17, 32, 0.6) 30%);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.chat-container.dark-theme .input-box {
  background: var(--color-surface);
  border-color: var(--color-border);
}

.chat-container.dark-theme .input-box:focus-within {
  background: var(--color-surface);
  border-color: var(--color-primary);
}

.chat-container.dark-theme .modal-box {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.chat-container.dark-theme .modal-input {
  background: var(--color-bg);
}

.chat-container.dark-theme .modal-input:focus {
  background: var(--color-surface);
}

.chat-container.dark-theme .thinking-indicator {
  background: rgba(99, 102, 241, 0.12);
}

.chat-container.dark-theme .message-bubble.markdown-body :deep(pre) {
  background: #0d1117;
  border-color: var(--color-border);
}

.chat-container.dark-theme .message-bubble.markdown-body :deep(pre code) {
  color: #c9d1d9;
}

.chat-container.dark-theme .message-bubble.markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.08);
}

.chat-container.dark-theme .context-limit-tip {
  background: rgba(239, 68, 68, 0.1);
}

.chat-container.dark-theme .modal-cancel-btn:hover {
  background: var(--color-bg);
}

/* ========================================
   响应式
   ======================================== */
@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .message-row {
    max-width: 90%;
  }

  .message-list {
    padding: 16px 14px;
    gap: 14px;
  }

  .input-wrapper {
    padding: 12px 14px 16px;
  }

  .input-box {
    padding: 4px 4px 4px 10px;
    gap: 4px;
  }
}

.modal-input-group {
  margin-bottom: 20px;
}

.input-error-border {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 1px #ef4444 !important;
}

.phone-error-text {
  color: #ef4444;
  font-size: 12px;
  margin-top: 4px;
  line-height: 1.4;
}

.chat-container.dark-theme .input-error-border {
  border-color: #f87171 !important;
  box-shadow: 0 0 0 1px #f87171 !important;
}

.chat-container.dark-theme .phone-error-text {
  color: #f87171;
}

.quick-contact-banner {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  padding: 8px;
  background-color: var(--accent-light);
  border-radius: 8px;
  margin-bottom: 8px;
}

.quick-contact-banner a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
  margin-left: 4px;
}

.quick-contact-banner a:hover {
  text-decoration: underline;
}
</style>