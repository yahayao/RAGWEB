# RAGWEB Python Backend

独立 Python FastAPI 后端，提供聊天记录 CRUD、IP 地理位置查询、数据大屏、邮件告警等功能。

## API 接口

- `POST /api/chat/register` — 注册用户
- `PUT /api/chat/user-geo` — 手动更新用户地理位置
- `POST /api/chat/record` — 保存对话记录
- `GET /api/chat/records/:session_id` — 获取会话历史
- `DELETE /api/chat/records/:session_id` — 删除会话
- `GET /api/chat/sessions/:user_id` — 用户会话列表
- `GET /api/ip/lookup` — 查询 IP 归属地
- `POST /api/ip/batch-lookup` — 批量查询 IP 归属地
- `GET /api/ip/health` — GeoIP 数据库健康检查
- `GET /api/dashboard/ip-distribution` — 用户 IP 分布 + 海外统计
- `GET /api/dashboard/keywords` — 关键词词云
- `GET /api/dashboard/overview` — 数据概览
- `POST /api/alert/teacher` — 人工介入告警
- `WS /ws/dashboard` — 数据大屏 WebSocket
- `GET /api/statistic/*` — 数据统计 API

IP 地理位置使用 **MaxMind GeoLite2-City** 数据库。

---

## 1. 安装依赖

```bash
cd backend-python
pip install -r requirements.txt
```

## 2. 配置 PostgreSQL

执行数据库初始化 SQL（可重复执行）：

```bash
psql -U postgres -d ai_chat -f sql/init_geo_columns.sql
```

## 3. 注册 MaxMind 并下载 GeoLite2 数据库

1. 在 [MaxMind](https://www.maxmind.com/en/geolite2/signup) 注册账户
2. 创建 License Key
3. 配置 `/etc/GeoIP.conf`（参考 `geoip/GeoIP.conf.example`）
4. 安装 `geoipupdate` 工具
5. 首次下载：

```bash
geoipupdate -f /etc/GeoIP.conf -d /path/to/backend-python/geoip
```

6. 设置环境变量 `GEOLITE2_CITY_DB_PATH`（默认 `./geoip/GeoLite2-City.mmdb`）

> **This product includes GeoLite Data created by MaxMind.**

## 4. 配置环境变量

复制 `.env.example` 为 `.env` 并按需修改：

- `DATABASE_URL` — PostgreSQL 连接字符串
- `GEOLITE2_CITY_DB_PATH` — GeoLite2-City.mmdb 路径
- `GEOIP_RELOAD_INTERVAL_SECONDS` — 热重载间隔（默认 300 秒）
- `TRUSTED_PROXY_CIDRS` — 可信代理 CIDR（多个用逗号分隔）
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_PASSWORD` — 邮件告警配置

## 5. 配置可信代 

只有请求直接来自 `TRUSTED_PROXY_CIDRS` 配置的地址时，才信任转发 Header（X-Forwarded-For 等）。
如果你的服务部署在 Nginx / Cloudflare 等反向代理之后，请将代理 IP 段加入配置：

```env
TRUSTED_PROXY_CIDRS=10.0.0.0/8,172.16.0.0/12,172.64.0.0/13
```

## 6. 启动服务

```bash  
uvicorn main:app --host 0.0.0.0 --port 9000
```

默认监听 `http://localhost:9000`。

## 7. GeoLite2 自动更新

应用主进程内置定时更新机制，无需配置外部 Cron：

- 每 `GEOIP_UPDATE_INTERVAL_SECONDS` 秒（默认 43200 = 12 小时）自动调用 `geoipupdate` 下载最新数据库
- 每 `GEOIP_RELOAD_INTERVAL_SECONDS` 秒（默认 300 = 5 分钟）检查文件变化并热重载
- 下载失败不会影响现有数据库，只记录 warning 日志
- 确保系统已安装 `geoipupdate` 并正确配置 `/etc/GeoIP.conf`

手动更新脚本仍可用：`bash scripts/update_geolite2.sh`

## 8. 回填已有用户 IP 数据

```bash
# 预览（不写入数据库）
python scripts/rebuild_user_geo.py --dry-run

# 实际执行（每 500 条提交一次）
python scripts/rebuild_user_geo.py --batch-size 500
```

## 9. 运行测试

```bash
python -m pytest test_geo.py -v
```

## 10. 地理位置存储规则

| 场景 | country_code | country_name | region |
|------|-------------|-------------|--------|
| 中国大陆（有省份） | CN | 中国 | 广东省 |
| 中国大陆（无省份） | CN | 中国 | Unknown | 
| 香港 | HK | 中国香港 | 香港特别行政区 |
| 澳门 | MO | 中国澳门 | 澳门特别行政区 |
| 台湾 | TW | 中国台湾 | 台湾省 |
| 其他已识别国家 | US / JP / ... | 美国 / 日本 / ... | 海外 |
| 无法识别 | null | Unknown | Unknown |

- 国外用户统一统计为"海外"
- 具体国家只保存在 `country_code` 和 `country_name` 字段
- 用户可在前端手动选择地区（当 IP 无法识别时），选择后 `manual_geo=true`，IP 变更不再覆盖

## 11. GeoLite2 不可用时的降级

- 应用启动时如果 MMDB 文件不存在或加载失败，只记录 warning，不阻止启动
- IP 查询返回 `Unknown`
- 可通过 `GET /api/ip/health` 查看当前状态

## 12. 与前端联调

根目录 `vite.config.ts` 已将 `/api/chat` 代理到 Python 后端（默认 `http://localhost:9000`）。