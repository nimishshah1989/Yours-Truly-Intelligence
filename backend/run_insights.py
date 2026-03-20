"""One-off script to generate Claude deep insights and store them."""
import json
import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO)

from database import SessionLocal
from models import IntelligenceFinding
from services.insight_generator import generate_deep_insights

db = SessionLocal()
as_of = date.today() - timedelta(days=1)

# Clear old findings
deleted = db.query(IntelligenceFinding).filter(
    IntelligenceFinding.restaurant_id == 5
).delete()
db.commit()
print(f"Cleared {deleted} old findings")

# Generate Claude-powered insights
findings = generate_deep_insights(db, 5, as_of)
for f in findings:
    db.add(f)
db.commit()

print(f"\nGenerated {len(findings)} Claude insights:")
for f in findings:
    impact = f"₹{f.rupee_impact // 100:,}" if f.rupee_impact else "N/A"
    print(f"\n  [{f.severity}] [{f.category}] {f.title}")
    print(f"  Impact: {impact}")
    if f.detail:
        print(f"  Narrative: {f.detail.get('narrative', '')[:150]}")
        print(f"  Action: {f.detail.get('action', '')[:150]}")

db.close()
