from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.calc_time import calc_total_time_split
from src.db import AttendanceDB

CARD_ID = "012E5527A2C2383D"


def main() -> None:
    # デフォルトのdata/attendance.dbを使用
    db = AttendanceDB()
    today = datetime.now().date()
    year = today.year

    # 年度判定：1-3月なら前年度、4月以降なら今年度
    fiscal_year = year if today.month >= 4 else year - 1

    # 期間設定（handle_card_touched_for_confirmと同じ）
    start1 = datetime(fiscal_year, 4, 1)
    end1 = datetime(fiscal_year, 9, 18, 23, 59, 59)
    start2 = datetime(fiscal_year, 9, 19)
    end2 = datetime(fiscal_year + 1, 3, 31, 23, 59, 59)

    # レコード確認用に全件列挙
    records1 = db.search_records_during(CARD_ID, start1, end1)
    records2 = db.search_records_during(CARD_ID, start2, end2)

    def fmt_records(label: str, records):
        print(f"--- {label}: {len(records)} records")
        for r in records:
            t = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {t}  type={r.type}")

    fmt_records("4-9", records1)
    fmt_records("10-3", records2)

    t1_9_17, t1_other = calc_total_time_split(CARD_ID, start1, end1)
    t2_9_17, t2_other = calc_total_time_split(CARD_ID, start2, end2)

    print("\n=== calc_total_time_split result (hours)")
    print(f"4-9月: 9-17 {t1_9_17 / 3600:.2f}h, その他 {t1_other / 3600:.2f}h")
    print(f"10-3月: 9-17 {t2_9_17 / 3600:.2f}h, その他 {t2_other / 3600:.2f}h")


if __name__ == "__main__":
    main()
