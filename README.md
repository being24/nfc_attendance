# NFC Attendance Server

FastAPI + Jinja2/HTMX + SQLAlchemy + SQLite で実装した、NFC勤怠管理システムのサーバ側です。

## セットアップ

```bash
uv sync
```

プロジェクト直下の `.env` は起動時に自動で読み込まれます。
必要に応じて `.env.example` をコピーして `.env` を作成してください。

## 起動方法

### FastAPIサーバ

```bash
uv run fastapi dev app/main.py
```

または

```bash
uv run python -m uvicorn app.main:app --reload
```

## テスト方法

```bash
uv run python -m pytest -q
```

## 開発用コマンド

```bash
# 静的チェック
uv run ruff check app tests

# テスト
uv run python -m pytest -q
```

## 環境変数

- `DATABASE_URL`（default: `sqlite:///./attendance.db`）
- `API_BASE_URL`（default: `http://127.0.0.1:8000`、reader用）
- `READER_TOKEN`（default: `dev-reader-token`）
- `READER_NAME`（default: `dummy-reader`、reader用）
- `SESSION_SECRET_KEY`（default: `dev-session-secret`）
- `ADMIN_USERNAME`（default: `admin`）
- `ADMIN_PASSWORD`（default: `admin`）
- `ADMIN_CARD_IDS`（default: `ADMIN-CARD-001`、カンマ区切り）

## Readerプロセス起動（ダミー運用可）

実機リーダーが無くても、ダミーreaderでAPI連携を検証できます。

```bash
# 1回だけ疑似タッチ（allowed_actionsの先頭を自動選択）
uv run python -m reader.main --base-url http://127.0.0.1:8000 --card-id CARD1

# ループ送信
uv run python -m reader.main --base-url http://127.0.0.1:8000 --card-id CARD1 --loop
```

主なオプション:
- `--action ENTER|LEAVE_TEMP|RETURN|LEAVE_FINAL|auto`（default: `auto`）
- `--reader-token`（default: `dev-reader-token`）
- `--interval` / `--cooldown`

## API概要

- Reader:
  - `POST /api/reader/touches`
  - `POST /api/reader/touches/{touch_token}/confirm`
- Students:
  - `GET /api/students`
  - `POST /api/students`
  - `GET /api/students/{student_id}`
  - `PATCH /api/students/{student_id}`
- Attendance/Admin/Export:
  - `GET /api/attendance/today`
  - `POST /api/admin/corrections`（ログインセッション必須）
  - `GET /api/export/monthly.csv?year=YYYY&month=MM`

## 画面

- `/` 打刻待受
- `/login` 管理者ログイン
- `/admin/today` 本日在室
- `/admin/students` 学生一覧・編集
- `/admin/events` 本日イベント
- `/admin/export` CSV出力

## 時間計算方針

- DB保存は Unix timestamp（秒）
- 内部正規値: セッション時間 - 休憩時間
- 表示用: 9:00-17:00の集計関数を別提供

## 文字コード

- CSV出力は UTF-8（BOMなし）
