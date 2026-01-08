from datetime import datetime
from pathlib import Path

import dearpygui.dearpygui as dpg
from smartcard.CardMonitoring import CardMonitor

from src.attendance_reader import CardEventObserver, NFCReader
from src.calc_time import calc_total_time_split
from src.db import AttendanceDB, AttendanceType
from src.log_config import logger


def main():
    nfc_reader = NFCReader()
    # AttendanceDBインスタンスをmain関数の先頭で1つだけ生成
    db = AttendanceDB()
    monitor = CardMonitor()

    logger.info("Application started")
    dpg.create_context()
    # フォントの追加（グローバル指定、フォントヒント付き）
    font_path = (
        Path(__file__).resolve().parent
        / "data"
        / "BIZ_UDGothic"
        / "BIZUDGothic-Regular.ttf"
    )
    with dpg.font_registry():
        with dpg.font(str(font_path), 40, default_font=True) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
        with dpg.font(str(font_path), 28) as small_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)

    dpg.bind_font(default_font)

    dpg.create_viewport(
        title="Attendance Management System",
        width=800,
        height=400,
        x_pos=100,
        y_pos=100,
        vsync=True,
        resizable=False,  # 追加: リサイズ不可
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # ウィンドウサイズ取得
    win_width = 800  # viewportと同じ最大サイズに固定
    win_height = 400
    btn_width = int(win_width * 0.45)
    btn_height = int(win_height * 0.7)
    margin = int(win_width * 0.05)

    with dpg.window(
        label="勤怠管理",
        no_resize=True,
        no_collapse=True,
        no_title_bar=True,
        width=win_width,
        height=win_height,
        pos=(0, 0),
        horizontal_scrollbar=False,
        autosize=False,
        no_scrollbar=True,
    ):
        # 上部ボタン（確認・入力・登録・出力）は入室・退室ボタンの上のスペースに収める
        top_btn_h = int(btn_height * 0.27)  # 高さを今の2/3に
        top_btn_y = 12  # さらに上に
        btn_margin = int(win_width * 0.04)
        btn_w = int((win_width - btn_margin * 5) / 4)  # 均等配置
        btn_labels = ["確認", "入力", "登録", "出力"]
        btn_tags = ["confirm_btn", "input_btn", "register_btn", "csv_btn"]
        btns = []
        for i, (label, tag) in enumerate(zip(btn_labels, btn_tags)):
            btn_x = btn_margin + i * (btn_w + btn_margin)
            btn = dpg.add_button(
                label=label,
                width=btn_w,
                height=top_btn_h,
                pos=(btn_x, top_btn_y),
                tag=tag,
            )
            btns.append(btn)
        # コールバック設定（登録・出力のみ既存機能）
        dpg.set_item_callback(
            "register_btn",
            lambda: show_card_touch_popup("register", nfc_reader, monitor),
        )
        dpg.set_item_callback(
            "csv_btn", lambda: show_card_touch_popup("csv", nfc_reader, monitor)
        )
        # 出勤・退勤ボタンを横方向中央揃え・下方向に少しだけ間隔を広げて配置
        btns_total_width = btn_width * 2 + margin
        btns_start_x = int((win_width - btns_total_width) / 2)
        original_btn_y = int(win_height * 0.2)
        target_btn_y = int(win_height * 0.45)
        btn_y = original_btn_y + int((target_btn_y - original_btn_y) / 3)
        # 出勤ボタン（左・緑）
        with dpg.theme() as theme_in:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 180, 75, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 200, 95, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (40, 140, 55, 255))

        def on_register_name(card_id):
            name = dpg.get_value("register_name_input")
            student_number = dpg.get_value("register_student_number_input")
            if not name.strip():
                logger.info("名前が空欄のため登録しません")
                dpg.delete_item("register_name_popup")
                return
            # upsert_userで登録・更新を一括処理（学籍番号も渡す）
            db.upsert_user(card_id, name, is_admin=False, student_number=student_number)
            logger.info(
                f"Register user: card_id={card_id}, name={name}, student_number={student_number}"
            )
            dpg.delete_item("register_name_popup")

            # 完了メッセージはset_frame_callbackでUIスレッドにスケジューリング
            def show_done_popup():
                popup_width = int(win_width * 0.5)
                popup_height = 100
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="登録完了",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="register_done_popup",
                ):
                    dpg.add_text(
                        "登録完了",
                        pos=(int(popup_width / 2 - 80), int(popup_height / 2 - 18)),
                    )
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 120,
                    lambda s, a: dpg.delete_item("register_done_popup"),
                )

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: show_done_popup()
            )

        def handle_card_touched_for_register(card_id):
            user = db.get_user(card_id)
            user_name = user.name if user else ""
            user_student_number = (
                user.student_number if user and hasattr(user, "student_number") else ""
            )
            logger.info(f"Card touched for registration: {card_id}, User: {user_name}")

            def show_popup():
                if dpg.does_item_exist("register_name_popup"):
                    dpg.delete_item("register_name_popup")
                # show_confirm_popupと同じウインドウサイズ・位置に統一
                popup_width = int(win_width * 0.9)
                popup_height = int(win_height * 0.8)
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="名前登録",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    no_move=True,  # ウインドウ移動不可
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="register_name_popup",
                ):
                    with dpg.group():
                        dpg.add_text(
                            f"Card ID: {card_id}\n名前を入力してください",
                            pos=(60, 40),
                            tag="register_cardid_text",
                        )

                    dpg.bind_item_font("register_cardid_text", small_font)
                    # 入力欄を下に
                    input_y = 110
                    dpg.add_input_text(
                        hint="名前",
                        default_value=user_name or "",
                        width=popup_width - 120,
                        pos=(60, input_y),
                        tag="register_name_input",
                    )
                    dpg.add_input_text(
                        hint="学籍番号",
                        default_value=user_student_number or "",
                        width=popup_width - 120,
                        pos=(60, input_y + 70),
                        tag="register_student_number_input",
                    )
                    # ボタン横並び
                    btn_w = 144
                    btn_h = 72
                    btn_space = 40
                    btn_y = popup_height - btn_h
                    btn_x1 = int((popup_width - btn_w * 2 - btn_space) / 2)
                    btn_x2 = btn_x1 + btn_w + btn_space
                    btn_register = dpg.add_button(
                        label="登録",
                        width=btn_w,
                        height=btn_h,
                        pos=(btn_x1, btn_y),
                        callback=lambda: on_register_name(card_id),
                    )
                    btn_cancel = dpg.add_button(
                        label="キャンセル",
                        width=btn_w,
                        height=btn_h,
                        pos=(btn_x2, btn_y),
                        callback=lambda: dpg.delete_item("register_name_popup"),
                    )
                    dpg.bind_item_font(btn_register, small_font)
                    dpg.bind_item_font(btn_cancel, small_font)
                dpg.show_item("register_name_popup")

            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda s, a: show_popup())

        def handle_card_touched_for_in(card_id):
            now = datetime.now()
            db.add_record(card_id, AttendanceType.CLOCK_IN, now)
            logger.info(f"入室記録: card_id={card_id}, time={now}")

            # 完了メッセージ
            def show_in_done_popup():
                popup_width = int(win_width * 0.5)
                popup_height = 100
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="入室記録完了",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="in_done_popup",
                ):
                    dpg.add_text(
                        "入室を記録",
                        pos=(int(popup_width / 2 - 100), int(popup_height / 2 - 24)),
                    )
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 120,
                    lambda s, a: dpg.delete_item("in_done_popup"),
                )

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: show_in_done_popup()
            )

        def handle_card_touched_for_out(card_id):
            now = datetime.now()
            db.add_record(card_id, AttendanceType.CLOCK_OUT, now)
            logger.info(f"退室記録: card_id={card_id}, time={now}")

            # 完了メッセージ
            def show_out_done_popup():
                popup_width = int(win_width * 0.5)
                popup_height = 100
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="退室記録完了",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="out_done_popup",
                ):
                    dpg.add_text(
                        "退室を記録",
                        pos=(int(popup_width / 2 - 100), int(popup_height / 2 - 24)),
                    )
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 120,
                    lambda s, a: dpg.delete_item("out_done_popup"),
                )

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: show_out_done_popup()
            )

        def sudo_popup(card_id, on_success):
            user = db.get_user(card_id)
            if user and getattr(user, "is_admin", False):
                logger.info(f"管理者認証成功: {card_id}, name={user.name}")
                # 管理者カードが離れるまで待ってから次のカード読み取りを開始
                monitor = CardMonitor()
                already_handled = {"remove": False}

                def on_card_event(event_type, card_id, error=None):
                    if event_type == "remove" and not already_handled["remove"]:
                        already_handled["remove"] = True
                        try:
                            monitor.deleteObserver(observer)
                        except Exception:
                            pass
                        logger.info("管理者カードが離れたので次のカード受付を開始")
                        dpg.set_frame_callback(
                            dpg.get_frame_count() + 1,
                            lambda s, a: show_card_touch_popup(
                                "admin_action", nfc_reader, monitor
                            ),
                        )

                observer = CardEventObserver(on_card_event)
                monitor.addObserver(observer)
            else:
                logger.warning(f"管理者認証失敗: card_id={card_id}")

                # 管理者のみポップアップ（UIスレッドで表示、フォント小さく）
                def show_error():
                    popup_width = int(win_width * 0.5)
                    popup_height = 100
                    popup_x = int((win_width - popup_width) * 0.5)
                    popup_y = int((win_height - popup_height) * 0.5)
                    if dpg.does_item_exist("sudo_error_popup"):
                        dpg.delete_item("sudo_error_popup")
                    with dpg.window(
                        label="管理者認証エラー",
                        modal=True,
                        no_title_bar=True,
                        no_resize=True,
                        no_collapse=True,
                        width=popup_width,
                        height=popup_height,
                        pos=(popup_x, popup_y),
                        tag="sudo_error_popup",
                    ):
                        text_id = dpg.add_text(
                            "管理者のみ操作可能です",
                            pos=(
                                int(popup_width / 2 - 150),
                                int(popup_height / 2 - 12),
                            ),
                        )
                        dpg.bind_item_font(text_id, small_font)
                    dpg.show_item("sudo_error_popup")
                    dpg.set_frame_callback(
                        dpg.get_frame_count() + 120,
                        lambda s, a: dpg.delete_item("sudo_error_popup"),
                    )

                dpg.set_frame_callback(
                    dpg.get_frame_count() + 1, lambda s, a: show_error()
                )

        # --- admin_action: 2回目のカードタッチでoffset入力ポップアップ ---
        def handle_admin_action(card_id):
            user = db.get_user(card_id)
            logger.info(f"admin_action: card_id={card_id}, user={user}")
            popup_width = int(win_width * 0.6)
            popup_height = 180
            popup_x = int((win_width - popup_width) * 0.5)
            popup_y = int((win_height - popup_height) * 0.5)

            def on_offset_submit():
                try:
                    offset_val = float(dpg.get_value("offset_input"))
                except Exception:
                    offset_val = 0.0
                db.upsert_user(card_id, offset=offset_val)
                logger.info(f"offset updated: card_id={card_id}, offset={offset_val}")
                dpg.delete_item("offset_popup")

                # 完了メッセージはUIスレッドで確実に表示
                def show_done():
                    with dpg.window(
                        label="登録完了",
                        modal=True,
                        no_title_bar=True,
                        no_resize=True,
                        no_collapse=True,
                        width=popup_width,
                        height=80,
                        pos=(popup_x, popup_y + 40),
                        tag="offset_done_popup",
                    ):
                        dpg.add_text(
                            f"{offset_val:.1f} 時間で登録しました",
                            pos=(30, 30),
                        )
                        dpg.bind_item_font(dpg.last_item(), small_font)
                    dpg.set_frame_callback(
                        dpg.get_frame_count() + 120,
                        lambda s, a: dpg.delete_item("offset_done_popup"),
                    )

                dpg.set_frame_callback(
                    dpg.get_frame_count() + 1, lambda s, a: show_done()
                )

            # ポップアップ生成もUIスレッドで確実に
            def show_offset_popup():
                if dpg.does_item_exist("offset_popup"):
                    dpg.delete_item("offset_popup")
                # show_confirm_popupと同じウインドウサイズ・位置に統一
                popup_width = int(win_width * 0.9)
                popup_height = int(win_height * 0.8)
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="offset_popup",
                ):
                    # ラベル2列の間隔を広げる
                    label_x1 = 60
                    label_y = 40
                    id_text = dpg.add_text(
                        f"カードID: {card_id}\n時間を入力してください",
                        pos=(label_x1, label_y),
                    )
                    dpg.bind_item_font(id_text, small_font)
                    # 入力欄をもっと下に
                    input_y = label_y + 70
                    offset_input = dpg.add_input_float(
                        default_value=user.offset if user else 0.0,
                        width=popup_width - 120,
                        pos=(label_x1, input_y),
                        tag="offset_input",
                        format="%.3f",
                    )
                    dpg.bind_item_font(offset_input, small_font)
                    # ボタン横並び
                    btn_w = 144
                    btn_h = 72
                    btn_space = 40
                    btn_y = popup_height - btn_h - 30
                    btn_x1 = int((popup_width - btn_w * 2 - btn_space) / 2)
                    btn_x2 = btn_x1 + btn_w + btn_space
                    btn_register = dpg.add_button(
                        label="登録",
                        width=btn_w,
                        height=btn_h,
                        pos=(btn_x1, btn_y),
                        callback=on_offset_submit,
                    )
                    dpg.bind_item_font(btn_register, small_font)
                    btn_cancel = dpg.add_button(
                        label="キャンセル",
                        width=btn_w,
                        height=btn_h,
                        pos=(btn_x2, btn_y),
                        callback=lambda: dpg.delete_item("offset_popup"),
                    )
                    dpg.bind_item_font(btn_cancel, small_font)
                dpg.show_item("offset_popup")

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: show_offset_popup()
            )

        def show_read_error_popup(message="読み取りエラー\n管理者に連絡してください"):
            popup_width = int(win_width * 0.5)
            popup_height = 120
            popup_x = int((win_width - popup_width) * 0.5)
            popup_y = int((win_height - popup_height) * 0.5)

            def create_popup():
                if dpg.does_item_exist("read_error_popup"):
                    dpg.delete_item("read_error_popup")
                with dpg.window(
                    label="読み取りエラー",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="read_error_popup",
                ):
                    text_id = dpg.add_text(
                        message,
                        pos=(int(popup_width / 2 - 150), int(popup_height / 2 - 20)),
                        wrap=popup_width - 40,
                    )
                    dpg.bind_item_font(text_id, small_font)
                dpg.show_item("read_error_popup")
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 120,
                    lambda s, a: dpg.delete_item("read_error_popup"),
                )

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: create_popup()
            )

        # show_card_touch_popupでadmin_action時の処理を追加
        def show_card_touch_popup(mode, nfc_reader, monitor):
            logger.info(f"Show card touch popup: {mode}")
            if mode == "register":
                # まずカードIDを直接取得してみる
                try:
                    card_id = nfc_reader.read_card_id()
                    if card_id:
                        logger.info(f"Card ID read directly: {card_id}")
                        handle_card_touched_for_register(card_id)
                        return
                except Exception as e:
                    logger.info(f"No card present or read error: {e}")
                    # show_read_error_popup()
                    # return
            elif mode == "in":
                try:
                    card_id = nfc_reader.read_card_id()
                    if card_id:
                        logger.info(f"Card ID read directly: {card_id}")
                        handle_card_touched_for_in(card_id)
                        return
                except Exception as e:
                    logger.info(f"No card present or read error: {e}")
                    # show_read_error_popup()
                    # return
            elif mode == "out":
                try:
                    card_id = nfc_reader.read_card_id()
                    if card_id:
                        logger.info(f"Card ID read directly: {card_id}")
                        handle_card_touched_for_out(card_id)
                        return
                except Exception as e:
                    logger.info(f"No card present or read error: {e}")
                    # show_read_error_popup()
                    # return
            elif mode == "confirm":
                try:
                    card_id = nfc_reader.read_card_id()
                    if card_id:
                        logger.info(f"Card ID read directly: {card_id}")
                        handle_card_touched_for_confirm(card_id)
                        return
                except Exception as e:
                    logger.info(f"No card present or read error: {e}")
                    # show_read_error_popup()
                    # return
            if dpg.does_item_exist("card_touch_popup"):
                dpg.delete_item("card_touch_popup")
            # ポップアップウィンドウ作成
            popup_width = int(win_width * 0.7)
            popup_height = int(win_height * 0.5) + 40
            popup_x = int((win_width - popup_width) * 0.5)
            popup_y = int((win_height - popup_height) * 0.5)
            with dpg.window(
                label="カードタッチポップアップ",
                modal=True,
                no_title_bar=True,
                no_resize=True,
                no_collapse=True,
                width=popup_width,
                height=popup_height,
                pos=(popup_x, popup_y),
                tag="card_touch_popup",
            ):
                text_w = 340
                text_x = int((popup_width - text_w) / 2)
                text_y = 30
                dpg.add_text(
                    "タッチしてください",
                    pos=(text_x, text_y),
                    wrap=popup_width - 60,
                )
                btn_w = 90
                btn_h = 72
                btn_x = int((popup_width - btn_w) / 2)
                btn_y = popup_height - btn_h - 30  # 以前より上に配置
                dpg.add_button(
                    label="戻る",
                    width=btn_w,
                    height=btn_h,
                    pos=(btn_x, btn_y),
                    callback=lambda: close_card_touch_popup(),
                    tag="popup_back_btn",
                )

            # イベント駆動NFC監視
            observer = None

            def on_card_touched(event_type, card_id, error=None):
                if event_type == "insert":
                    if error:
                        logger.error(f"NFC event error: {error}")
                        # show_read_error_popup()
                    elif card_id:
                        logger.info(f"Card touched (event): {card_id}")
                        if mode == "register":
                            handle_card_touched_for_register(card_id)
                        elif mode == "in":
                            handle_card_touched_for_in(card_id)
                        elif mode == "out":
                            handle_card_touched_for_out(card_id)
                        elif mode == "admin_action":
                            handle_admin_action(card_id)
                        elif mode == "confirm":
                            handle_card_touched_for_confirm(card_id)
                    # 監視解除・ポップアップクローズはmode判定の外で共通実行
                    try:
                        monitor.deleteObserver(observer)
                    except ValueError:
                        pass
                    if dpg.does_item_exist("card_touch_popup"):
                        dpg.delete_item("card_touch_popup")
                # removeイベントはここでは何もしない
                return

            observer = CardEventObserver(on_card_touched)
            monitor.addObserver(observer)

            def close_after_timeout(sender, app_data):
                if dpg.does_item_exist("card_touch_popup"):
                    logger.info("Card touch popup was auto-closed due to timeout.")
                    dpg.delete_item("card_touch_popup")
                    try:
                        monitor.deleteObserver(observer)
                    except ValueError:
                        pass

            dpg.set_frame_callback(dpg.get_frame_count() + 600, close_after_timeout)

        def close_card_touch_popup():
            if dpg.does_item_exist("card_touch_popup"):
                dpg.delete_item("card_touch_popup")

        btn1 = dpg.add_button(
            label="入室",
            width=btn_width,
            height=btn_height,
            pos=(btns_start_x, btn_y),
            callback=lambda: show_card_touch_popup("in", nfc_reader, monitor),
        )
        dpg.bind_item_theme(btn1, theme_in)
        # 退室ボタン（右・赤）
        with dpg.theme() as theme_out:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (220, 50, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (240, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180, 30, 30, 255))
        btn2 = dpg.add_button(
            label="退室",
            width=btn_width,
            height=btn_height,
            pos=(btns_start_x + btn_width + margin - 10, btn_y),
            callback=lambda: show_card_touch_popup("out", nfc_reader, monitor),
        )
        dpg.bind_item_theme(btn2, theme_out)
        # 新規登録・CSV出力ボタンも同様に修正
        dpg.set_item_callback(
            "register_btn",
            lambda: show_card_touch_popup("register", nfc_reader, monitor),
        )
        dpg.set_item_callback(
            "csv_btn", lambda: show_card_touch_popup("csv", nfc_reader, monitor)
        )

        # 入力ボタン（管理者認証付き）
        def handle_input_btn():
            already_handled = {"admin": False}

            def after_admin():
                # 認証後の処理（例: ポップアップ表示や管理画面遷移など）
                popup_width = int(win_width * 0.5)
                popup_height = 100
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="管理者操作",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="input_admin_popup",
                ):
                    dpg.add_text(
                        "管理者操作画面",
                        pos=(int(popup_width / 2 - 80), int(popup_height / 2 - 12)),
                    )
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 120,
                    lambda s, a: dpg.delete_item("input_admin_popup"),
                )

            # カードタッチで管理者認証
            def on_card(event_type, card_id, error=None):
                if already_handled["admin"]:
                    return
                if event_type == "insert":
                    if error:
                        logger.error(f"NFC event error: {error}")
                    elif card_id:
                        logger.info(f"Card touched for admin input: {card_id}")
                        already_handled["admin"] = True
                        sudo_popup(card_id, after_admin)
                    try:
                        monitor.deleteObserver(observer)
                    except Exception:
                        pass
                    if dpg.does_item_exist("input_card_popup"):
                        dpg.delete_item("input_card_popup")
                # removeイベントはここでは何もしない

            observer = CardEventObserver(on_card)
            monitor.addObserver(observer)

            # ポップアップでカードタッチを促す
            popup_width = int(win_width * 0.7)
            popup_height = int(win_height * 0.5) + 40
            popup_x = int((win_width - popup_width) * 0.5)
            popup_y = int((win_height - popup_height) * 0.5)
            with dpg.window(
                label="管理者カード認証",
                modal=True,
                no_title_bar=True,
                no_resize=True,
                no_collapse=True,
                width=popup_width,
                height=popup_height,
                pos=(popup_x, popup_y),
                tag="input_card_popup",
            ):
                text_w = 340
                text_x = int((popup_width - text_w) / 2)
                text_y = 30
                dpg.add_text(
                    "管理者カードを\nタッチしてください",
                    pos=(text_x, text_y),
                    wrap=popup_width - 60,
                )
                btn_w = 90
                btn_h = 72
                btn_x = int((popup_width - btn_w) / 2)
                btn_y = popup_height - btn_h - 30  # 以前より上に配置
                dpg.add_button(
                    label="戻る",
                    width=btn_w,
                    height=btn_h,
                    pos=(btn_x, btn_y),
                    callback=lambda: dpg.delete_item("input_card_popup"),
                    tag="input_popup_back_btn",
                )
            observer = CardEventObserver(on_card)
            monitor.addObserver(observer)

            def close_after_timeout(sender, app_data):
                if dpg.does_item_exist("input_card_popup"):
                    logger.info("Input card popup was auto-closed due to timeout.")
                    dpg.delete_item("input_card_popup")
                    try:
                        monitor.deleteObserver(observer)
                    except Exception:
                        pass

            dpg.set_frame_callback(dpg.get_frame_count() + 600, close_after_timeout)

        dpg.set_item_callback("input_btn", handle_input_btn)

        def on_confirm_btn():
            # 普通のタッチのpopupを表示し、カードID取得後にhandle_card_touched_for_confirmを呼ぶ
            show_card_touch_popup("confirm", nfc_reader, monitor)

        def handle_card_touched_for_confirm(card_id):
            # 今年度の4/1～9/30, 10/1～3/31
            today = datetime.now().date()
            year = today.year
            # 年度判定：1-3月なら前年度、4月以降なら今年度
            fiscal_year = year if today.month >= 4 else year - 1
            # 4/1～9/18
            start1 = datetime(fiscal_year, 4, 1)
            end1 = datetime(fiscal_year, 9, 18, 23, 59, 59)
            # 9/19～翌年3/31
            start2 = datetime(fiscal_year, 9, 19)
            end2 = datetime(fiscal_year + 1, 3, 31, 23, 59, 59)
            t1_9_17, t1_other = calc_total_time_split(card_id, start1, end1)
            t2_9_17, t2_other = calc_total_time_split(card_id, start2, end2)
            # 名前・オフセット取得
            user = db.get_user(card_id)
            name = user.name if user and getattr(user, "name", None) else "Unknown"
            offset = (
                user.offset if user and hasattr(user, "offset") and user.offset else 0.0
            )
            # 2025年前半(4-9月)のみオフセット加算
            if year == 2025:
                t1_9_17 += offset * 3600
                t1_other += 0  # 必要なら他にも加算

            # ポップアップで表示（UIスレッドで実行）
            def show_confirm_popup():
                # msg = (
                #     f"4-9月  9-17時: {t1_9_17 / 3600:.1f} Hour  その他: {t1_other / 3600:.1f} Hour\n"
                #     f"10-3月 9-17時: {t2_9_17 / 3600:.1f} Hour  その他: {t2_other / 3600:.1f} Hour"
                # )
                popup_width = int(win_width * 0.9)
                popup_height = int(win_height * 0.8)
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                if dpg.does_item_exist("confirm_result_popup"):
                    dpg.delete_item("confirm_result_popup")
                with dpg.window(
                    label="確認結果",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="confirm_result_popup",
                ):
                    dpg.add_text(
                        f"名前: {name}", wrap=popup_width - 40, tag="confirm_name_text"
                    )
                    # テーブル風表示
                    with dpg.table(
                        header_row=True,
                        borders_innerH=True,
                        borders_outerH=True,
                        borders_innerV=True,
                        borders_outerV=True,
                        pos=(0, 120),  # テーブル全体を下方向に120pxオフセット
                    ):
                        col1 = dpg.add_table_column(label="期間")
                        col2 = dpg.add_table_column(label="9-17時 (H)")
                        col3 = dpg.add_table_column(label="その他 (H)")
                        dpg.bind_item_font(col1, small_font)
                        dpg.bind_item_font(col2, small_font)
                        dpg.bind_item_font(col3, small_font)
                        with dpg.table_row():
                            dpg.add_text("4-9月")
                            dpg.add_text(f"{t1_9_17 / 3600:.1f}")
                            dpg.add_text(f"{t1_other / 3600:.1f}")
                        with dpg.table_row():
                            dpg.add_text("10-3月")
                            dpg.add_text(f"{t2_9_17 / 3600:.1f}")
                            dpg.add_text(f"{t2_other / 3600:.1f}")
                    dpg.bind_item_font("confirm_name_text", small_font)
                    # 閉じるボタン追加
                    btn_w = 144
                    btn_h = 72
                    btn_x = int((popup_width - btn_w) / 2)
                    btn_y = popup_height - btn_h - 10
                    dpg.add_button(
                        label="閉じる",
                        width=btn_w,
                        height=btn_h,
                        pos=(btn_x, btn_y),
                        callback=lambda: dpg.delete_item("confirm_result_popup"),
                        tag="confirm_close_btn",
                    )
                dpg.set_frame_callback(
                    dpg.get_frame_count() + 480,
                    lambda s, a: dpg.delete_item("confirm_result_popup"),
                )

            dpg.set_frame_callback(
                dpg.get_frame_count() + 1, lambda s, a: show_confirm_popup()
            )

        dpg.set_item_callback("confirm_btn", on_confirm_btn)

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
