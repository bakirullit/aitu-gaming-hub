from pydantic import BaseModel, Field
from typing import Optional


class MinecraftRequestCodePayload(BaseModel):
    telegram_tag: Optional[str] = Field(None, description="Telegram handle (e.g. @username or username)")
    tag: Optional[str] = Field(None, description="Alternative tag field")
    minecraft_nickname: Optional[str] = Field(None, description="Minecraft Java player nickname")
    mc_nick: Optional[str] = Field(None, description="Minecraft nickname alias")


class MinecraftRequestCodeResponse(BaseModel):
    status: str = "code_sent"
    message: str = "Verification code sent to Telegram"


class MinecraftVerifyPayload(BaseModel):
    telegram_tag: Optional[str] = Field(None, description="Telegram handle (e.g. @username or username)")
    tag: Optional[str] = Field(None, description="Alternative tag field")
    code: Optional[str] = Field(None, description="6-digit verification code")
    pin: Optional[str] = Field(None, description="6-digit verification PIN")
    minecraft_nickname: Optional[str] = Field(None, description="Minecraft Java player nickname")
    mc_nick: Optional[str] = Field(None, description="Minecraft nickname alias")


class MinecraftVerifyResponse(BaseModel):
    status: str = "success"
    session_token: str
    token: Optional[str] = None
    telegram_id: int
    username: str
    telegram_tag: Optional[str] = None
    tag: Optional[str] = None
    minecraft_nickname: Optional[str] = None
    nickname: Optional[str] = None


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


class MinecraftTokenVerifyPayload(BaseModel):
    token: Optional[str] = Field(None, description="Client session token")
    session_token: Optional[str] = Field(None, description="Alternative token field")
    launcher_nickname: Optional[str] = Field(None, description="Optional launcher username reported by client")
    player_name: Optional[str] = Field(None, description="Player nickname alias")
    username: Optional[str] = Field(None, description="Username alias")


class MinecraftTokenVerifyResponse(BaseModel):
    valid: bool
    status: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_tag: Optional[str] = None
    minecraft_nickname: Optional[str] = None
    nickname: Optional[str] = None
    player_name: Optional[str] = None
    is_whitelisted: bool = False
    role: Optional[str] = None
    error: Optional[str] = None
