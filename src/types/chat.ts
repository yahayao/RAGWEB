// src/types/chat.ts
// 对话消息（前端展示用）
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: number
}

/** POST /api/rag/chat 请求体 */
export interface ChatRequest {
  question: string
  session_id: string
  stream?: boolean
}

/** 匿名会话引导返回 */
export interface AuthSessionData {
  id: number | string
  username: string
  auth_token: string
  region?: string
  country_code?: string | null
  country_name?: string
  manual_geo?: boolean
}

/** POST /api/rag/chat 响应体 */
export interface ChatResponse {
  id: string
  object: string
  created: number
  question: string
  choices: {
    index: number
    message: {
      role: 'assistant'
      content: string
    }
    finish_reason: string
  }[]
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

/** 前端使用的会话聚合结构：一个会话下包含多条消息（Message[]） */
export interface ChatSession {
  id: string          // 会话ID
  title?: string      // 对话标题（可选）
  createTime: number  // 创建时间戳
  messages: Message[] // 该会话下的所有消息
}

/** 与后端保存接口对齐：一轮对话记录（用户问题 + AI回复） */
export interface ChatRecord {
  user_id: string                   // 用户UID（系统生成的 UUID）
  session_id: string                // 会话/对话ID
  question: string                  // 用户问题
  answer: string                    // AI回复
}

