from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Activity
from app.schemas import Activity as ActivitySchema, ActivityCreate

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])

@router.get("/", response_model=List[ActivitySchema])
def get_activities(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    activities = db.query(Activity).order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()
    return activities

@router.post("/", response_model=ActivitySchema)
def create_activity(activity: ActivityCreate, db: Session = Depends(get_db)):
    db_activity = Activity(**activity.model_dump())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity
