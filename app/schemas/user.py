from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    FARMER = "farmer"
    ADMIN = "admin"
    AGRONOMIST = "agronomist"


class UserBase(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    full_name: str


class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.FARMER


class UserLogin(BaseModel):
    phone_number: str
    password: str


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    wallet_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None


class FarmBase(BaseModel):
    name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    size_acres: Optional[float] = None
    crop_type: Optional[str] = None


class FarmCreate(FarmBase):
    pass


class FarmResponse(FarmBase):
    id: int
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
