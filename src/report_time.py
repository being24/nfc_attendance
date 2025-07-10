import argparse
import csv
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.calc_time import WeeklyTimeData, calc_weekly_time_split
from src.db import AttendanceDB


class UserTimeReport(BaseModel):
    """ユーザーの時間レポートデータ"""

    card_id: str
    name: str
    total_business_hours: float  # 9-17時の合計時間（秒）
    total_other_hours: float  # その他の合計時間（秒）
    weekly_data: WeeklyTimeData


class TimeReportGenerator:
    """時間レポート生成クラス"""

    def __init__(self, db_file: Optional[str] = None):
        self.db = AttendanceDB(db_file)

    def generate_all_users_report(
        self, start_dt: datetime, end_dt: datetime
    ) -> List[UserTimeReport]:
        """全ユーザーの時間レポートを生成"""
        users = self.db.list_users()
        reports: List[UserTimeReport] = []

        for user in users:
            weekly_data = calc_weekly_time_split(
                user.card_id,
                start_dt,
                end_dt,
            )

            # 週間データから合計時間を計算
            total_business = sum(
                [
                    weekly_data.monday.business_hours,
                    weekly_data.tuesday.business_hours,
                    weekly_data.wednesday.business_hours,
                    weekly_data.thursday.business_hours,
                    weekly_data.friday.business_hours,
                    weekly_data.saturday.business_hours,
                    weekly_data.sunday.business_hours,
                ]
            )

            total_other = sum(
                [
                    weekly_data.monday.other_hours,
                    weekly_data.tuesday.other_hours,
                    weekly_data.wednesday.other_hours,
                    weekly_data.thursday.other_hours,
                    weekly_data.friday.other_hours,
                    weekly_data.saturday.other_hours,
                    weekly_data.sunday.other_hours,
                ]
            )

            total_business += user.offset * 3600

            report = UserTimeReport(
                card_id=user.card_id,
                name=user.name,
                total_business_hours=total_business,
                total_other_hours=total_other,
                weekly_data=weekly_data,
            )
            reports.append(report)

        return reports

    def print_summary_report(
        self, start_dt: datetime, end_dt: datetime, show_weekly_detail: bool = False
    ) -> None:
        """サマリーレポートを標準出力に表示"""
        reports = self.generate_all_users_report(start_dt, end_dt)

        print(f"=== 勤怠時間レポート ({start_dt.date()} ～ {end_dt.date()}) ===\n")

        # ヘッダー
        print(f"{'名前':<15} {'カードID':<12} {'9-17時':<8} {'その他':<8} {'合計':<8}")
        print("-" * 60)

        total_business_all = 0.0
        total_other_all = 0.0

        # 各ユーザーの情報を表示
        for report in reports:
            business_hours = report.total_business_hours / 3600  # 時間に変換
            other_hours = report.total_other_hours / 3600
            total_hours = business_hours + other_hours

            total_business_all += business_hours
            total_other_all += other_hours

            print(
                f"{report.name:<15} {report.card_id:<12} "
                f"{business_hours:>6.1f}H {other_hours:>6.1f}H {total_hours:>6.1f}H"
            )

            # 週間詳細を表示する場合
            if show_weekly_detail:
                self._print_weekly_detail(report.weekly_data)
                print()

        # 全体合計
        print("-" * 60)
        print(
            f"{'合計':<15} {'':<12} "
            f"{total_business_all:>6.1f}H {total_other_all:>6.1f}H "
            f"{total_business_all + total_other_all:>6.1f}H"
        )

    def _print_weekly_detail(self, weekly_data: WeeklyTimeData) -> None:
        """週間詳細を表示"""
        days = [
            ("  月", weekly_data.monday),
            ("  火", weekly_data.tuesday),
            ("  水", weekly_data.wednesday),
            ("  木", weekly_data.thursday),
            ("  金", weekly_data.friday),
            ("  土", weekly_data.saturday),
            ("  日", weekly_data.sunday),
        ]

        for day_name, day_data in days:
            if day_data.business_hours > 0 or day_data.other_hours > 0:
                business_h = day_data.business_hours / 3600
                other_h = day_data.other_hours / 3600
                print(
                    f"    {day_name}: 9-17時 {business_h:.1f}H, その他 {other_h:.1f}H"
                )

    def export_csv_report(
        self, start_dt: datetime, end_dt: datetime, output_file: Path
    ) -> None:
        """CSVファイルにレポートを出力"""

        reports = self.generate_all_users_report(start_dt, end_dt)

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow(
                [
                    "名前",
                    "カードID",
                    "9-17時(時間)",
                    "その他(時間)",
                    "合計(時間)",
                    "月_9-17",
                    "月_その他",
                    "火_9-17",
                    "火_その他",
                    "水_9-17",
                    "水_その他",
                    "木_9-17",
                    "木_その他",
                    "金_9-17",
                    "金_その他",
                    "土_9-17",
                    "土_その他",
                    "日_9-17",
                    "日_その他",
                ]
            )

            # データ行
            for report in reports:
                business_h = report.total_business_hours / 3600
                other_h = report.total_other_hours / 3600
                total_h = business_h + other_h

                w = report.weekly_data
                row = [
                    report.name,
                    report.card_id,
                    f"{business_h:.2f}",
                    f"{other_h:.2f}",
                    f"{total_h:.2f}",
                    f"{w.monday.business_hours / 3600:.2f}",
                    f"{w.monday.other_hours / 3600:.2f}",
                    f"{w.tuesday.business_hours / 3600:.2f}",
                    f"{w.tuesday.other_hours / 3600:.2f}",
                    f"{w.wednesday.business_hours / 3600:.2f}",
                    f"{w.wednesday.other_hours / 3600:.2f}",
                    f"{w.thursday.business_hours / 3600:.2f}",
                    f"{w.thursday.other_hours / 3600:.2f}",
                    f"{w.friday.business_hours / 3600:.2f}",
                    f"{w.friday.other_hours / 3600:.2f}",
                    f"{w.saturday.business_hours / 3600:.2f}",
                    f"{w.saturday.other_hours / 3600:.2f}",
                    f"{w.sunday.business_hours / 3600:.2f}",
                    f"{w.sunday.other_hours / 3600:.2f}",
                ]
                writer.writerow(row)

        print(f"レポートを {output_file} に出力しました。")


def main():
    """メイン関数 - コマンドライン実行用"""

    parser = argparse.ArgumentParser(description="勤怠時間レポート生成")
    parser.add_argument("--start", type=str, help="開始日 (YYYY-MM-DD)", default=None)
    parser.add_argument("--end", type=str, help="終了日 (YYYY-MM-DD)", default=None)
    parser.add_argument("--weekly", action="store_true", help="週間詳細を表示")
    parser.add_argument("--csv", type=str, help="CSVファイル出力パス")
    parser.add_argument("--db", type=str, help="データベースファイルパス")

    args = parser.parse_args()

    # デフォルトは今期（4-9月 or 10-3月）
    today = date.today()
    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    else:
        # 今期の開始日を計算
        year = today.year
        if today.month >= 4 and today.month <= 9:
            # 4-9月期間
            start_date = date(year, 4, 1)
        else:
            # 10-3月期間
            if today.month >= 10:
                start_date = date(year, 10, 1)
            else:
                start_date = date(year - 1, 10, 1)

    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    else:
        end_date = today

    start_dt = datetime.combine(start_date, time(0, 0, 0))
    end_dt = datetime.combine(end_date, time(23, 59, 59))

    # レポート生成
    generator = TimeReportGenerator(args.db)

    if args.csv:
        # pathlib.Pathを使ってパスを正規化
        output_path = Path(args.csv).resolve()
        generator.export_csv_report(start_dt, end_dt, output_path)
    else:
        generator.print_summary_report(start_dt, end_dt, args.weekly)


if __name__ == "__main__":
    main()
