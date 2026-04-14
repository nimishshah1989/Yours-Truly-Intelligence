"""Agent scheduler — thin wrapper.

The CLI commands live in scheduler/cli.py (backfill, summary, verify, stock, cogs).
The production cron scheduler lives in etl/scheduler.py (started from main.py).
The pipeline orchestration lives in scheduler/pipeline.py.

This file exists for backwards compatibility. Running `python scheduler/agent_scheduler.py`
delegates to cli.py.
"""

from scheduler.cli import main

if __name__ == "__main__":
    main()
