from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# User
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        orm_mode = True

# Task
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "new"
    deadline: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    owner_id: int

    class Config:
        orm_mode = True

# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
