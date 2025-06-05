import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import datetime, time
from src.db import AttendanceDB, AttendanceType


def calc_total_time(
    card_id: str, start_dt: datetime, end_dt: datetime, db_file=None
) -> float:
    """
    指定カードID・期間内の入退室ペアの合計滞在時間（秒）を返す。
    退出記録から直前の入室を探し、ペアが成立した場合のみ加算。
    """
    db = AttendanceDB(db_file)
    records = db.search_records_during(card_id=card_id, start=start_dt, end=end_dt)
    total_seconds = 0.0
    # 退出（CLOCK_OUT）を基準に、その直前の入室（CLOCK_IN）を探す
    for i, rec in enumerate(records):
        if rec.type == AttendanceType.CLOCK_OUT:
            # 直前の入室を逆順で探す
            for j in range(i - 1, -1, -1):
                prev = records[j]
                if (
                    prev.type == AttendanceType.CLOCK_IN
                    and prev.timestamp < rec.timestamp
                ):
                    delta = (rec.timestamp - prev.timestamp).total_seconds()
                    if delta > 0:
                        total_seconds += delta
                    break  # 1つの入室に対して1つの退出のみ対応
    return total_seconds


def calc_total_time_split(
    card_id: str, start_dt: datetime, end_dt: datetime, db_file=None
) -> tuple[float, float]:
    """
    9～17時台の積算時間（秒）と、それ以外の積算時間（秒）を分けて返す。
    """
    db = AttendanceDB(db_file)
    records = db.search_records_during(card_id=card_id, start=start_dt, end=end_dt)
    nine = time(9, 0, 0)
    seventeen = time(17, 0, 0)
    inout_pairs = []
    # 退出（CLOCK_OUT）を基準に、その直前の入室（CLOCK_IN）を探す
    used_in = set()
    for i, rec in enumerate(records):
        if rec.type == AttendanceType.CLOCK_OUT:
            for j in range(i - 1, -1, -1):
                prev = records[j]
                if (
                    prev.type == AttendanceType.CLOCK_IN
                    and prev.timestamp < rec.timestamp
                    and j not in used_in
                ):
                    inout_pairs.append((prev.timestamp, rec.timestamp))
                    used_in.add(j)
                    break
    total_9_17 = 0.0
    total_other = 0.0
    for t_in, t_out in inout_pairs:
        cur = t_in
        while cur < t_out:
            next_point = min(
                datetime.combine(cur.date(), seventeen)
                if cur.time() < seventeen
                else t_out,
                t_out,
            )
            if nine <= cur.time() < seventeen:
                # 9:00～17:00の区間
                delta = (next_point - cur).total_seconds()
                total_9_17 += delta
            else:
                delta = (next_point - cur).total_seconds()
                total_other += delta
            cur = next_point
            if cur.time() == seventeen:
                # 17:00を超えたら次は17:00以降
                cur = datetime.combine(cur.date(), seventeen)
    return total_9_17, total_other


if __name__ == "__main__":
    # IDをハードコーディング
    card_id = "card_id_example"
    today = datetime.now().date()
    start_dt = datetime.combine(today, time(0, 0, 0))
    end_dt = datetime.combine(today, time(23, 59, 59))
    t_9_17, t_other = calc_total_time_split(card_id, start_dt, end_dt)
    print(f"9-17時: {t_9_17 / 3600:.2f} Hour  その他: {t_other / 3600:.2f} Hour")
