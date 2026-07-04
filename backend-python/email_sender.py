"""邮件告警发送模块

使用标准库 smtplib + email.mime 发送 HTML 格式的告警邮件。
SMTP 配置（服务器、端口、密码）通过环境变量注入，不硬编码敏感信息。
收件人列表直接定义在本模块的 ALERT_RECIPIENTS 变量中。

环境变量:
  SMTP_HOST       — SMTP 服务器地址（必填）
  SMTP_PORT       — SMTP 服务器端口（默认 465）
  SMTP_PASSWORD   — aohelper@bnbu.edu.cn 的密码/授权码（必填）
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from typing import Any

logger = logging.getLogger(__name__)

# ==================== 邮件配置 ====================

SMTP_SENDER = "aohelper@bnbu.edu.cn"
SMTP_SENDER_NAME = "招生助手提醒"

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()

# ==================== 收件人列表 ====================
# 在此数组中添加需要接收告警邮件的邮箱地址
ALERT_RECIPIENTS: list[str] = [
    # "teacher1@bnbu.edu.cn",
    "u430026005@mail.bnbu.edu.cn",
    "u430026183@mail.bnbu.edu.cn",
    "u430016047@mail.bnbu.edu.cn",
    "u430026175@mail.bnbu.edu.cn",
    "u430026130@mail.bnbu.edu.cn",
]

_configured: bool | None = None


def is_configured() -> bool:
    """检查邮件发送所需的配置是否齐全"""
    global _configured
    if _configured is not None:
        return _configured
    missing: list[str] = []
    if not SMTP_HOST:
        missing.append("SMTP_HOST")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    if not ALERT_RECIPIENTS:
        missing.append("ALERT_RECIPIENTS（收件人列表为空）")
    if missing:
        logger.warning("邮件告警未配置，缺少环境变量: %s", ", ".join(missing))
        _configured = False
    else:
        logger.info("邮件告警已配置，收件人 (%d 人): %s", len(ALERT_RECIPIENTS), ", ".join(ALERT_RECIPIENTS))
        _configured = True
    return _configured


# ==================== HTML 模板 ====================

ALERT_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>招生助手提醒系统通知</title>
<style>
  body {{
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                 'Microsoft YaHei', sans-serif;
    background-color: #f0f2f5;
  }}
  .container {{
    max-width: 600px; margin: 24px auto; padding: 0 16px;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 32px 24px; border-radius: 12px 12px 0 0; text-align: center;
  }}
  .header h1 {{
    margin: 0; color: #4facfe; font-size: 22px; letter-spacing: 2px;
  }}
  .header p {{
    margin: 8px 0 0; color: #8899aa; font-size: 13px;
  }}
  .body {{
    background: #ffffff; padding: 24px; border-radius: 0 0 12px 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }}
  .tag {{
    display: inline-block; padding: 4px 14px; border-radius: 4px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.5px;
  }}
  .tag-urgent {{ background: #fef2f2; color: #dc2626; }}
  .tag-high {{ background: #fff7ed; color: #ea580c; }}
  .field {{ margin-bottom: 16px; }}
  .field-label {{
    font-size: 12px; color: #6b7280; margin-bottom: 4px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .field-value {{
    font-size: 15px; color: #111827; line-height: 1.5;
    padding: 8px 12px; background: #f9fafb; border-radius: 6px;
    word-break: break-all;
  }}
  .grid-2 {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
  }}
  .footer {{
    text-align: center; padding: 20px; color: #9ca3af; font-size: 12px;
  }}
  .hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 20px 0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>招生助手提醒</h1>
    <p>{alert_time} · 系统自动发送</p>
  </div>
  <div class="body">
    <div style="text-align:center;margin-bottom:20px;">
      {intent_badge}
    </div>

    <div class="grid-2">
      <div class="field">
        <div class="field-label">用户手机号</div>
        <div class="field-value" style="font-size:18px;font-weight:600;color:#2563eb;">
          {contact}
        </div>
      </div>
      <div class="field">
        <div class="field-label">用户姓名</div>
        <div class="field-value">{student_name}</div>
      </div>
    </div>

    <hr class="hr">

    <div class="grid-2">
      <div class="field">
        <div class="field-label">客户端 IP</div>
        <div class="field-value">{client_ip}</div>
      </div>
      <div class="field">
        <div class="field-label">国家/地区</div>
        <div class="field-value">{country_name}</div>
      </div>
    </div>

    <div class="field">
      <div class="field-label">区域</div>
      <div class="field-value">{region}</div>
    </div>

    <hr class="hr">

    <div class="field">
      <div class="field-label">触发消息摘要</div>
      <div class="field-value">{message_snippet}</div>
    </div>

    <div class="field">
      <div class="field-label">会话 ID</div>
      <div class="field-value" style="font-family:monospace;font-size:13px;">
        {session_id}
      </div>
    </div>
  </div>
  <div class="footer">
    此邮件由系统自动发送，请勿直接回复。
  </div>
</div>
</body>
</html>
"""


def _build_html_body(
    *,
    contact: str,
    student_name: str,
    client_ip: str,
    region: str,
    country_name: str = "Unknown",
    intent_type: str,
    message_snippet: str,
    session_id: str,
    alert_time: str,
) -> str:
    """用模板数据填充 HTML 邮件正文"""
    if intent_type == "urgent":
        intent_badge = '<span class="tag tag-urgent">紧急告警</span>'
    else:
        intent_badge = '<span class="tag tag-high">高意向咨询</span>'

    return ALERT_EMAIL_TEMPLATE.format(
        alert_time=alert_time,
        intent_badge=intent_badge,
        contact=contact,
        student_name=student_name or "匿名用户",
        client_ip=client_ip,
        country_name=country_name or "Unknown",
        region=region or "未知",
        message_snippet=message_snippet or "（无）",
        session_id=session_id or "（无）",
    )


# ==================== 发送函数 ====================


def send_alert_email_sync(alert_data: dict[str, Any]) -> bool:
    """同步发送告警邮件（内部调用，由 async wrapper 包装）"""
    if not is_configured():
        logger.debug("邮件未配置，跳过发送")
        return False

    html = _build_html_body(**alert_data)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = f"[招生系统提醒] {alert_data.get('intent_type', 'unknown')} — {alert_data.get('contact', '')}"
    msg["From"] = formataddr((SMTP_SENDER_NAME, SMTP_SENDER))
    msg["To"] = ", ".join(ALERT_RECIPIENTS)
    msg["Date"] = formatdate(localtime=True)
    msg["X-Priority"] = "1" if alert_data.get("intent_type") == "urgent" else "3"

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.login(SMTP_SENDER, SMTP_PASSWORD)
                server.sendmail(SMTP_SENDER, ALERT_RECIPIENTS, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                if SMTP_PORT == 587:
                    server.starttls()
                server.login(SMTP_SENDER, SMTP_PASSWORD)
                server.sendmail(SMTP_SENDER, ALERT_RECIPIENTS, msg.as_string())

        logger.info(
            "告警邮件已发送: to=%s, contact=%s, type=%s",
            ", ".join(ALERT_RECIPIENTS),
            alert_data.get("contact"),
            alert_data.get("intent_type"),
        )
        return True

    except Exception:
        logger.exception("发送告警邮件失败: to=%s, contact=%s", ", ".join(ALERT_RECIPIENTS), alert_data.get("contact"))
        return False


async def send_alert_email(alert_data: dict[str, Any]) -> bool:
    """异步发送告警邮件，在 executor 中执行同步 SMTP 操作"""
    if not is_configured():
        return False

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, send_alert_email_sync, alert_data)
