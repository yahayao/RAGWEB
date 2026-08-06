"""Bearer token 鉴权依赖。"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

import database


def get_current_user(
    request: Request,
    db: Session = Depends(database.get_db),
):
    """从 Authorization: Bearer <token> 解析匿名会话用户。"""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少认证信息")

    token = header[len("Bearer "):].strip()
    user = database.get_user_by_auth_token(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="认证信息无效")
    return user
