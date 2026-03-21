import type { Connect, Plugin } from 'vite'
import type { IncomingMessage, ServerResponse } from 'node:http'
import { loadEnv } from 'vite'
import mysql from 'mysql2/promise'

function sendJson(res: ServerResponse, status: number, data: unknown) {
    res.writeHead(status, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(data))
}

function readBody(req: IncomingMessage): Promise<Record<string, unknown>> {
    return new Promise((resolve) => {
        let raw = ''
        req.on('data', (chunk: Buffer) => (raw += chunk.toString()))
        req.on('end', () => {
            try {
                resolve(JSON.parse(raw || '{}'))
            } catch {
                resolve({})
            }
        })
    })
}

export function chatApiPlugin(): Plugin {
    let pool: mysql.Pool | null = null
    let schemaInitPromise: Promise<void> | null = null

    const ensureSchema = async () => {
        if (!pool) {
            throw new Error('数据库连接池未初始化，请检查 DB_* 环境变量')
        }
        if (!schemaInitPromise) {
            schemaInitPromise = (async () => {
                await pool!.execute(`
                    CREATE TABLE IF NOT EXISTS chat_users (
                        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(64) NOT NULL UNIQUE,
                        create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                `)
                await pool!.execute(`
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT UNSIGNED NOT NULL,
                        session_id VARCHAR(64) NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_session_time (user_id, session_id, create_time),
                        CONSTRAINT fk_chat_sessions_user
                          FOREIGN KEY (user_id) REFERENCES chat_users(id)
                          ON UPDATE CASCADE ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                `)
            })().catch((error) => {
                schemaInitPromise = null
                throw error
            })
        }
        await schemaInitPromise
    }

    const ensureUserIdByUsername = async (usernameRaw: string): Promise<number> => {
        if (!pool) {
            throw new Error('数据库连接池未初始化，请检查 DB_* 环境变量')
        }
        const username = usernameRaw.trim() || 'default_user'
        await pool.execute('INSERT IGNORE INTO chat_users (username) VALUES (?)', [username])
        const [rows] = await pool.execute('SELECT id FROM chat_users WHERE username = ? LIMIT 1', [username])
        const userRows = rows as Array<{ id: number }>
        if (!userRows.length) {
            throw new Error('用户创建或查询失败')
        }
        return userRows[0]!.id
    }

    const chatMiddleware: Connect.NextHandleFunction = async (
        req: IncomingMessage,
        res: ServerResponse,
        next: () => void,
    ) => {
        const rawUrl = req.url ?? ''
        if (!rawUrl.startsWith('/api/chat/')) return next()

        if (!pool) {
            return sendJson(res, 500, { code: 500, message: '数据库连接池未初始化，请检查 DB_* 环境变量' })
        }

        await ensureSchema()

        const urlObj = new URL(rawUrl, 'http://localhost')
        const pathname = urlObj.pathname
        const method = req.method ?? ''

        try {
            // POST /api/chat/record
            if (method === 'POST' && pathname === '/api/chat/record') {
                const body = await readBody(req)
                const username = (body.user_id as string) || 'default_user'
                const { session_id, question, answer } = body as Record<string, string>
                if (!session_id || !question || !answer) {
                    return sendJson(res, 400, { code: 400, message: '缺少必要字段：session_id/question/answer' })
                }

                const user_id = await ensureUserIdByUsername(username)
                const [result] = await pool.execute(
                    'INSERT INTO chat_sessions (user_id, session_id, question, answer) VALUES (?, ?, ?, ?)',
                    [user_id, session_id, question, answer],
                )
                const okResult = result as mysql.OkPacket
                return sendJson(res, 200, { code: 200, message: '保存成功', data: { id: okResult.insertId } })
            }

            // /api/chat/records/:session_id
            const recordsMatch = pathname.match(/^\/api\/chat\/records\/(.+)$/)
            if (recordsMatch) {
                const session_id = decodeURIComponent(recordsMatch[1])
                const username = urlObj.searchParams.get('user_id') ?? 'default_user'
                const [userRows] = await pool.execute('SELECT id FROM chat_users WHERE username = ? LIMIT 1', [username])
                const matchedUsers = userRows as Array<{ id: number }>
                const user_id = matchedUsers[0]?.id

                if (method === 'GET') {
                    if (!user_id) {
                        return sendJson(res, 200, { code: 200, message: '获取成功', data: [] })
                    }
                    const [rows] = await pool.execute(
                        'SELECT id, question, answer, create_time FROM chat_sessions WHERE session_id = ? AND user_id = ? ORDER BY create_time ASC, id ASC',
                        [session_id, user_id],
                    )
                    const turns = rows as Array<{ id: number; question: string; answer: string; create_time: string }>
                    const messages = turns.flatMap((turn) => [
                        {
                            id: `${turn.id}-u`,
                            role: 'user',
                            content: turn.question,
                            create_time: turn.create_time,
                        },
                        {
                            id: `${turn.id}-a`,
                            role: 'assistant',
                            content: turn.answer,
                            create_time: turn.create_time,
                        },
                    ])
                    return sendJson(res, 200, { code: 200, message: '获取成功', data: messages })
                }

                if (method === 'DELETE') {
                    if (!user_id) {
                        return sendJson(res, 200, { code: 200, message: '删除成功', data: { affectedRows: 0 } })
                    }
                    const [result] = await pool.execute(
                        'DELETE FROM chat_sessions WHERE session_id = ? AND user_id = ?',
                        [session_id, user_id],
                    )
                    const okResult = result as mysql.OkPacket
                    return sendJson(res, 200, { code: 200, message: '删除成功', data: { affectedRows: okResult.affectedRows } })
                }
            }

            // GET /api/chat/sessions/:user_id
            const sessionsMatch = pathname.match(/^\/api\/chat\/sessions\/(.+)$/)
            if (method === 'GET' && sessionsMatch) {
                const username = decodeURIComponent(sessionsMatch[1])
                const user_id = await ensureUserIdByUsername(username)
                const [rows] = await pool.execute(
                    `SELECT cs.session_id,
                                            MAX(cs.create_time) AS last_time,
                                            MIN(cs.create_time) AS create_time,
                                            (SELECT question FROM chat_sessions
                                             WHERE session_id = cs.session_id AND user_id = cs.user_id
                                             ORDER BY create_time ASC, id ASC LIMIT 1) AS first_message
                             FROM chat_sessions cs
                             WHERE cs.user_id = ?
                             GROUP BY cs.session_id, cs.user_id
               ORDER BY last_time DESC`,
                    [user_id],
                )
                return sendJson(res, 200, { code: 200, message: '获取成功', data: rows })
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : '未知错误'
            return sendJson(res, 500, { code: 500, message: '服务器错误', error: message })
        }

        next()
    }

    return {
        name: 'vite-plugin-chat-api',

        config(_, { mode }) {
            const env = loadEnv(mode, process.cwd(), '')
            pool = mysql.createPool({
                host: env.DB_HOST,
                port: Number(env.DB_PORT) || 3306,
                user: env.DB_USER,
                password: env.DB_PASSWORD,
                database: env.DB_DATABASE,
                waitForConnections: true,
                connectionLimit: 10,
                connectTimeout: 60000,
            })
        },

        configureServer(server) {
            server.middlewares.use(chatMiddleware)
        },

        configurePreviewServer(server) {
            server.middlewares.use(chatMiddleware)
        },
    }
}
