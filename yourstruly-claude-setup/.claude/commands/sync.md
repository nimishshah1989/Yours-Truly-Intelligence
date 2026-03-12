# /sync — PetPooja & Tally Data Sync Operations

## Purpose
Handles all data ingestion operations — initial backfill, manual sync triggers, and sync debugging.

## Sub-Commands

### /sync backfill [days]
Backfill historical PetPooja order data.
```bash
# Example: backfill last 90 days
python backend/ingestion/etl_orders.py --backfill --days=90
```
- Iterates from today backwards
- For each date D, requests D+1 from API (T-1 adjustment)
- Logs every day's result to sync_log table
- Skips dates that already have data (idempotent)
- Reports: total orders ingested, any failed dates

### /sync orders [date]
Sync a specific date's orders. If no date given, syncs yesterday.
```bash
python backend/ingestion/etl_orders.py --date=2026-03-10
```

### /sync menu
Refresh menu items from DineIn Menu API.
```bash
python backend/ingestion/etl_menu.py
```
- Upserts all items (update if exists, insert if new)
- Marks items no longer in API response as `is_active=false`

### /sync inventory [date]
Sync stock snapshot for a specific date.
```bash
python backend/ingestion/etl_inventory.py --date=2026-03-10
```

### /sync status
Check sync health — show last sync time and record count for each data source.
```sql
SELECT source, sync_date, records_inserted, status, created_at
FROM sync_log
ORDER BY created_at DESC
LIMIT 20;
```

### /sync debug [date]
Debug a failed sync — show raw API response and the exact error.
- Call the API directly and print raw JSON
- Check if the date has T-1 lag issues
- Check for pagination (50-record cap on inventory APIs)

## T-1 Lag Reference (critical — never forget this)
| What you want | Date to pass in API call |
|---|---|
| Data for March 10 | Pass March 11 |
| Data for March 9 | Pass March 10 |
| Yesterday's data | Pass today's date |

## Pagination Pattern for Inventory APIs
```python
async def fetch_all_records(endpoint, params):
    all_records = []
    ref_id = ""
    while True:
        params["refId"] = ref_id
        response = await call_api(endpoint, params)
        records = response.get("data", [])
        all_records.extend(records)
        if len(records) < 50:
            break  # Last page
        ref_id = records[-1]["id"]  # Use last record ID as cursor
    return all_records
```
