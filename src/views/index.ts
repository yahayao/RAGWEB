// 数据库存储类型：一条记录表示一轮对话
export interface ChatRecord {
  user_id?: string;       // 可选，默认default_user
  session_id: string;     // 必选，会话ID
  question: string;       // 用户问题
  answer: string;         // AI回复
}

// （可选）AI响应类型补充（如果需要）
export interface AiResponse {
  id: string;
  content: string;
}