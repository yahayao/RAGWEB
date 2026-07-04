"""共享数据库配置、模型定义与工具函数"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, cast

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, create_engine, event, text
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column, relationship, sessionmaker

from time_util import to_str_time as _to_str_time

try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError
except Exception:  # pragma: no cover
    geoip2 = None
    AddressNotFoundError = Exception

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

# MaxMind GeoLite2 City 数据库路径
GEOLITE2_CITY_DB_PATH = os.getenv(
    "GEOLITE2_CITY_DB_PATH",
    os.path.join(os.path.dirname(__file__), "geoip", "GeoLite2-City.mmdb"),
)

# 热重载检查间隔（秒）
GEOIP_RELOAD_INTERVAL_SECONDS = int(
    os.getenv("GEOIP_RELOAD_INTERVAL_SECONDS", "300")
)

# geoipupdate 下载间隔（秒），默认 12 小时
GEOIP_UPDATE_INTERVAL_SECONDS = int(
    os.getenv("GEOIP_UPDATE_INTERVAL_SECONDS", "43200")
)

# 可信代理 CIDR 列表，只有直接连接来自这些地址时才信任转发 Header
TRUSTED_PROXY_CIDRS = os.getenv(
    "TRUSTED_PROXY_CIDRS",
    "127.0.0.1/32,::1/128",
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

# ==================== 全局 GeoIP 状态 ====================

_geoip_reader = None             # geoip2.database.Reader 实例
_geoip_lock = threading.RLock()  # 保护 Reader 的读写锁
_geoip_file_signature = None     # (inode, mtime_ns, size) 文件签名
_geoip_build_epoch = None        # 数据库 build epoch
_geoip_last_reload_time = None   # 最后成功加载时间


# ==================== 中国省份映射 ====================

CN_PROVINCE_MAP = {
    "AH": "安徽省",
    "BJ": "北京市",
    "CQ": "重庆市",
    "FJ": "福建省",
    "GS": "甘肃省",
    "GD": "广东省",
    "GX": "广西壮族自治区",
    "GZ": "贵州省",
    "HI": "海南省",
    "HE": "河北省",
    "HL": "黑龙江省",
    "HA": "河南省",
    "HB": "湖北省",
    "HN": "湖南省",
    "JS": "江苏省",
    "JX": "江西省",
    "JL": "吉林省",
    "LN": "辽宁省",
    "NM": "内蒙古自治区",
    "NX": "宁夏回族自治区",
    "QH": "青海省",
    "SN": "陕西省",
    "SD": "山东省",
    "SH": "上海市",
    "SX": "山西省",
    "SC": "四川省",
    "TJ": "天津市",
    "XZ": "西藏自治区",
    "XJ": "新疆维吾尔自治区",
    "YN": "云南省",
    "ZJ": "浙江省",
}


# ==================== 查询结果对象 ====================


@dataclass(frozen=True, slots=True)
class GeoLookupResult:
    """IP 地理位置查询结果"""
    ip: str
    country_code: str | None
    country_name: str
    region: str
    source: str  # "geolite2" 或 "unresolved"


# ==================== ORM 模型 ====================


class ChatUser(Base):
    """用户主表：id 自增主键作为唯一标识，username 存展示名（可重复）"""

    __tablename__ = "chat_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True,
    )
    country_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    manual_geo: Mapped[bool] = mapped_column(
        default=False,
        server_default=text("false"),
        nullable=False,
    )
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


def normalize_ip(raw_ip: str) -> str | None:
    """规范化 IP 地址，返回合法 IP 字符串或 None

    支持: IPv4, IPv6, IPv4-mapped IPv6, [IPv6]:port, zone ID, 端口号剥离
    """
    ip_val = (raw_ip or "").strip().strip('"').strip("'")
    if not ip_val or ip_val.lower() == "unknown":
        return None

    # [IPv6]:port 格式
    if ip_val.startswith("[") and "]" in ip_val:
        ip_val = ip_val[1 : ip_val.index("]")]

    # IPv4-mapped IPv6
    if ip_val.startswith("::ffff:"):
        ip_val = ip_val[7:]

    # zone ID
    if "%" in ip_val:
        ip_val = ip_val.split("%", 1)[0]

    # IPv4:port 格式
    if ip_val.count(":") == 1 and "." in ip_val:
        host, port = ip_val.rsplit(":", 1)
        if port.isdigit():
            ip_val = host

    try:
        ip_address(ip_val)
        return ip_val
    except ValueError:
        return None


def _parse_trusted_cidrs() -> list[ip_network]:
    """解析 TRUSTED_PROXY_CIDRS 环境变量为 ip_network 列表"""
    networks: list[ip_network] = []
    for raw in TRUSTED_PROXY_CIDRS.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            networks.append(ip_network(raw))
        except ValueError:
            logger.warning("无效的 TRUSTED_PROXY_CIDRS 条目: %s", raw)
    return networks


def _is_trusted_proxy(ip_str: str) -> bool:
    """判断 IP 是否属于可信代理范围"""
    try:
        addr = ip_address(ip_str)
    except ValueError:
        return False
    for net in _parse_trusted_cidrs():
        if addr in net:
            return True
    return False


def extract_client_ip(req: Any) -> str:
    """按反向代理常见头顺序提取真实客户端地址

    安全规则: 只有直接连接来源在 TRUSTED_PROXY_CIDRS 中时，才信任转发 Header。
    否则忽略所有转发头，使用直连 IP。
    """
    # 获取直连地址
    remote_addr = cast(str | None, req.client.host if req.client else None)
    direct_ip = _parse_ip_candidate((remote_addr or "").strip())

    if not direct_ip:
        return "0.0.0.0"

    # 只有直接连接来源可信时才解析转发 Header
    if not _is_trusted_proxy(direct_ip):
        return direct_ip

    # 可信来源：依次尝试各转发 Header
    direct_headers = [
        req.headers.get("CF-Connecting-IP", ""),
        req.headers.get("True-Client-IP", ""),
        req.headers.get("X-Real-IP", ""),
        req.headers.get("X-Client-IP", ""),
    ]
    chosen = _prefer_public_ip(direct_headers)
    if chosen:
        return chosen

    # X-Forwarded-For: 从右向左遍历，跳过可信代理
    xff = req.headers.get("X-Forwarded-For", "").strip()
    if xff:
        xff_candidates = [p.strip() for p in xff.split(",")]
        # 从右向左：最后一个非可信代理 IP 就是客户端真实 IP
        for candidate in reversed(xff_candidates):
            ip = _parse_ip_candidate(candidate)
            if ip and not _is_trusted_proxy(ip):
                return ip

    # Forwarded 头 (RFC 7239)
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

    return direct_ip


def _get_file_signature(path: str) -> tuple[int, int, int] | None:
    """获取文件签名: (inode, mtime_ns, size)"""
    try:
        stat = os.stat(path)
        return (stat.st_ino, stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None


def lookup_geo(raw_ip: str) -> GeoLookupResult:
    """查询 IP 地理位置信息（使用 GeoLite2 City）

    返回 GeoLookupResult，包含: ip, country_code, country_name, region, source

    区域规则:
    - 中国大陆 (CN): country_code=CN, country_name=中国, region=省份名 (或 Unknown)
    - 香港 (HK): country_code=HK, country_name=中国香港, region=香港特别行政区
    - 澳门 (MO): country_code=MO, country_name=中国澳门, region=澳门特别行政区
    - 台湾 (TW): country_code=TW, country_name=中国台湾, region=台湾省
    - 其他已识别国家: region=海外, country_code/country_name 保留具体值
    - 无法识别: country_code=None, country_name=Unknown, region=Unknown, source=unresolved
    """
    # 规范化 IP
    normalized = normalize_ip(raw_ip)
    if normalized is None:
        return GeoLookupResult(
            ip=raw_ip.strip() or "0.0.0.0",
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="unresolved",
        )

    # 验证是否为合法 IP 地址
    try:
        parsed_ip = ip_address(normalized)
    except ValueError:
        return GeoLookupResult(
            ip=normalized,
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="unresolved",
        )

    # 公网 IP 才查询 GeoLite2
    if not parsed_ip.is_global:
        return GeoLookupResult(
            ip=normalized,
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="unresolved",
        )

    # 查询 GeoLite2
    with _geoip_lock:
        reader = _geoip_reader

    if reader is None:
        return GeoLookupResult(
            ip=normalized,
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="unresolved",
        )

    try:
        response = reader.city(normalized)
    except AddressNotFoundError:
        return GeoLookupResult(
            ip=normalized,
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="geolite2",
        )
    except Exception:
        return GeoLookupResult(
            ip=normalized,
            country_code=None,
            country_name="Unknown",
            region="Unknown",
            source="unresolved",
        )

    # 解析国家信息
    country_code = (response.country.iso_code or "").strip() or None
    country_name = response.country.name or country_code or "Unknown"

    # 业务规则覆盖
    if country_code == "CN":
        country_name = "中国"
        subdivision = response.subdivisions[0] if response.subdivisions else None
        subdivision_code = subdivision.iso_code.strip() if subdivision and subdivision.iso_code else None
        region = CN_PROVINCE_MAP.get(subdivision_code, "Unknown") if subdivision_code else "Unknown"
    elif country_code == "HK":
        country_name = "中国香港"
        region = "香港特别行政区"
    elif country_code == "MO":
        country_name = "中国澳门"
        region = "澳门特别行政区"
    elif country_code == "TW":
        country_name = "中国台湾"
        region = "台湾省"
    else:
        region = "海外"

    return GeoLookupResult(
        ip=normalized,
        country_code=country_code,
        country_name=country_name,
        region=region,
        source="geolite2",
    )


def lookup_region(raw_ip: str) -> tuple[str, str]:
    """兼容旧接口: 返回 (ip, region) 元组"""
    result = lookup_geo(raw_ip)
    return result.ip, result.region


# ==================== 保留旧辅助（extract_client_ip 依赖） ====================


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


def register_user(db: Session, display_name_raw: str, client_ip: str) -> dict:
    """注册新用户：自增 id 作为唯一标识，username 存展示名（可重复）

    每次注册都会查询 IP 归属地并写入 geo 字段。
    如果用户已设置 manual_geo=True，则保留其手动选择的地理位置。
    """
    username = (display_name_raw or "").strip()[:64] or "匿名用户"
    geo = lookup_geo(client_ip)
    user = ChatUser(
        username=username,
        ip=geo.ip,
        region=geo.region,
        country_code=geo.country_code,
        country_name=geo.country_name,
    )
    db.add(user)
    db.flush()
    return {
        "id": int(user.id),
        "username": user.username,
        "region": user.region,
        "country_code": user.country_code,
        "country_name": user.country_name,
        "manual_geo": user.manual_geo,
    }


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
    """启动时加载 MaxMind GeoLite2 City 数据库 Reader

    加载失败不阻止应用启动，只记录 warning。
    Reader 不可用时 IP 查询返回 Unknown。
    """
    global _geoip_reader, _geoip_file_signature, _geoip_build_epoch, _geoip_last_reload_time

    if geoip2 is None:
        logger.warning("geoip2 库未安装，IP 地理位置查询不可用")
        return

    db_path = GEOLITE2_CITY_DB_PATH
    if not os.path.exists(db_path):
        logger.warning("GeoLite2-City 数据库文件不存在: %s", db_path)
        return

    try:
        reader = geoip2.database.Reader(db_path, locales=["zh-CN", "en"])
        # 验证数据库类型
        metadata = reader.metadata()
        if metadata.database_type != "GeoLite2-City":
            logger.warning(
                "数据库类型不匹配: 期望 GeoLite2-City, 实际 %s",
                metadata.database_type,
            )
            reader.close()
            return

        _geoip_build_epoch = metadata.build_epoch
        _geoip_file_signature = _get_file_signature(db_path)
        _geoip_last_reload_time = datetime.now()
        _geoip_reader = reader
        logger.info(
            "GeoLite2-City 加载成功: build_epoch=%s, path=%s",
            _geoip_build_epoch,
            db_path,
        )
    except Exception as exc:
        logger.warning("初始化 GeoLite2-City 失败: %s", exc)


def close_searcher() -> None:
    """关闭 GeoLite2 Reader，释放资源"""
    global _geoip_reader, _geoip_file_signature, _geoip_build_epoch, _geoip_last_reload_time

    with _geoip_lock:
        reader = _geoip_reader
        _geoip_reader = None

    if reader is not None:
        try:
            reader.close()
        except Exception:
            pass

    _geoip_file_signature = None
    _geoip_build_epoch = None
    _geoip_last_reload_time = None


def reload_searcher_if_changed() -> bool:
    """检查 MMDB 文件是否变化，若变化则在锁外创建新 Reader 后原子替换

    返回 True 表示成功热重载，False 表示无变化或重载失败。
    失败时保留旧 Reader 继续服务。
    """
    global _geoip_reader, _geoip_file_signature, _geoip_build_epoch, _geoip_last_reload_time

    db_path = GEOLITE2_CITY_DB_PATH
    if not os.path.exists(db_path):
        return False

    new_sig = _get_file_signature(db_path)
    if new_sig is None:
        return False

    with _geoip_lock:
        old_sig = _geoip_file_signature

    if new_sig == old_sig:
        return False

    # 文件变化，在锁外创建新 Reader
    try:
        new_reader = geoip2.database.Reader(db_path, locales=["zh-CN", "en"])
        metadata = new_reader.metadata()
        if metadata.database_type != "GeoLite2-City":
            logger.warning("热重载: 新数据库类型不匹配，跳过")
            new_reader.close()
            return False
    except Exception as exc:
        logger.warning("热重载 GeoLite2-City 失败 (创建新 Reader): %s", exc)
        return False

    # 原子替换
    with _geoip_lock:
        old_reader = _geoip_reader
        _geoip_reader = new_reader
        _geoip_file_signature = new_sig
        _geoip_build_epoch = metadata.build_epoch
        _geoip_last_reload_time = datetime.now()

    # 关闭旧 Reader（锁外，确保没有查询在使用）
    if old_reader is not None:
        try:
            old_reader.close()
        except Exception:
            pass

    logger.info(
        "GeoLite2-City 热重载成功: build_epoch=%s",
        metadata.build_epoch,
    )
    return True


def run_geoipupdate() -> bool:
    """通过子进程调用 geoipupdate 下载最新 GeoLite2-City 数据库

    使用系统的 /etc/GeoIP.conf 配置文件，不需要在 .env 中额外存储凭证。
    返回 True 表示下载成功，False 表示失败。
    失败时保留现有 MMDB 文件不变。
    """
    geoip_dir = os.path.dirname(GEOLITE2_CITY_DB_PATH)
    try:
        result = subprocess.run(
            ["geoipupdate", "-f", "/etc/GeoIP.conf", "-d", geoip_dir],
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
        )
        if result.returncode == 0:
            logger.info("geoipupdate 下载成功: %s", result.stdout.strip())
            return True
        else:
            logger.warning(
                "geoipupdate 下载失败 (exit=%d): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False
    except FileNotFoundError:
        logger.warning("geoipupdate 命令未找到，请安装 geoipupdate 工具")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("geoipupdate 下载超时（5 分钟）")
        return False
    except Exception as exc:
        logger.warning("geoipupdate 执行异常: %s", exc)
        return False


def get_geoip_status() -> dict[str, Any]:
    """获取 GeoIP 当前状态（用于健康检查）"""
    with _geoip_lock:
        available = _geoip_reader is not None
        build_epoch = _geoip_build_epoch
        last_reload = _geoip_last_reload_time

    from time_util import to_str_time

    return {
        "available": available,
        "database_build_epoch": build_epoch,
        "last_reload_time": to_str_time(last_reload) if last_reload else None,
        "reload_interval_seconds": GEOIP_RELOAD_INTERVAL_SECONDS,
    }
