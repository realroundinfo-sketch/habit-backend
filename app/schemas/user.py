from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    work_type: Optional[str] = None
    work_hours_target: Optional[float] = None
    sleep_target: Optional[float] = None
    primary_goal: Optional[str] = None
    experience_level: Optional[str] = None
    daily_reminder_time: Optional[str] = None
    weekly_report_enabled: Optional[bool] = None
    notification_enabled: Optional[bool] = None


class OnboardingComplete(BaseModel):
    work_type: str
    work_hours_target: float = 8.0
    sleep_target: float = 7.5
    primary_goal: str
    experience_level: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    timezone: str
    role: str
    work_type: Optional[str] = None
    work_hours_target: Optional[float] = None
    sleep_target: Optional[float] = None
    primary_goal: Optional[str] = None
    experience_level: Optional[str] = None
    onboarding_completed: bool
    daily_reminder_time: Optional[str] = None
    weekly_report_enabled: bool
    notification_enabled: bool
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    last_checkin: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=6)
