from pydantic import BaseModel, Field


class AccessKeyLogin(BaseModel):
    access_key: str = Field(min_length=1)


class SauthLogin(BaseModel):
    sauth_json: dict


class SauthCaptureRequest(BaseModel):
    pid: int | None = None
    process_name: str | None = None
    max_bytes: int = Field(default=1024 * 1024 * 1024, ge=16 * 1024 * 1024, le=2 * 1024 * 1024 * 1024)
