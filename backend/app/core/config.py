import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    app_name: str = "Minecraft Link API"
    access_key: str = "fiker-mc-login-demo-key"
    secret_key: str = "please-change-this-development-secret"
    token_algorithm: str = "HS256"
    token_expire_minutes: int = 60 * 24

    mc_api_base: str = "https://g79mclobt.minecraft.cn"
    mc_transfer_base: str = "https://g79mcltransfer.minecraft.cn"
    mc_room_lookup_path: str = "/room-with-name"
    mc_user_multi_detail_path: str = "/user-else-detail-many"
    mc_add_friend_path: str = "/user-apply-friend/"
    mc_remove_friend_path: str = "/user-del-friend/"
    mc_friend_apply_path: str = "/user-apply-friend/"
    mc_friend_reply_path: str = "/user-reply-friend/"
    mc_friend_detail_path: str = "/user-allfriends-with-detail"
    mc_accept_timeout: float = 15.0


settings = Settings()
