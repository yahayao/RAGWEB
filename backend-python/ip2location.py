"""IP 归属地查询 API — 独立子路由，挂载到主服务 main.py"""

from __future__ import annotations

import logging
from ipaddress import ip_address

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from database import extract_client_ip, lookup_geo, normalize_ip, get_geoip_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ip", tags=["IP Lookup"])

BATCH_MAX_IPS = 100


def _geo_result_to_dict(result) -> dict:
    """将 GeoLookupResult 转为 API 响应字典"""
    return {
        "ip": result.ip,
        "region": result.region,
        "country_code": result.country_code,
        "country_name": result.country_name,
        "source": result.source,
    }


@router.get("/lookup")
def ip_lookup(
    request: Request,
    ip: str = Query(default="", description="要查询的 IP 地址，留空则自动获取客户端 IP"),
):
    """查询 IP 归属地信息
    - 传 `ip` 参数：查询指定 IP
    - 不传 `ip`：自动获取当前请求的客户端 IP 并查询
    """
    target_ip = (ip or "").strip()
    if not target_ip:
        target_ip = extract_client_ip(request)

    # 验证 IP 合法性
    normalized = normalize_ip(target_ip)
    if normalized is None and target_ip:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": f"无效的 IP 地址: {target_ip}"},
        )

    result = lookup_geo(target_ip)
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "查询成功",
            "data": _geo_result_to_dict(result),
        },
    )


@router.post("/batch-lookup")
async def batch_lookup(request: Request):
    """批量查询 IP 归属地（最多 100 条）
    Body: {"ips": ["1.2.3.4", "8.8.8.8"]}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "请求体不是有效的 JSON"},
        )

    ips = body.get("ips") if isinstance(body, dict) else None
    if not isinstance(ips, list) or not ips:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": "请提供 ips 数组"},
        )

    if len(ips) > BATCH_MAX_IPS:
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": f"单次最多查询 {BATCH_MAX_IPS} 个 IP"},
        )

    results: list[dict] = []
    for raw_ip in ips:
        if isinstance(raw_ip, str) and raw_ip.strip():
            result = lookup_geo(raw_ip.strip())
            results.append(_geo_result_to_dict(result))
        else:
            results.append({
                "ip": str(raw_ip) if raw_ip else "",
                "region": "Invalid",
                "country_code": None,
                "country_name": "Unknown",
                "source": "unresolved",
            })

    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "批量查询成功", "data": results},
    )


@router.get("/health")
def ip_health():
    """GeoIP 数据库健康检查"""
    status = get_geoip_status()
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "查询成功",
            "data": status,
        },
    )

