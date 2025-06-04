from pathlib import Path

import dearpygui.dearpygui as dpg
from smartcard.CardMonitoring import CardMonitor

from src.attendance_reader import CardInsertObserver, NFCReader
from src.db import AttendanceDB
from src.log_config import logger


def main():
    nfc_reader = NFCReader()
    # AttendanceDBインスタンスをmain関数の先頭で1つだけ生成
    db = AttendanceDB()

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
        with dpg.font(str(font_path), 22, default_font=True) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
        with dpg.font(str(font_path), 14) as small_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)

    dpg.bind_font(default_font)

    dpg.create_viewport(
        title="Attendance Management System",
        width=400,
        height=200,
        x_pos=100,
        y_pos=100,
        vsync=True,
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # ウィンドウサイズ取得
    win_width = dpg.get_viewport_client_width()
    win_height = dpg.get_viewport_client_height()
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
    ):
        # 新規登録・CSV出力（右上・幅広く、位置はそのまま）
        btn_w = int(win_width * 0.28)
        top_btn_y = 10
        # 新規登録ボタンのIDを取得
        register_btn = dpg.add_button(
            label="新規登録", width=btn_w, pos=(win_width - btn_w * 2 - 20, top_btn_y)
        )
        # CSV出力ボタンのIDを取得
        csv_btn = dpg.add_button(
            label="CSV出力", width=btn_w, pos=(win_width - btn_w - 10, top_btn_y)
        )
        # 出勤・退勤ボタンを横方向中央揃え・下方向に少しだけ間隔を広げて配置
        btns_total_width = btn_width * 2 + margin
        btns_start_x = int((win_width - btns_total_width) / 2)
        # ボタンを下方向に「今の感覚の1/3」だけずらす
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
            if not name.strip():
                logger.info("名前が空欄のため登録しません")
                dpg.delete_item("register_name_popup")
                return
            # upsert_userで登録・更新を一括処理
            db.upsert_user(card_id, name, is_admin=False)
            logger.info(f"Register user: card_id={card_id}, name={name}")
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
                        pos=(int(popup_width / 2 - 60), int(popup_height / 2 - 12)),
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
            logger.info(f"Card touched for registration: {card_id}, User: {user_name}")

            def show_popup():
                if dpg.does_item_exist("register_name_popup"):
                    dpg.delete_item("register_name_popup")
                popup_width = int(win_width * 0.7)
                popup_height = 180
                popup_x = int((win_width - popup_width) * 0.5)
                popup_y = int((win_height - popup_height) * 0.5)
                with dpg.window(
                    label="名前登録",
                    modal=True,
                    no_title_bar=True,
                    no_resize=True,
                    no_collapse=True,
                    width=popup_width,
                    height=popup_height,
                    pos=(popup_x, popup_y),
                    tag="register_name_popup",
                ):
                    with dpg.group():
                        dpg.add_text(
                            f"Card ID: {card_id}",
                            pos=(30, 20),
                            tag="register_cardid_text",
                        )
                        dpg.add_text(
                            "名前を入力してください",
                            pos=(30, 50),
                            tag="register_guide_text",
                        )
                    dpg.bind_item_font("register_cardid_text", small_font)
                    dpg.bind_item_font("register_guide_text", small_font)
                    logger.info("add_input_text called")
                    dpg.add_input_text(
                        label=" ",  # ラベル非表示
                        default_value=user_name or "",
                        width=popup_width - 60,
                        pos=(30, 80),
                        tag="register_name_input",
                    )
                    dpg.add_button(
                        label="登録",
                        width=90,
                        height=36,
                        pos=(popup_width - 120, popup_height - 50),
                        callback=lambda: on_register_name(card_id),
                    )
                    dpg.add_button(
                        label="キャンセル",
                        width=90,
                        height=36,
                        pos=(30, popup_height - 50),
                        callback=lambda: dpg.delete_item("register_name_popup"),
                    )
                dpg.show_item("register_name_popup")

            dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda s, a: show_popup())

        def show_card_touch_popup(mode, nfc_reader):
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
                text_w = 220
                text_x = int((popup_width - text_w) / 2)
                text_y = 30
                dpg.add_text(
                    "タッチしてください",
                    pos=(text_x, text_y),
                    wrap=popup_width - 60,
                )
                btn_w = 90
                btn_h = 36
                btn_x = int((popup_width - btn_w) / 2)
                btn_y = popup_height - btn_h - 10
                dpg.add_button(
                    label="戻る",
                    width=btn_w,
                    height=btn_h,
                    pos=(btn_x, btn_y),
                    callback=lambda: close_card_touch_popup(),
                    tag="popup_back_btn",
                )

            # イベント駆動NFC監視
            card_monitor = CardMonitor()
            observer = None

            def on_card_touched(card_id, error=None):
                if error:
                    logger.error(f"NFC event error: {error}")
                elif card_id:
                    logger.info(f"Card touched (event): {card_id}")
                    if mode == "register":
                        handle_card_touched_for_register(card_id)
                # 監視解除・ポップアップクローズはmode判定の外で共通実行
                try:
                    card_monitor.deleteObserver(observer)
                except ValueError:
                    pass
                if dpg.does_item_exist("card_touch_popup"):
                    dpg.delete_item("card_touch_popup")
                return

            observer = CardInsertObserver(on_card_touched)
            card_monitor.addObserver(observer)

            def close_after_timeout(sender, app_data):
                if dpg.does_item_exist("card_touch_popup"):
                    logger.info("Card touch popup was auto-closed due to timeout.")
                    dpg.delete_item("card_touch_popup")
                    try:
                        card_monitor.deleteObserver(observer)
                    except ValueError:
                        pass

            dpg.set_frame_callback(dpg.get_frame_count() + 600, close_after_timeout)

        def close_card_touch_popup():
            if dpg.does_item_exist("card_touch_popup"):
                dpg.delete_item("card_touch_popup")

        btn1 = dpg.add_button(
            label="出勤",
            width=btn_width,
            height=btn_height,
            pos=(btns_start_x, btn_y),
            callback=lambda: show_card_touch_popup("in", nfc_reader),
        )
        dpg.bind_item_theme(btn1, theme_in)
        # 退勤ボタン（右・赤）
        with dpg.theme() as theme_out:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (220, 50, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (240, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180, 30, 30, 255))
        btn2 = dpg.add_button(
            label="退勤",
            width=btn_width,
            height=btn_height,
            pos=(btns_start_x + btn_width + margin, btn_y),
            callback=lambda: show_card_touch_popup("out", nfc_reader),
        )
        dpg.bind_item_theme(btn2, theme_out)
        # 新規登録・CSV出力ボタンも同様に修正
        dpg.set_item_callback(
            register_btn, lambda: show_card_touch_popup("register", nfc_reader)
        )
        dpg.set_item_callback(csv_btn, lambda: show_card_touch_popup("csv", nfc_reader))

    # set_item_callbackによるコールバック設定は不要なので削除
    # dpg.set_item_callback(btn1, lambda: show_card_touch_popup())
    # dpg.set_item_callback(btn2, lambda: show_card_touch_popup())
    # dpg.set_item_callback(register_btn, lambda: show_card_touch_popup())
    # dpg.set_item_callback(csv_btn, lambda: show_card_touch_popup())
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
