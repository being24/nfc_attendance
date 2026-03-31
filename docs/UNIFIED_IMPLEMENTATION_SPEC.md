# NFC勤怠システム 統合実装仕様（確定版）

## 1. 本仕様の位置づけ
本仕様は `codex_prompts_nfc_attendance.md` を正とし、既存実装の有用要素を取り込みつつ、開発実装で直接使える統合仕様として定義する。

- アーキテクチャ: あなたのMD（FastAPI中心）を採用
- ドメイン仕様: あなたのMD（FSM + pending touch）を採用
- DBモデル: あなたのMD（7テーブル構成）を採用
- API仕様: あなたのMDを採用
- CSV文字コード: `UTF-8`（BOMなし）
- 追加要件:
  - 最終退出者に「施錠アラート」を表示
  - 本日在室表（在室者一覧）を表示
- 時間計算方針:
  - 内部: セッション時間 - 休憩時間（完全保持）
  - 表示: 9:00-17:00に該当する時間のみ表示用に集計可能

## 2. 技術スタック・バージョン
- Python `3.12`
- FastAPI
- Jinja2
- HTMX
- SQLAlchemy 2.x
- SQLite
- pytest
- reader側: Python + pyscard（別プロセス）

## 3. システム構成

### 3.1 構成方針
- サーバ側（FastAPI）に業務ロジックを集約する
- readerプロセスはカード読取とAPI送信に専念する
- ドメインロジックはFSMで明示的に管理する

### 3.2 ディレクトリ構成
```text
nfc_attendance/
  app/
    main.py
    config.py
    db.py
    deps.py

    models/
    schemas/
    routers/
    services/
    repositories/
    domain/
    templates/
    static/

  reader/
  tests/
```

## 4. ドメイン仕様

### 4.1 状態・操作（FSM）
- 状態:
  - `OUTSIDE`
  - `IN_ROOM`
  - `OUT_ON_BREAK`
- 操作:
  - `ENTER`
  - `LEAVE_TEMP`
  - `RETURN`
  - `LEAVE_FINAL`

### 4.2 正常遷移
- `OUTSIDE + ENTER -> IN_ROOM`
- `IN_ROOM + LEAVE_TEMP -> OUT_ON_BREAK`
- `OUT_ON_BREAK + RETURN -> IN_ROOM`
- `IN_ROOM + LEAVE_FINAL -> OUTSIDE`

上記以外は不正遷移とし、専用例外を送出する。

### 4.3 Pending Touch
- `touch_token`（UUID文字列）
- `student_id`
- `card_id`
- `reader_name`
- `detected_at`
- `current_status`
- `allowed_actions`
- `expires_at`
- `is_expired(now)` を提供
- TTLは `20秒`

## 5. DBモデル
以下7テーブルを採用する。

- `students`
- `attendance_events`
- `attendance_status`
- `attendance_sessions`
- `break_periods`
- `audit_logs`
- `unknown_card_logs`

### 5.1 主要整合ルール
- `students.card_id` は unique
- `students.student_code` は unique
- `attendance_status` は student単位で現在状態を一意管理
- `attendance_sessions` は滞在セッション単位
- `break_periods` はセッション配下
- correctionはイベント追加で表現し、物理削除しない

### 5.2 時刻・タイムゾーン
- アプリ基準TZは `Asia/Tokyo`
- DB保存時刻の扱いは統一（naive/awareの方針を実装時に一本化）

## 6. リポジトリ/サービス責務

### 6.1 repository層
- CRUD・検索・集計のDBアクセスを隠蔽
- ドメイン判断（遷移可否など）は持ち込まない

### 6.2 service層（中核）
#### `attendance_service.prepare_touch(card_id, reader_name, detected_at)`
- 学生照合（card_id）
- 未登録カードは `unknown_card_logs` 保存 + 専用例外
- 無効学生は専用例外
- 現在状態を取得し allowed actions を返却
- pending touch をメモリ保存（TTL 20秒）

#### `attendance_service.confirm_touch(touch_token, action, now=None)`
- pending touch 検証（期限・action妥当性）
- FSMで次状態決定
- `attendance_events` 保存
- `attendance_status` 更新
- `attendance_sessions` / `break_periods` 更新
- 必要時に監査ログ保存

#### `attendance_service.get_today_attendance()`
- 本日在室者一覧
- 本日イベント一覧
- 管理画面表示用データを返却

## 7. API仕様（採用）

### 7.1 Reader API
- `POST /api/reader/touches`
- `POST /api/reader/touches/{touch_token}/confirm`
- 認証: `X-Reader-Token`

### 7.2 Student API
- `GET /api/students`
- `POST /api/students`
- `PATCH /api/students/{student_id}`
- `GET /api/students/{student_id}`

### 7.3 Attendance/Admin/Export API
- `GET /api/attendance/today`
- `POST /api/admin/corrections`
- `GET /api/export/monthly.csv?year=YYYY&month=MM`

### 7.4 CSV仕様（確定）
- 文字コード: `UTF-8`（BOMなし）
- 月次明細CSVを返す

## 8. 時間計算仕様（確定）

### 8.1 内部保持（正規値）
- セッション実時間 = `left_at - entered_at`
- 休憩合計 = セッション配下 `break_periods` の総和
- 正味在室時間 = `セッション実時間 - 休憩合計`
- これを内部の正規値として保持する

### 8.2 表示用集計（9-17ルール）
- 表示時は `09:00-17:00` 枠に重なる時間のみを算出できること
- 9-17外時間も内部値として保持し、必要に応じて別表示可能にする
- 画面/CSVで何を表示するかは用途別に切替可能とする

## 9. 追加業務要件（今回追加）

### 9.1 最終退出者アラート（施錠）
`LEAVE_FINAL` 確定時に以下を判定:

- 判定: 当該時点で `IN_ROOM` の在室者が0人になるか
- 0人になる場合:
  - レスポンスに `lock_alert_required=true` を含める
  - UIに「最終退出者です。施錠してください」を表示
  - 監査目的で通知発生をログ化（event memo または audit_log）
- 0人でない場合:
  - `lock_alert_required=false`

### 9.2 在室表表示
- 管理画面で本日在室者一覧を表示する
- 最低表示項目:
  - 学籍番号
  - 氏名
  - 入室時刻
  - 現在状態
  - 累計在室時間（必要なら簡易）
- データソースは `attendance_status + open session + student` の結合で取得

## 10. 画面要件（Jinja2/HTMX）
- `/` 打刻待受
- 完了画面 / エラー画面
- 管理画面:
  - 本日在室一覧
  - 学生一覧/登録/編集
  - イベント一覧
  - CSV出力
- 簡易ログイン（セッション認証）
- 未ログイン時は管理画面アクセス不可

## 11. 例外・監査
- ドメイン例外とアプリ例外を分離
- RouterでHTTPエラーへマッピング
- correctionはイベント追加方式
- correction時に監査ログ必須

## 12. テスト要件
- domain（FSM, pending_touch, time_utils）
- model smoke
- repository
- service（正常系・異常系）
- API
- auth
- error handling
- readerの実機非依存部分（debounce, client）

## 13. 開発進行ルール
`codex_prompts_nfc_attendance.md` のPhase順をそのまま採用する。

1. Phase 1: domain/FSM
2. Phase 2: DB基盤・モデル
3. Phase 3: repository
4. Phase 4: schema
5. Phase 5: service
6. Phase 6: router/API
7. Phase 7: templates/UI
8. Phase 8: reader
9. Phase 9: auth
10. Phase 10: 例外整理・README

## 14. 実装上の補足決定
- 既存GUI（DearPyGui）実装は移行対象として扱い、新規主系はFastAPI系に統一する
- 旧仕様にある「9-17時表示」の要件は、表示レイヤ要件として継承する
- 既存コードの `offset` 相当機能は、必要であれば `students.note` または別カラム追加で明示的に設計する

