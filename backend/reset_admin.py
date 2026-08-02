import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
user = db.query(User).filter(User.username == "admin").first()

if user:
    user.hashed_password = pwd_context.hash("***")
    user.updated_at = datetime.utcnow()
    db.commit()
    print("Password reseteada para admin")
else:
    print("Usuario admin no encontrado")

db.close()
