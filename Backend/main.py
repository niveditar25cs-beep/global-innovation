from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Academic Deadline Management System API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(email=user.email, username=user.username, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/courses/", response_model=schemas.Course)
def create_course(course: schemas.CourseCreate, db: Session = Depends(get_db)):
    db_course = models.Course(code=course.code, name=course.name)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@app.get("/courses/", response_model=List[schemas.Course])
def read_courses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Course).offset(skip).limit(limit).all()


@app.post("/users/{user_id}/deadlines/", response_model=schemas.Deadline)
def create_deadline_for_user(
    user_id: int, deadline: schemas.DeadlineCreate, db: Session = Depends(get_db)
):
    db_deadline = models.Deadline(**deadline.model_dump(), owner_id=user_id)
    db.add(db_deadline)
    db.commit()
    db.refresh(db_deadline)
    return db_deadline


@app.get("/deadlines/", response_model=List[schemas.Deadline])
def read_deadlines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    deadlines = db.query(models.Deadline).offset(skip).limit(limit).all()
    return deadlines
