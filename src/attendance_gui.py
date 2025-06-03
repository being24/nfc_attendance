import dearpygui.dearpygui as dpg
from pathlib import Path


def main():
    dpg.create_context()
    # フォントの追加（グローバル指定、フォントヒント付き）
    font_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "BIZ_UDGothic"
        / "BIZUDGothic-Regular.ttf"
    )
    with dpg.font_registry():
        with dpg.font(str(font_path), 22, default_font=True) as default_font:
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
        # 出勤ボタン（左・緑）
        with dpg.theme() as theme_in:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 180, 75, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 200, 95, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (40, 140, 55, 255))
        btn1 = dpg.add_button(
            label="出勤",
            width=btn_width,
            height=btn_height,
            pos=(margin, int(win_height * 0.2)),
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
            pos=(win_width - btn_width - margin, int(win_height * 0.2)),
        )
        dpg.bind_item_theme(btn2, theme_out)
        # 新規登録・CSV出力（右上・幅広く）
        btn_w = int(win_width * 0.28)  # 横幅をさらに大きく
        dpg.add_button(
            label="新規登録", width=btn_w, pos=(win_width - btn_w * 2 - 20, 10)
        )
        dpg.add_button(label="CSV出力", width=btn_w, pos=(win_width - btn_w - 10, 10))

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
