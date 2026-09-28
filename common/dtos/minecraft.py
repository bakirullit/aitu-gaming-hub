from pydantic import BaseModel, Field
from typing import Optional


class MinecraftRequestCodePayload(BaseModel):
    telegram_tag: str = Field(..., description="Telegram handle (e.g. @username or username)")
    minecraft_nickname: str = Field(..., description="Minecraft Java player nickname")


class MinecraftRequestCodeResponse(BaseModel):
    status: str = "code_sent"
    message: str = "Verification code sent to Telegram"


class MinecraftVerifyPayload(BaseModel):
    telegram_tag: str = Field(..., description="Telegram handle (e.g. @username or username)")
    code: str = Field(..., description="6-digit verification code")
    minecraft_nickname: str = Field(..., description="Minecraft Java player nickname")


class MinecraftVerifyResponse(BaseModel):
    status: str = "success"
    session_token: str
    telegram_id: int
    username: str


class MinecraftServerInfoResponse(BaseModel):
    ip: str = "mc.aitu-gaming.y-not-devs.com:25565"
    name: str = "AITU Official SMP / Create"
    online: int = 14
    max_players: int = 50
    motd: str = "Welcome to AITU Gaming Network!"


class MinecraftFriendItem(BaseModel):
    nickname: str
    telegram_tag: str
    status: str = "online"
    activity: str = "Playing on AITU SMP"


class MinecraftFriendsListResponse(BaseModel):
    friends: list[MinecraftFriendItem] = Field(default_factory=list)


class MinecraftFriendRequestItem(BaseModel):
    request_id: Optional[int] = None
    id: Optional[int] = None
    from_nickname: Optional[str] = None
    from_tag: Optional[str] = None
    status: str = "pending"


class MinecraftFriendRequestsResponse(BaseModel):
    requests: list[MinecraftFriendRequestItem] = Field(default_factory=list)


class MinecraftFriendSendRequestPayload(BaseModel):
    query: str = Field(..., description="@friend_tag or email or nickname")


class MinecraftFriendActionPayload(BaseModel):
    request_id: Optional[int] = None
    target_tag: Optional[str] = None


class MinecraftStatusResponse(BaseModel):
    status: str
