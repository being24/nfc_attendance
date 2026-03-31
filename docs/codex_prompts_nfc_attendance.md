# Codex投入用プロンプト集

以下は、NFC勤怠管理システムを段階的に実装するための、Codex投入用プロンプト集である。  
各プロンプトは**順番に投入すること**を前提とする。  
一度に全部実装させず、Phaseごとに区切って進めること。

前提:

- Python 3.12
- FastAPI
- Jinja2
- HTMX
- SQLAlchemy 2.x
- SQLite
- pytest
- カード読み取りは別途 Python + pyscard で実装する
- FastAPI + Jinja2/HTMX 構成
- 業務ロジックは reader 側ではなくサーバ側に置く
- 状態遷移は明示的な FSM として実装する

---

## 共通ルール（最初に一緒に渡してよい）

以下のルールに従って実装してください。

- Python 3.12 を前提にする
- SQLAlchemy は 2.x スタイルで書く
- 型ヒントを付ける
- Pydantic スキーマを分離する
- router / service / repository / domain / models を分離する
- pytest によるテストを書く
- 1つのファイルに全部詰め込まない
- コメントは最小限でよいが、責務の境界は明確にする
- 既存コードを壊さないよう、段階的に追加する
- 依存ライブラリは必要最小限にする
- 関数名・クラス名・ファイル名は一貫性を持たせる
- テンプレートはシンプルでよい
- 過剰な抽象化は不要
- 実装後、変更ファイル一覧と実装内容の要約を出す
- 時間計算は「内部保持=セッション-休憩」「表示=9:00-17:00の表示用集計」を両立する
- CSVの文字コードは `UTF-8`（BOMなし）を使用する
- 最終退出者には施錠アラートを返せる設計にする
- 本日在室表（在室者一覧）を表示できる設計にする

プロジェクト構成は以下を前提とする。

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

---

# Phase 1: domain と状態遷移の実装

## Prompt 1-1: enum と状態遷移本体

以下の仕様で、勤怠状態遷移FSMを実装してください。

要件:

- Python 3.12
- `app/domain/enums.py`
- `app/domain/state_machine.py`
- `app/domain/rules.py`
- `tests/test_state_machine.py`
  を作成してください

仕様:

- 状態は以下の3種類
  - `OUTSIDE`
  - `IN_ROOM`
  - `OUT_ON_BREAK`
- 操作は以下の4種類
  - `ENTER`
  - `LEAVE_TEMP`
  - `RETURN`
  - `LEAVE_FINAL`

状態遷移表:

- `OUTSIDE` + `ENTER` -> `IN_ROOM`
- `IN_ROOM` + `LEAVE_TEMP` -> `OUT_ON_BREAK`
- `IN_ROOM` + `LEAVE_FINAL` -> `OUTSIDE`
- `OUT_ON_BREAK` + `RETURN` -> `IN_ROOM`

不正遷移:

- 上記以外はすべて不正とする
- 不正遷移時は専用例外を送出すること

実装要件:

- Enum を用いること
- 遷移判定ロジックを pure function で実装すること
- `get_allowed_actions(state)` も実装すること
- 不正遷移用の例外クラスを定義すること
- pytest で正常系・異常系の単体テストを作ること

出力してほしいもの:

- 追加/更新したファイル一覧
- 実装概要
- テスト観点

---

## Prompt 1-2: touch token と pending touch 用のドメイン定義

以下を実装してください。

対象:

- `app/domain/pending_touch.py`
- `tests/test_pending_touch.py`

要件:

- カードタッチ後、操作確定前の一時状態を表す dataclass もしくは Pydantic モデルを実装する
- 必須フィールド:
  - `touch_token: str`
  - `student_id: int`
  - `card_id: str`
  - `reader_name: str | None`
  - `detected_at: datetime`
  - `current_status`
  - `allowed_actions`
  - `expires_at: datetime`
- `is_expired(now)` を実装する
- `touch_token` は UUID文字列を想定する
- テストを書く

注意:

- 永続化方法はまだ実装しなくてよい
- まずは domain として表現できればよい

---

## Prompt 1-3: 時間計算ユーティリティ

以下を実装してください。

対象:

- `app/domain/time_utils.py`
- `tests/test_time_utils.py`

要件:

- タイムゾーンは `Asia/Tokyo` を前提にする
- 以下の関数を実装する
  - `now_jst()`
  - `minutes_between(start, end) -> int`
  - `clamp_non_negative_minutes(value) -> int`
- `minutes_between` は分単位の整数を返す
- 負数にならないように扱う補助関数も用意する
- pytest を書く

---

# Phase 2: DB モデルとDB基盤

## Prompt 2-1: SQLAlchemy基盤

以下を実装してください。

対象:

- `app/config.py`
- `app/db.py`

要件:

- Python 3.12
- SQLAlchemy 2.x
- SQLite 用の DB 接続設定を実装する
- 設定値は環境変数またはデフォルト値で扱えるようにする
- `Base` を定義する
- `engine`
- `SessionLocal`
- `get_db()` dependency
  を実装する

要件詳細:

- デフォルトの SQLite ファイルは `./attendance.db`
- `future=True` の 2.x スタイル
- セッションは context manager で安全に扱える構成にする
- FastAPI dependency として利用できる `get_db()` を提供する

まだ実装しなくてよいもの:

- Alembic
- migration

---

## Prompt 2-2: SQLAlchemy モデル実装

以下の SQLAlchemy モデルを実装してください。

対象:

- `app/models/student.py`
- `app/models/attendance_event.py`
- `app/models/attendance_status.py`
- `app/models/attendance_session.py`
- `app/models/break_period.py`
- `app/models/audit_log.py`
- `app/models/unknown_card_log.py`

必要なら:

- `app/models/__init__.py`

仕様:

### students

- id: Integer PK
- student_code: String, unique, not null
- name: String, not null
- card_id: String, unique, not null
- is_active: Boolean, default True
- note: Text, nullable
- created_at: DateTime
- updated_at: DateTime

### attendance_events

- id: Integer PK
- student_id: FK
- event_type: String, not null
- occurred_at: DateTime, not null
- source: String, not null
- reader_name: String, nullable
- operator_name: String, nullable
- memo: Text, nullable
- created_at: DateTime

### attendance_status

- student_id: PK + FK
- current_status: String, not null
- last_event_id: Integer, nullable
- updated_at: DateTime

### attendance_sessions

- id: Integer PK
- student_id: FK
- entered_at: DateTime, not null
- left_at: DateTime, nullable
- total_minutes: Integer, nullable
- status: String, not null

### break_periods

- id: Integer PK
- session_id: FK
- started_at: DateTime, not null
- ended_at: DateTime, nullable

### audit_logs

- id: Integer PK
- actor_type: String, not null
- actor_name: String, nullable
- action: String, not null
- target_type: String, not null
- target_id: Integer, nullable
- detail_json: Text, nullable
- created_at: DateTime

### unknown_card_logs

- id: Integer PK
- card_id: String, not null
- reader_name: String, nullable
- detected_at: DateTime, not null
- created_at: DateTime

実装要件:

- SQLAlchemy 2.x declarative style
- relationship は必要最小限でよい
- created_at / updated_at の扱いを適切にする
- nullable / unique / index を適切に設定する
- 外部キーを張る
- タイムスタンプのデフォルトに `now_jst()` 相当の関数または datetime を利用する

---

## Prompt 2-3: モデル作成確認テスト

以下を実装してください。

対象:

- `tests/test_models_smoke.py`

要件:

- SQLite のテストDB上で全テーブルを作成できることを確認する
- 最低限、`Student` 1件を insert / select できることを確認する
- unique 制約の最低限の確認をする

---

# Phase 3: repository 層

## Prompt 3-1: student repository

以下を実装してください。

対象:

- `app/repositories/student_repository.py`
- `tests/test_student_repository.py`

要件:

- SQLAlchemy Session を受け取る repository クラスを実装する
- 以下のメソッドを実装する
  - `get_by_id(student_id)`
  - `get_by_card_id(card_id)`
  - `get_by_student_code(student_code)`
  - `list_all(include_inactive=False)`
  - `create(student_code, name, card_id, note=None)`
  - `update(student, **kwargs)`
  - `deactivate(student)`
- `card_id` と `student_code` の重複時は適切に例外を扱う
- pytest を書く

---

## Prompt 3-2: attendance repository

以下を実装してください。

対象:

- `app/repositories/attendance_repository.py`
- `tests/test_attendance_repository.py`

要件:

- 以下の操作を扱う repository を実装する
  - attendance_event の追加
  - attendance_status の取得・更新
  - open session の取得
  - session の作成・更新
  - break_period の開始・終了
  - 当日イベント一覧取得
- repository はドメインロジックを持ちすぎないこと
- DB操作を隠蔽すること
- pytest を書く

---

## Prompt 3-3: unknown card repository と audit repository

以下を実装してください。

対象:

- `app/repositories/unknown_card_repository.py`
- `app/repositories/audit_repository.py`
- `tests/test_unknown_card_repository.py`
- `tests/test_audit_repository.py`

要件:

- 未登録カードログ保存
- 監査ログ保存
  を行う repository を実装する
- 最低限 create と list のテストを書く

---

# Phase 4: schema 層

## Prompt 4-1: Pydantic schemas 実装

以下を実装してください。

対象:

- `app/schemas/student.py`
- `app/schemas/reader.py`
- `app/schemas/attendance.py`
- `app/schemas/admin.py`

必要なスキーマ:

### student

- `StudentCreate`
- `StudentUpdate`
- `StudentResponse`

### reader

- `ReaderTouchRequest`
- `ReaderTouchResponse`
- `ReaderTouchConfirmRequest`
- `ReaderTouchConfirmResponse`

### attendance

- `AttendanceEventResponse`
- `TodayAttendanceResponse`

### admin

- `CorrectionRequest`

要件:

- Pydantic v2 を前提にする
- バリデーションを適切に書く
- enum と整合するようにする
- FastAPI response_model で使いやすい形にする

---

# Phase 5: service 層（最重要）

## Prompt 5-1: student service

以下を実装してください。

対象:

- `app/services/student_service.py`
- `tests/test_student_service.py`

要件:

- repository を使って student のユースケースを実装する
- 以下を含む
  - 学生登録
  - 学生更新
  - 学生一覧取得
  - 学生無効化
- duplicate card_id / duplicate student_code の扱いを整理する
- active student のみを既定で返すこと
- pytest を書く

---

## Prompt 5-2: attendance service

以下を実装してください。

対象:

- `app/services/attendance_service.py`
- `tests/test_attendance_service.py`

要件:

- この service が本システムの中心
- repository 群と domain/state_machine を使って勤怠処理を実装する

実装してほしいメソッド:

1. `prepare_touch(card_id, reader_name, detected_at)`
   - 学生を card_id で引く
   - 見つからなければ unknown card log を保存する
   - active でなければエラー
   - 現在状態を取得する
   - allowed_actions を返す
   - pending touch を生成する
   - touch token はメモリ上ストアで保持してよい
   - TTL は 20 秒

2. `confirm_touch(touch_token, action, now=None)`
   - pending touch を取得する
   - 期限切れならエラー
   - allowed_actions に action が含まれないならエラー
   - state machine で次状態を求める
   - attendance_event を保存する
   - attendance_status を更新する
   - session / break_period を更新する
   - 完了レスポンスを返す

3. `get_today_attendance()`
   - 本日在室・本日イベント一覧など、必要最小限でよい

重要仕様:

- `OUTSIDE + ENTER` で session 新規作成
- `IN_ROOM + LEAVE_TEMP` で break_period 開始
- `OUT_ON_BREAK + RETURN` で break_period 終了
- `IN_ROOM + LEAVE_FINAL` で session 終了し、在室分を計算
- 在室時間 = `(left_at - entered_at) - break合計`
- 内部ではセッション実時間・休憩時間・正味在室時間を保持する
- 表示用として 9:00-17:00 枠の時間を算出できる関数/メソッドを用意する
- 不正遷移では例外
- 未登録カードは専用例外
- 無効学生も専用例外
- pytest で正常系・異常系をしっかり書く

追加仕様:

- `LEAVE_FINAL` 確定時、在室者が0人になる場合は施錠アラートを返す
  - 例: `lock_alert_required=true`
- 在室者が残る場合は `lock_alert_required=false`
- `get_today_attendance()` では本日在室表に必要な情報を返す
  - 学籍番号
  - 氏名
  - 入室時刻
  - 現在状態
  - 累計在室時間（必要十分な精度でよい）

---

## Prompt 5-3: audit service と correction service

以下を実装してください。

対象:

- `app/services/audit_service.py`
- `app/services/correction_service.py`
- `tests/test_correction_service.py`

要件:

- correction は初版では「イベント追加ベース」でよい
- 元イベントを物理削除しない
- correction 時に audit log を必ず残す
- correction request を受けて event を追加できる構成にする
- pytest を書く

---

# Phase 6: FastAPI router 実装

## Prompt 6-1: app/main.py と router 登録

以下を実装してください。

対象:

- `app/main.py`
- `app/routers/__init__.py`

要件:

- FastAPI アプリを作る
- router を include する
- Jinja2 templates を設定する
- static files を mount する
- `/health` を作る
- 起動に必要な最小構成を整える

---

## Prompt 6-2: reader router

以下を実装してください。

対象:

- `app/routers/reader.py`
- `tests/test_reader_api.py`

要件:

- `POST /api/reader/touches`
- `POST /api/reader/touches/{touch_token}/confirm`
  を実装する
- service を呼ぶだけに近い薄い router にする
- `X-Reader-Token` による簡易認証を実装する
- token は config から読む
- 例外を HTTPException にマッピングする
- pytest で API テストを書く

---

## Prompt 6-3: student router

以下を実装してください。

対象:

- `app/routers/students.py`
- `tests/test_students_api.py`

要件:

- `GET /api/students`
- `POST /api/students`
- `PATCH /api/students/{student_id}`
- `GET /api/students/{student_id}`
  を実装する
- service を使う
- JSON API として動作する
- テストを書く

---

## Prompt 6-4: attendance / admin / export router

以下を実装してください。

対象:

- `app/routers/attendance.py`
- `app/routers/admin.py`
- `app/routers/export.py`
- `tests/test_export_csv.py`

要件:

- `GET /api/attendance/today`
- `POST /api/admin/corrections`
- `GET /api/export/monthly.csv?year=YYYY&month=MM`
  を実装する
- CSV は UTF-8（BOMなし）で返す
- 月次明細CSVを返す
- reader confirm系レスポンスに施錠アラート情報を含められるようにする
- テストを書く

---

# Phase 7: Jinja2 / HTMX ページ実装

## Prompt 7-1: pages router と最低限のテンプレート

以下を実装してください。

対象:

- `app/routers/pages.py`
- `app/templates/base.html`
- `app/templates/index.html`
- `app/templates/error.html`
- `app/templates/touch_result.html`
- `app/static/app.css`

要件:

- `/` で打刻待受画面を表示する
- シンプルなレイアウトを作る
- 待受画面には「学生証をタッチしてください」と表示する
- 完了画面・エラー画面のテンプレートを用意する
- CSS は最小限でよい

注意:

- この段階では reader との連動UIを無理に作り込まなくてよい
- まずページが成立することを優先する

---

## Prompt 7-2: 管理画面テンプレート

以下を実装してください。

対象:

- `app/templates/admin_today.html`
- `app/templates/admin_students.html`
- `app/templates/admin_student_form.html`
- `app/templates/admin_events.html`
- `app/templates/admin_export.html`

必要なら:

- `app/static/app.js`

要件:

- 本日在室一覧ページ
- 学生一覧ページ
- 学生登録/編集ページ
- イベント一覧ページ
- CSV出力ページ
  を Jinja2 で実装する
- HTMX を使ってフォーム送信や部分更新を少し取り入れてよい
- 見た目はシンプルでよい
- まず業務利用できるUIを優先する
- 本日在室一覧には、学籍番号・氏名・入室時刻・状態・累計在室時間を表示する
- 最終退出時の施錠アラートを管理画面/結果画面で明確に表示する

---

# Phase 8: reader プロセス実装

## Prompt 8-1: reader の最小実装

以下を実装してください。

対象:

- `reader/main.py`
- `reader/observer.py`
- `reader/debounce.py`
- `reader/client.py`

要件:

- Python + pyscard を使う
- `CardMonitor` / `CardObserver` を使う
- `insert` イベントのみ扱う
- `remove` は無視する
- callback 内で重い処理をしすぎない
- カードIDを取得して API に POST する
- debounce 秒数はデフォルト2秒
- API base URL と Reader token を設定可能にする
- ログを出す
- 例外時に落ちっぱなしにならないようにする

前提:

- 既存の pyscard 実装断片を活かしてよい
- DB には直接触れない
- FastAPI の `/api/reader/touches` を叩く

---

## Prompt 8-2: reader のテスト可能部分

以下を実装してください。

対象:

- `tests/test_reader_debounce.py`
- `tests/test_reader_client.py`

要件:

- debounce ロジックをテストする
- HTTP client 部分をテストする
- pyscard 実機依存部分は無理に自動テストしなくてよい
- テスト可能な純粋ロジックを切り出すこと

---

# Phase 9: 認証と管理者機能の最低限整備

## Prompt 9-1: 管理者ログインの最小実装

以下を実装してください。

対象:

- `app/routers/auth.py`
- `app/templates/login.html`
- 必要な session middleware 設定
- `tests/test_auth.py`

要件:

- 管理画面向けの簡易ログインを実装する
- 管理者ユーザは環境変数ベースでもよい
- セッション認証を使う
- 未ログイン時は管理画面へアクセスできない
- 最低限のログイン・ログアウト機能を実装する

---

# Phase 10: 最終仕上げ

## Prompt 10-1: 例外整理と共通エラーハンドリング

以下を実装してください。

対象:

- `app/exceptions.py`
- 必要な service / router 修正
- `tests/test_error_handling.py`

要件:

- ドメイン例外、アプリケーション例外を整理する
- FastAPI 側で共通エラーハンドリングを入れる
- JSON API と HTML ページの両方で破綻しにくい構成にする
- エラーメッセージを整理する

---

## Prompt 10-2: README と起動手順整備

以下を実装してください。

対象:

- `README.md`

要件:

- セットアップ手順
- 起動方法
- テスト方法
- 開発用コマンド
- 環境変数一覧
- reader の起動方法
- FastAPI サーバの起動方法
  をまとめる

---

# 投入順の推奨

以下の順番で投入すること。

1. Prompt 1-1
2. Prompt 1-2
3. Prompt 1-3
4. Prompt 2-1
5. Prompt 2-2
6. Prompt 2-3
7. Prompt 3-1
8. Prompt 3-2
9. Prompt 3-3
10. Prompt 4-1
11. Prompt 5-1
12. Prompt 5-2
13. Prompt 5-3
14. Prompt 6-1
15. Prompt 6-2
16. Prompt 6-3
17. Prompt 6-4
18. Prompt 7-1
19. Prompt 7-2
20. Prompt 8-1
21. Prompt 8-2
22. Prompt 9-1
23. Prompt 10-1
24. Prompt 10-2

---

# 使い方の注意

- 1回で全部投げない
- 1プロンプトごとに差分を確認する
- 特に `attendance_service` はテスト込みで確認する
- API と画面を同時に作り込みすぎない
- まず domain / service / test を固める
- reader は最後のほうでつなぐ
- UI は最低限から始める
- バグが出たら、そのファイルだけ局所修正させる

---

# 最初にCodexへ貼る短い前置き

以下を各プロンプトの前に付けてもよい。

このプロジェクトは、学生証のFeliCaカードを使った勤怠管理システムです。  
FastAPI + Jinja2/HTMX + SQLAlchemy + SQLite を使います。  
カード読み取りは Python + pyscard の別プロセスです。  
業務ロジックはサーバ側に集約します。  
段階的に実装したいので、今回の依頼範囲だけを実装してください。  
既存ファイルとの整合性を保ち、変更ファイル一覧・実装概要・テスト内容を最後に示してください。
