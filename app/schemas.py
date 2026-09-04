from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class TrackerRecordIn(BaseModel):
    ticket_id: str = Field(min_length=1, max_length=120)
    date_started: date | None = None
    date_ended: date | None = None
    tester_name_raw: str | None = None
    status: str = "Pending"
    zephyr_upload: str | None = None
    comments: str | None = None
    owner_user_id: int | None = None
    version: int | None = None


class TrackerRecordOut(TrackerRecordIn):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str = Field(min_length=12)
    role_id: int
    active: bool = True


class UserUpdate(BaseModel):
    display_name: str | None = None
    role_id: int | None = None
    active: bool | None = None


class LoginIn(BaseModel):
    email: str
    password: str
