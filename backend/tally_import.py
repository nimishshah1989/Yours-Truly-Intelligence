"""Direct Tally XML importer — for large files that exceed the API upload limit.

Usage inside the container:
    python tally_import.py /app/tally_data.xml
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

from database import SessionLocal
from etl.etl_tally import import_tally_file
from models import Restaurant, TallyUpload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("ytip.tally_import")


def run(filepath: Path) -> None:
    if not filepath.exists():
        logger.error("File not found: %s", filepath)
        sys.exit(1)

    db = SessionLocal()
    try:
        restaurant = db.query(Restaurant).filter(Restaurant.is_active == True).first()
        if not restaurant:
            logger.error("No active restaurant found — run seed first")
            sys.exit(1)

        logger.info("Importing Tally file: %s (%d bytes)", filepath.name, filepath.stat().st_size)

        # Create a TallyUpload record so the UI can show import history
        upload = TallyUpload(
            restaurant_id=restaurant.id,
            filename=filepath.name,
            file_size=filepath.stat().st_size,
            status="pending",
            uploaded_at=datetime.utcnow(),
        )
        db.add(upload)
        db.flush()
        upload_id = upload.id
        db.commit()

        result = import_tally_file(restaurant, db, filepath, upload_id)
        db.commit()

        logger.info(
            "\nTally import complete: fetched=%d created=%d skipped=%d parse_errors=%d",
            result.records_fetched,
            result.records_created,
            result.records_skipped,
            result.parse_errors,
        )

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        path = Path("/app/tally_data.xml")
    else:
        path = Path(sys.argv[1])
    run(path)
