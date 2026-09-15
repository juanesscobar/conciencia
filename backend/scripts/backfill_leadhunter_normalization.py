"""Backfill idempotente: puebla normalized_name/domain/phone en leads existentes.

Uso: .venv\\Scripts\\python scripts\\backfill_leadhunter_normalization.py
Corre contra DATABASE_URL de app.config (SQLite dev / Postgres prod).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal  # noqa: E402
from app.modules.leadhunter.models import Lead  # noqa: E402
from app.modules.leadhunter.normalization import normalize_company, norm_phone, domain_of  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        leads = db.query(Lead).all()
        updated = 0
        for lead in leads:
            nname = normalize_company(lead.company)
            ndomain = domain_of(lead.website)
            nphone = norm_phone(lead.phone)
            if (
                lead.normalized_name != nname
                or lead.normalized_domain != ndomain
                or lead.normalized_phone != nphone
            ):
                lead.normalized_name = nname
                lead.normalized_domain = ndomain
                lead.normalized_phone = nphone
                updated += 1
        db.commit()
        print(f"Backfill OK: {len(leads)} leads revisados, {updated} actualizados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
