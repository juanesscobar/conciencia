import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext
import uuid
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
hashed_password = pwd_context.hash("admin123")

user = User(
    id=uuid.uuid4(),
    email="admin@missioncontrol.local",
    username="admin",
    hashed_password=hashed_password,
    display_name="Admin",
    role="admin",
    is_active=True,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

db.add(user)
db.commit()
db.close()

print("✅ Usuario admin creado")
print("Email: admin@missioncontrol.local")
print("Username: admin")
print("Password: admin123")
