import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext
from datetime import datetime
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

# Crear usuario irontoto si no existe
user = db.query(User).filter(User.username == "irontoto").first()
if not user:
    user = User(
        id=uuid.uuid4(),
        email="irontoto7@gmail.com",
        username="irontoto",
        hashed_password=pwd_context.hash("***"),
        display_name="Iron Toto",
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    print("Usuario irontoto creado")
else:
    user.hashed_password = pwd_context.hash("***")
    user.updated_at = datetime.utcnow()
    db.commit()
    print("Usuario irontoto actualizado (password reset)")

# Verificar ambos usuarios
users = db.query(User).all()
print("\nUsuarios en DB:")
for u in users:
    print(f"  - {u.username} ({u.email}) active={u.is_active} role={u.role}")

db.close()
