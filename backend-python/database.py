"""共享数据库配置、模型定义与工具函数"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from ipaddress import ip_address
from typing import Any, cast

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, create_engine, event, text
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column, relationship, sessionmaker

from time_util import to_str_time as _to_str_time

try:
    import ip2region.searcher as ip2xdb  # type: ignore[import-not-found]
    import ip2region.util as ip2util  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    ip2xdb = None
    ip2util = None

try:
    import IP2Location  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    IP2Location = None

logger = logging.getLogger(__name__)

# ==================== 环境变量加载 ====================


def load_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


load_env_file()

# ==================== 应用配置 ====================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:123456@localhost:5432/ai_chat")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "9000"))

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_ECHO = os.getenv("DB_ECHO", "false").lower() in {"1", "true", "yes", "on"}

# IP2Region 数据文件路径
IP2REGION_DB_PATH = os.getenv(
    "IP2REGION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "data", "ip2region_v4.xdb"),
)

# IP2Location BIN 文件路径
IP2LOCATION_DB_PATH = os.getenv(
    "IP2LOCATION_DB_PATH",
    os.path.join(os.path.dirname(__file__), "ip2region", "data", "IP2LOCATION-LITE-DB3.BIN"),
)

# ==================== 数据库引擎 ====================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    echo=DB_ECHO,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _set_timezone(dbapi_connection, _connection_record):
    """每个新数据库连接建立时设置会话时区为东八区"""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'Asia/Shanghai'")
    cursor.close()

# ==================== 全局检索实例 ====================

_searcher = None          # ip2region xdb 检索器
_location_db = None       # IP2Location 实例


# ==================== ORM 模型 ====================


class ChatUser(Base):
    """用户主表：id 自增主键作为唯一标识，username 存展示名（可重复）"""

    __tablename__ = "chat_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ChatSession(Base):
    """对话会话表：记录每一轮问答"""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_user_session_time", "user_id", "session_id", "create_time"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user: Mapped[ChatUser] = relationship(back_populates="sessions")


# ==================== 工具函数 ====================


def ensure_schema() -> None:
    """仅负责建表，不做业务数据变更"""
    Base.metadata.create_all(bind=engine)


def json_resp(status: int, data: dict[str, Any]) -> dict[str, Any]:
    """返回字典格式的 JSON 响应体（配合 FastAPI 响应使用）"""
    return {"code": status, **data} if "code" not in data else data


async def _safe_json_body(request: Any) -> dict[str, Any]:
    try:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== IP 工具函数 ====================


def _parse_ip_candidate(value: str) -> str | None:
    """规范化候选 IP：去掉引号、端口、IPv6 zone、IPv4-mapped 前缀"""
    candidate = (value or "").strip().strip('"').strip("'")
    if not candidate or candidate.lower() == "unknown":
        return None

    if candidate.startswith("[") and "]" in candidate:
        candidate = candidate[1 : candidate.index("]")]

    if candidate.startswith("::ffff:"):
        candidate = candidate[7:]

    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]

    if candidate.count(":") == 1 and "." in candidate:
        host, port = candidate.rsplit(":", 1)
        if port.isdigit():
            candidate = host

    try:
        ip_address(candidate)
        return candidate
    except ValueError:
        return None


def _prefer_public_ip(candidates: list[str]) -> str | None:
    """优先使用公网地址，若无公网则回退到首个合法 IP"""
    parsed: list[str] = []
    for c in candidates:
        ip = _parse_ip_candidate(c)
        if ip:
            parsed.append(ip)

    for ip in parsed:
        if ip_address(ip).is_global:
            return ip

    return parsed[0] if parsed else None


def extract_client_ip(req: Any) -> str:
    """按反向代理常见头顺序提取真实客户端地址"""
    direct_headers = [
        req.headers.get("CF-Connecting-IP", ""),
        req.headers.get("True-Client-IP", ""),
        req.headers.get("X-Real-IP", ""),
        req.headers.get("X-Client-IP", ""),
    ]
    chosen = _prefer_public_ip(direct_headers)
    if chosen:
        return chosen

    xff = req.headers.get("X-Forwarded-For", "").strip()
    if xff:
        chosen = _prefer_public_ip([p.strip() for p in xff.split(",")])
        if chosen:
            return chosen

    forwarded = req.headers.get("Forwarded", "").strip()
    if forwarded:
        forwarded_candidates: list[str] = []
        for seg in forwarded.split(","):
            for item in seg.split(";"):
                kv = item.strip()
                if kv.lower().startswith("for="):
                    forwarded_candidates.append(kv.split("=", 1)[1].strip())
        chosen = _prefer_public_ip(forwarded_candidates)
        if chosen:
            return chosen

    remote_addr = cast(str | None, req.client.host if req.client else None)
    return _parse_ip_candidate((remote_addr or "").strip()) or "0.0.0.0"


def normalize_ip(raw_ip: str) -> str:
    ip_val = (raw_ip or "0.0.0.0").strip()
    if ip_val.startswith("::ffff:"):
        ip_val = ip_val[7:]
    if "%" in ip_val:
        ip_val = ip_val.split("%", 1)[0]
    return ip_val


def lookup_region(raw_ip: str) -> tuple[str, str]:
    """查询 IP 归属地，支持 ip2region xdb 和 IP2Location BIN 两种方式"""
    ip_val = normalize_ip(raw_ip)
    try:
        ip_address(ip_val)
    except ValueError:
        return ip_val, "Unknown"

    # 优先使用 ip2region xdb
    if _searcher is not None:
        try:
            region = _searcher.search(ip_val)
            return ip_val, (region or "Unknown")
        except Exception:
            pass

    # 回退到 IP2Location
    if _location_db is not None:
        try:
            record = _location_db.get_all(ip_val)
            country = _clean_location_value(getattr(record, "country_name", ""))
            region = _clean_location_value(getattr(record, "region_name", ""))
            city = _clean_location_value(getattr(record, "city_name", ""))
            parts = [country, region, city]
            combined = " | ".join([p for p in parts if p])
            return ip_val, (combined or "Unknown")
        except Exception:
            pass

    return ip_val, "Unknown"


def _clean_location_value(value: Any) -> str:
    text_value = str(value or "").strip()
    if not text_value or text_value in {"-", "NOT_SUPPORTED", "Not_Supported"}:
        return ""
    return text_value


def register_user(db: Session, display_name_raw: str, client_ip: str) -> dict:
    """注册新用户：自增 id 作为唯一标识，username 存展示名（可重复）"""
    username = (display_name_raw or "").strip()[:64] or "匿名用户"
    ip_val, region = lookup_region(client_ip)
    user = ChatUser(username=username, ip=ip_val, region=region)
    db.add(user)
    db.flush()
    return {"id": int(user.id), "username": user.username}


def parse_user_id(raw: str | None) -> int | None:
    """将请求参数转为数字用户 ID，无效则返回 None"""
    try:
        uid = int(str(raw or "").strip())
        return uid if uid > 0 else None
    except (ValueError, TypeError):
        return None


def user_exists(db: Session, user_id: int) -> bool:
    """检查用户是否存在"""
    return db.query(ChatUser.id).filter(ChatUser.id == user_id).first() is not None


# ==================== 初始化 / 销毁 ====================


def init_searcher() -> None:
    """启动时加载 IP 检索器，避免每次请求重复读取文件"""
    global _searcher, _location_db

    # 初始化 ip2region
    if ip2xdb is not None and ip2util is not None and os.path.exists(IP2REGION_DB_PATH):
        try:
            ip2util.verify_from_file(IP2REGION_DB_PATH)
            with open(IP2REGION_DB_PATH, "rb") as handle:
                header = ip2util.load_header(handle)
                version = ip2util.version_from_header(header)
                if version is not None:
                    v_index = ip2util.load_vector_index(handle)
                    _searcher = ip2xdb.new_with_vector_index(version, IP2REGION_DB_PATH, v_index)
        except Exception as exc:
            logger.warning("初始化 ip2region 失败: %s", exc)

    # 初始化 IP2Location
    if IP2Location is not None and os.path.exists(IP2LOCATION_DB_PATH):
        try:
            _location_db = IP2Location.IP2Location(IP2LOCATION_DB_PATH)
        except Exception as exc:
            logger.warning("初始化 IP2Location 失败: %s", exc)


def close_searcher() -> None:
    """关闭检索器，释放资源"""
    global _searcher, _location_db

    if _searcher is not None:
        try:
            _searcher.close()
        except Exception:
            pass
        _searcher = None

    if _location_db is not None:
        try:
            close_fn = getattr(_location_db, "close", None)
            if callable(close_fn):
                close_fn()
        except Exception:
            pass
        _location_db = None
