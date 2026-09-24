from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    deadlines = relationship("Deadline", back_populates="owner")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)

    deadlines = relationship("Deadline", back_populates="course")

class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    due_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_completed = Column(Boolean, default=False)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))

    owner = relationship("User", back_populates="deadlines")
    course = relationship("Course", back_populates="deadlines")
