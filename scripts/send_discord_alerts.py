import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# GitHub Actions executes this file from scripts/, so add the repo root
# to Python's import path before importing local service modules.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.database import init_db
from services.discord_alerts import load_alert_watchlist, send_discord_alert
from services.watchlist import trade_desk_watchlist


def scheduled_label() -> tuple[str, bool]:
    """Return run label and whether the current time is an intended scheduled window."""
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    if event_name == "workflow_dispatch":
        return "Manual Discord alert test", True

    now_bkk = datetime.now(ZoneInfo("Asia/Bangkok"))
    now_ny = datetime.now(ZoneInfo("America/New_York"))

    # 09:00 Bangkok daily scan
    if now_bkk.hour == 9:
        return "09:00 Bangkok daily scan", True

    # 09:00 New York = 30 minutes before normal US market open. Weekdays only.
    # Workflow has both 13:00 and 14:00 UTC cron entries; this guard handles DST.
    if now_ny.weekday() < 5 and now_ny.hour == 9:
        return "30 min before US market open", True

    return "Outside target alert window", False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Send even outside scheduled windows")
    parser.add_argument("--include-empty", action="store_true", help="Send a no-candidates message")
    args = parser.parse_args()

    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    scan_limit = int(os.getenv("SCAN_LIMIT", "50"))

    label, should_run = scheduled_label()
    if not should_run and not args.force:
        print(label)
        return

    init_db()
    loaded = load_alert_watchlist()
    print(f"Loaded alert watchlist rows: {loaded}")

    desk = trade_desk_watchlist(limit=scan_limit)
    ok, status = send_discord_alert(webhook, desk, run_label=label, include_empty=args.include_empty)
    print(status)
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
