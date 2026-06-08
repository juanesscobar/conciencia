"""Celery tasks for JobScout"""

from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal

from .service import JobScoutService
from .models import OpportunityStatus


@shared_task
def scout_all_sources():
    """Run all scrapers and save opportunities"""
    import asyncio
    
    db = SessionLocal()
    try:
        service = JobScoutService(db)
        result = asyncio.run(service.run_scout())
        
        return {
            "status": "completed",
            "total_found": result.get("total_found", 0),
            "total_new": result.get("total_new", 0),
            "sources": [r["source"] for r in result.get("results", [])]
        }
    finally:
        db.close()


@shared_task
def cleanup_expired_opportunities():
    """Mark old opportunities as expired"""
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Mark opportunities older than 30 days as expired
        cutoff = datetime.utcnow() - timedelta(days=30)
        
        db.query(Opportunity).filter(
            Opportunity.created_at < cutoff,
            Opportunity.status != OpportunityStatus.EXPIRED
        ).update({
            "status": OpportunityStatus.EXPIRED
        })
        
        db.commit()
        return {"status": "completed"}
    finally:
        db.close()


@shared_task
def generate_daily_digest():
    """Generate daily digest of top opportunities"""
    db = SessionLocal()
    try:
        service = JobScoutService(db)
        opps = service.get_digest_opportunities(limit=10)
        
        # Format for Telegram or other notification
        if not opps:
            return {"status": "no_opportunities"}
        
        lines = [
            "🎯 *JobScout Daily Digest*",
            f"📋 {len(opps)} nuevas oportunidades",
            ""
        ]
        
        for opp in opps:
            score_emoji = "🔥" if opp.score >= 70 else "⭐" if opp.score >= 40 else "📌"
            type_emoji = {
                "microtask": "🧩",
                "full_time": "💼",
                "freelance": "🎨",
                "gig": "⚡",
                "survey": "📊"
            }.get(opp.type.value if hasattr(opp.type, 'value') else str(opp.type), "📌")
            
            lines.append(f"{type_emoji} {score_emoji} *{opp.title}*")
            lines.append(f"   🏢 {opp.company}")
            lines.append(f"   📍 {', '.join(opp.location_restrictions[:2])}")
            if opp.salary_text and opp.salary_text != "Not specified":
                lines.append(f"   💰 {opp.salary_text}")
            lines.append(f"   🔗 {opp.url}")
            lines.append(f"   📊 Score: {opp.score}/100")
            lines.append("")
        
        message = "\n".join(lines)
        
        # Mark as seen after including in digest
        for opp in opps:
            opp.status = OpportunityStatus.SEEN
        db.commit()
        
        # Here you would send to Telegram if configured
        # For now, just return the message
        return {
            "status": "completed",
            "message": message,
            "count": len(opps)
        }
    finally:
        db.close()
