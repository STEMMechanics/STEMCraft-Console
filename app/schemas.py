from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["admin", "user"]
ProcessBackend = Literal["subprocess", "systemd"]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=64,
    )

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role: Role = "user"


class UserUpdate(BaseModel):
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    role: Role | None = None

    enabled: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    username: str
    role: Role
    enabled: bool


class ServerCreate(BaseModel):
    name: str

    directory: str

    service_name: str

    minecraft_version: str | None = None

    paper_build: str | None = None

    memory: str = Field(default="2G", pattern=r"^[1-9][0-9]*[KMGkmg]$")
    jar_name: str = Field(default="paper.jar", pattern=r"^[^/\\]+\.jar$")
    java_args: str = Field(default="", max_length=1000)
    process_backend: ProcessBackend = "subprocess"

    port: int = Field(
        default=25565,
        ge=1,
        le=65535,
    )


class ServerUpdate(BaseModel):
    name: str | None = None

    directory: str | None = None

    service_name: str | None = None

    minecraft_version: str | None = None

    paper_build: str | None = None

    memory: str | None = Field(default=None, pattern=r"^[1-9][0-9]*[KMGkmg]$")
    jar_name: str | None = Field(default=None, pattern=r"^[^/\\]+\.jar$")
    java_args: str | None = Field(default=None, max_length=1000)
    process_backend: ProcessBackend | None = None

    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )

    enabled: bool | None = None


class ServerOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    name: str
    directory: str
    service_name: str

    minecraft_version: str | None
    paper_build: str | None

    memory: str
    jar_name: str
    java_args: str
    process_backend: ProcessBackend

    port: int
    enabled: bool


class ServerAccessRequest(BaseModel):
    user_id: int
    server_id: int

class PaperInstallRequest(BaseModel):
    minecraft_version: str


class ServerStartRequest(BaseModel):
    memory: str = "2G"


class ConsoleCommandRequest(BaseModel):
    command: str = Field(
        min_length=1,
        max_length=500,
    )
