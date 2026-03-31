# NFC勤怠システム 実装指示リファレンス

## 1. 目的と適用範囲
本ドキュメントは、`nfc_attendance` リポジトリ内スクリプトの実装仕様を、改修・再実装・外部仕様書との統合に使える粒度で定義する。

- 対象エントリポイント
  - `main.py`（GUIアプリ）
  - `src/report_time.py`（CLIレポート）
- 対象ライブラリ
  - `src/attendance_reader.py`（NFC読み取り・カードイベント）
  - `src/db.py`（DBアクセス）
  - `src/calc_time.py`（勤怠時間集計）
  - `src/log_config.py`（ログ設定）

## 2. 実行環境・依存
`pyproject.toml` より:

- Python: `>=3.13`
- 必須依存:
  - `dearpygui`
  - `pydantic`
  - `pyscard`
  - `sqlalchemy`
- 開発依存:
  - `pytest`
  - `ruff`

実行例:

```bash
uv sync
uv run main.py
uv run src/report_time.py --start 2025-12-01 --end 2026-01-08 --csv report.csv
```

## 3. ファイル責務マップ

- `main.py`
  - GUI構築
  - NFCカードイベント受信
  - 入室/退室記録、ユーザー登録、確認表示
- `src/attendance_reader.py`
  - リーダー選択 (`SONY FeliCa` 部分一致)
  - カードID読取（APDU `FF CA 00 00 00`）
  - カード挿抜イベント通知
- `src/db.py`
  - SQLiteスキーマ定義
  - 勤怠レコード・ユーザーCRUD
  - 期間検索、CSV出力
- `src/calc_time.py`
  - 入退室ペア化
  - 9-17時/その他時間の分割集計
  - 曜日別集計
- `src/report_time.py`
  - 全ユーザー期間集計
  - 標準出力レポート/CSV出力
- `src/log_config.py`
  - 回転ログ設定（`logs/log.log`）

## 4. DB仕様（`src/db.py`）

### 4.1 テーブル定義

#### `attendance`
- `id` INTEGER PK AUTOINCREMENT
- `timestamp` DATETIME NOT NULL
- `card_id` STRING NOT NULL
- `type` INTEGER NOT NULL
  - `1`: CLOCK_IN
  - `2`: CLOCK_OUT

#### `card_user`
- `id` INTEGER PK AUTOINCREMENT
- `card_id` STRING UNIQUE NOT NULL
- `name` STRING NOT NULL
- `student_number` STRING NULL
- `is_admin` BOOLEAN NOT NULL DEFAULT `False`
- `offset` FLOAT NOT NULL DEFAULT `0.0`

### 4.2 DBファイル配置
- 既定: `<repo>/data/attendance.db`
- `AttendanceDB(db_file=...)` で差し替え可能

### 4.3 主要API

- `add_record(card_id, type_, timestamp=None) -> int`
- `search_records(card_id=None, type_=None, year=None, month=None) -> list[AttendanceSchema]`
- `search_records_during(card_id, start, end) -> list[AttendanceSchema]`
- `upsert_user(card_id, name=None, is_admin=None, student_number=None, offset=None) -> int`
- `get_user(card_id) -> CardUserSchema | None`
- `list_users() -> list[CardUserSchema]`

## 5. NFC読み取り仕様（`src/attendance_reader.py`）

### 5.1 リーダー選択
- `NFCReader.__init__(reader_name_keyword="SONY FeliCa")`
- 接続済みリーダー一覧から `reader.name` にキーワード部分一致する最初の1件を採用。
- 未検出時は `NFCReaderError` を送出。

### 5.2 カードID取得
- APDU: `[0xFF, 0xCA, 0x00, 0x00, 0x00]`
- 受信バイト列を16進文字列（空白除去）へ変換。

### 5.3 イベント監視
`CardEventObserver` が `callback(event_type, card_id, error=None)` を呼び出す。

- `event_type="insert"`: 挿入時。読取成功なら `card_id`、失敗なら `error`。
- `event_type="remove"`: 離脱時。`card_id` は `None`。

## 6. 時間計算仕様（`src/calc_time.py`）

### 6.1 入退室ペア化ルール
- 対象期間内レコードを時系列取得。
- `CLOCK_OUT` ごとに、直前へ遡って未使用の `CLOCK_IN` を1つ対応。
- 同日ペアのみ有効（`checkin.date == checkout.date`）。
- 対応できない `OUT` は無視。

### 6.2 9-17時分割ロジック
- 境界時刻: `09:00:00`, `17:00:00`
- `checkin` から `checkout` までを区間分割し、
  - `09:00 <= t < 17:00` を `business_hours`
  - それ以外を `other_hours`
- 単位は秒で内部保持。

### 6.3 出力データ型
- `DayTimeData`: `business_hours`, `other_hours`（秒）
- `WeeklyTimeData`: 月〜日の `DayTimeData`

## 7. GUI仕様（`main.py`）

### 7.1 初期化順序
1. `NFCReader` 生成
2. `AttendanceDB` 生成
3. `CardMonitor` 生成
4. DearPyGuiコンテキスト・フォントロード
5. 画面作成（固定 `800x400`）

### 7.2 主要UI要素
- 上段ボタン: `確認`, `入力`, `登録`, `出力`
- 主ボタン: `入室`, `退室`
- 全ボタン処理はカードタッチポップアップ経由（または直接読取成功時は即時処理）

### 7.3 モード別処理

#### `in`
- カードID取得
- `add_record(card_id, CLOCK_IN, now)`
- 完了ポップアップ表示

#### `out`
- カードID取得
- `add_record(card_id, CLOCK_OUT, now)`
- 完了ポップアップ表示

#### `register`
- カードID取得
- 名前/学籍番号入力ポップアップ
- `upsert_user(card_id, name, is_admin=False, student_number=...)`

#### `confirm`
- カードID取得
- 年度を4月開始で判定
- 期間1: `4/1 - 9/18 23:59:59`
- 期間2: `9/19 - 翌年3/31 23:59:59`
- 各期間で `calc_total_time_split` を実行
- 名前と集計値をポップアップ表示

#### `input`（管理者操作導線）
- 管理者カード認証を要求
- 管理者カード離脱後に `admin_action` モードへ遷移
- `admin_action` で `offset` 入力・`upsert_user(card_id, offset=...)`

### 7.4 タイムアウト
- カード待機ポップアップは `600フレーム` 後に自動クローズ。

## 8. CLIレポート仕様（`src/report_time.py`）

### 8.1 引数
- `--start YYYY-MM-DD`（省略時: 今期開始）
- `--end YYYY-MM-DD`（省略時: 今日）
- `--weekly`（曜日詳細表示）
- `--csv <path>`（CSV出力）
- `--db <path>`（DB差し替え）

### 8.2 今期開始日の計算
- `4-9月`: `YYYY-04-01`
- `10-12月`: `YYYY-10-01`
- `1-3月`: `(YYYY-1)-10-01`

### 8.3 生成処理
1. `db.list_users()` で対象ユーザー取得
2. 各ユーザーで `calc_weekly_time_split(card_id, start_dt, end_dt)`
3. 曜日合算で `total_business_hours`, `total_other_hours` を計算
4. 標準出力またはCSVに整形

### 8.4 CSV列定義
固定順:
`名前, 学籍番号, カードID, 9-17時(時間), その他(時間), 合計(時間), 月_9-17, 月_その他, ... , 日_その他`

## 9. ログ仕様（`src/log_config.py`）
- 出力先: `<repo>/logs/log.log`
- ローテーション: `maxBytes=32KB`, `backupCount=3`
- ハンドラ: ファイル + 標準出力
- ロガー名: `main`

## 10. 実装時の重要制約

- `main.py` はUIスレッド上での描画更新を `dpg.set_frame_callback` で同期している。
  - 新規UI追加時も同様にUIスレッド同期を維持すること。
- 集計ロジックは「同日内ペア」前提。
  - 日跨ぎ勤務を扱う場合、`calc_time.py` の仕様変更が必要。
- `card_user.name` は `NOT NULL`。
  - `upsert_user` 新規時 `name=None` だと空文字で保存される。

## 11. 既知の実装ギャップ（現行コード準拠）

- GUIの `出力` ボタンは `show_card_touch_popup("csv", ...)` を呼ぶが、
  - `show_card_touch_popup` の直接読取分岐に `mode == "csv"` がない
  - `on_card_touched` のイベント分岐にも `mode == "csv"` がない
- 結果として `csv` モードの実処理が未実装。

## 12. 改修指示テンプレート
外部仕様書と接続する際は、以下フォーマットで指示を追加すること。

- 変更対象: `ファイルパス`
- 変更目的: `何を満たすか`
- 入力: `UI操作/CLI引数/DB値`
- 出力: `画面表示/CSV/DB更新`
- 正常系フロー: `手順1..n`
- 異常系フロー: `エラー条件と表示/ログ`
- 受け入れ条件: `テスト観点（最低3件）`
- 互換性: `既存仕様への影響`

## 13. 最低限の検証コマンド

```bash
# 単体テスト
uv run pytest

# レポート（標準出力）
uv run src/report_time.py --start 2025-12-01 --end 2026-01-08 --weekly

# レポート（CSV）
uv run src/report_time.py --start 2025-12-01 --end 2026-01-08 --csv ./report.csv
```
