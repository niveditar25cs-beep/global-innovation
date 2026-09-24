from typing import List, Optional
from pydantic import BaseModel
import datetime

class CourseBase(BaseModel):
    code: str
    name: str

class CourseCreate(CourseBase):
    pass

class Course(CourseBase):
    id: int

    class Config:
        from_attributes = True

class DeadlineBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: datetime.datetime
    is_completed: bool = False
    course_id: Optional[int] = None

class DeadlineCreate(DeadlineBase):
    pass

class Deadline(DeadlineBase):
    id: int
    owner_id: int
    course: Optional[Course] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    deadlines: List[Deadline] = []

    class Config:
        from_attributes = True
