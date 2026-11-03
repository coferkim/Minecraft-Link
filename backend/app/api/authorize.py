from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import constant_time_equal, create_access_token
from app.db import storage
from app.schemas.auth import AccessKeyLogin


router = APIRouter(tags=["authorize"])


@router.post("/authorize/access-key")
async def authorize_access_key(payload: AccessKeyLogin):
    if not constant_time_equal(payload.access_key, settings.access_key):
        storage.log_action("access_key_failed", {})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "访问密钥错误")
    storage.log_action("access_key_ok", {})
    access_token = create_access_token("guest", {"stage": "mc-login"})
    return {
        "stage": "mc-login",
        "access_token": access_token,
        "token_type": "bearer",
        "username": "guest",
        "message": "访问密钥验证成功",
    }
