"""Crea/actualiza el usuario admin local.

La password se toma de la env var LOCAL_ADMIN_PASSWORD (o ADMIN_PASSWORD como alias).
- Si la variable existe -> se aplica (idempotente: actualiza si el usuario ya existe).
- Si NO existe y el usuario ya existe -> NO toca la password (seguro para prod).
- Si NO existe y el usuario no existe -> genera una aleatoria y la imprime en el log
  (útil para el primer arranque sin configurar).

Uso:
    LOCAL_ADMIN_PASSWORD=mipass python scripts/seed_local_admin.py
"""
import sys
import os
import secrets
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.services.auth import hash_password

Base.metadata.create_all(bind=engine)

USERNAME = os.getenv("LOCAL_ADMIN_USER", "admin")
EMAIL = os.getenv("LOCAL_ADMIN_EMAIL", "toto@missioncontrol.ai")
PASSWORD = os.getenv("LOCAL_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or ""

db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == USERNAME).first()

    if existing:
        if PASSWORD:
            existing.hashed_password = hash_password(PASSWORD)
            db.commit()
            print(f"admin '{USERNAME}' actualizado (password reseteada desde env)")
        else:
            print(f"admin '{USERNAME}' ya existe — password NO modificada (LOCAL_ADMIN_PASSWORD no definida)")
    else:
        if not PASSWORD:
            PASSWORD = secrets.token_urlsafe(12)
            print(f"⚠️  LOCAL_ADMIN_PASSWORD no definida — se generó una password aleatoria:")
            print(f"    usuario: {USERNAME}")
            print(f"    password: {PASSWORD}")
            print(f"    (cambiala luego desde Configuración o con LOCAL_ADMIN_PASSWORD)")
        db.add(User(
            email=EMAIL,
            username=USERNAME,
            hashed_password=hash_password(PASSWORD),
            display_name="Iron Toto",
            role="ceo",
            is_active=True,
        ))
        db.commit()
        print(f"admin '{USERNAME}' creado")
finally:
    db.close()
