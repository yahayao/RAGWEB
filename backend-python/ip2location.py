"""IP 归属地查询 API — 独立子路由，挂载到主服务 main.py"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from database import extract_client_ip, lookup_region, normalize_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ip", tags=["IP Lookup"])


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

    resolved_ip, region = lookup_region(target_ip)
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "message": "查询成功",
            "data": {
                "ip": resolved_ip,
                "region": region,
            },
        },
    )


@router.post("/batch-lookup")
async def batch_lookup(request: Request):
    """批量查询 IP 归属地
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

    results: list[dict[str, str]] = []
    for raw_ip in ips:
        if isinstance(raw_ip, str):
            resolved_ip, region = lookup_region(raw_ip.strip())
        else:
            resolved_ip, region = str(raw_ip), "Invalid"
        results.append({"ip": resolved_ip, "region": region})

    return JSONResponse(
        status_code=200,
        content={"code": 200, "message": "批量查询成功", "data": results},
    )





