from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, database, utils

router = APIRouter()

@router.post("/", response_model=schemas.TaskResponse)
def create_task(task: schemas.TaskCreate, db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    new_task = models.Task(**task.dict(), owner_id=user.id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("/", response_model=List[schemas.TaskResponse])
def get_tasks(db: Session = Depends(database.get_db), user=Depends(utils.get_current_user)):
    return db.query(models.Task).filter(models.Task.owner_id == user.id).all()
