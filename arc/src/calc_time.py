import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from datetime import datetime, time
from typing import Optional, Tuple
from pydantic import BaseModel
from src.db import AttendanceDB, AttendanceType, AttendanceSchema


class DayTimeData(BaseModel):
    business_hours: float  # 9-17時の秒数
    other_hours: float  # それ以外の秒数


class WeeklyTimeData(BaseModel):
    monday: DayTimeData
    tuesday: DayTimeData
    wednesday: DayTimeData
    thursday: DayTimeData
    friday: DayTimeData
    saturday: DayTimeData
    sunday: DayTimeData


def calc_total_time(
    card_id: str, start_dt: datetime, end_dt: datetime, db_file: Optional[str] = None
) -> float:
    """
    指定カードID・期間内の入退室ペアの合計滞在時間（秒）を返す。
    退出記録から直前の入室を探し、ペアが成立した場合のみ加算。
    """
    db = AttendanceDB(db_file)
    records: list[AttendanceSchema] = db.search_records_during(
        card_id=card_id, start=start_dt, end=end_dt
    )
    total_seconds: float = 0.0
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
                    # 日付をまたぐ場合は無効
                    if prev.timestamp.date() == rec.timestamp.date():
                        delta = (rec.timestamp - prev.timestamp).total_seconds()
                        if delta > 0:
                            total_seconds += delta
                    break  # 1つの入室に対して1つの退出のみ対応
    return total_seconds


def calc_total_time_split(
    card_id: str, start_dt: datetime, end_dt: datetime, db_file: Optional[str] = None
) -> Tuple[float, float]:
    weekly = calc_weekly_time_split(card_id, start_dt, end_dt, db_file)
    total_9_17 = (
        weekly.monday.business_hours
        + weekly.tuesday.business_hours
        + weekly.wednesday.business_hours
        + weekly.thursday.business_hours
        + weekly.friday.business_hours
        + weekly.saturday.business_hours
        + weekly.sunday.business_hours
    )
    total_other = (
        weekly.monday.other_hours
        + weekly.tuesday.other_hours
        + weekly.wednesday.other_hours
        + weekly.thursday.other_hours
        + weekly.friday.other_hours
        + weekly.saturday.other_hours
        + weekly.sunday.other_hours
    )
    return total_9_17, total_other


def _find_matching_checkin(
    records: list[AttendanceSchema], checkout_index: int, used_in: set[int]
) -> Tuple[Optional[int], Optional[AttendanceSchema]]:
    """退室記録に対応する入室記録を探す"""
    checkout_rec: AttendanceSchema = records[checkout_index]
    for j in range(checkout_index - 1, -1, -1):
        prev = records[j]
        if (
            prev.type == AttendanceType.CLOCK_IN
            and prev.timestamp < checkout_rec.timestamp
            and j not in used_in
            and prev.timestamp.date()
            == checkout_rec.timestamp.date()  # 日付をまたがない
        ):
            return j, prev
    return None, None


def _calculate_time_periods(t_in: datetime, t_out: datetime) -> Tuple[float, float]:
    """入退室ペアの9-17時とその他の時間を計算"""
    nine = time(9, 0, 0)
    seventeen = time(17, 0, 0)
    business_hours = 0.0
    other_hours = 0.0

    cur = t_in
    while cur < t_out:
        date = cur.date()
        nine_today = datetime.combine(date, nine)
        seventeen_today = datetime.combine(date, seventeen)

        # 次の境界時刻を決定
        if cur < nine_today:
            next_boundary = min(nine_today, t_out)
        elif cur < seventeen_today:
            next_boundary = min(seventeen_today, t_out)
        else:
            next_boundary = t_out

        # 時間を加算
        delta = (next_boundary - cur).total_seconds()
        if nine_today <= cur < seventeen_today:
            business_hours += delta
        else:
            other_hours += delta

        cur = next_boundary

    return business_hours, other_hours


def calc_weekly_time_split(
    card_id: str, start_dt: datetime, end_dt: datetime, db_file: Optional[str] = None
) -> WeeklyTimeData:
    """
    曜日ごとに9-17時とそれ以外の積算時間（秒）を分けて返す。
    """
    db = AttendanceDB(db_file)
    records: list[AttendanceSchema] = db.search_records_during(
        card_id=card_id, start=start_dt, end=end_dt
    )

    # 曜日別の時間集計用辞書（0=月曜、6=日曜）
    weekday_times: dict[int, dict[str, float]] = {
        i: {"business_hours": 0.0, "other_hours": 0.0} for i in range(7)
    }
    used_in: set[int] = set()

    # 退室記録を基準に入退室ペアを作成
    for i, rec in enumerate(records):
        if rec.type != AttendanceType.CLOCK_OUT:
            continue

        # 対応する入室記録を探す
        checkin_index, checkin_rec = _find_matching_checkin(records, i, used_in)
        if checkin_index is None or checkin_rec is None:
            continue

        # 時間を計算
        weekday = checkin_rec.timestamp.weekday()
        business_hours, other_hours = _calculate_time_periods(
            checkin_rec.timestamp, rec.timestamp
        )

        # 曜日別に加算
        weekday_times[weekday]["business_hours"] += business_hours
        weekday_times[weekday]["other_hours"] += other_hours
        used_in.add(checkin_index)

    # WeeklyTimeDataに変換
    return WeeklyTimeData(
        monday=DayTimeData(**weekday_times[0]),
        tuesday=DayTimeData(**weekday_times[1]),
        wednesday=DayTimeData(**weekday_times[2]),
        thursday=DayTimeData(**weekday_times[3]),
        friday=DayTimeData(**weekday_times[4]),
        saturday=DayTimeData(**weekday_times[5]),
        sunday=DayTimeData(**weekday_times[6]),
    )


if __name__ == "__main__":
    # IDをハードコーディング
    card_id = "card_id_example"
    today = datetime.now().date()
    start_dt = datetime.combine(today, time(0, 0, 0))
    end_dt = datetime.combine(today, time(23, 59, 59))

    # 従来の関数
    t_9_17, t_other = calc_total_time_split(card_id, start_dt, end_dt)
    print(f"合計 - 9-17時: {t_9_17 / 3600:.2f} Hour  その他: {t_other / 3600:.2f} Hour")

    # 新しい曜日別関数
    weekly_data = calc_weekly_time_split(card_id, start_dt, end_dt)
    print("\n曜日別時間:")
    for day_name, day_data in [
        ("月曜", weekly_data.monday),
        ("火曜", weekly_data.tuesday),
        ("水曜", weekly_data.wednesday),
        ("木曜", weekly_data.thursday),
        ("金曜", weekly_data.friday),
        ("土曜", weekly_data.saturday),
        ("日曜", weekly_data.sunday),
    ]:
        print(
            f"{day_name}: 9-17時 {day_data.business_hours / 3600:.2f}H, その他 {day_data.other_hours / 3600:.2f}H"
        )
