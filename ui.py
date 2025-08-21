import tkinter as tk
from tkinter import ttk
import jsonHandler as jh
from PIL import Image, ImageTk, ImageDraw
from aimbot import Aimbot
from multiprocessing import Process, Event


global bot_stop_event, bot_process, settings_img_label

root = tk.Tk()

settings = {}
configs = {}
variables = {}
classes_headers = ["CT_Body", "CT_Head", "T_Body", "T_Head"]

setting_font = ("Verdana", 9)

settings_img = Image.open("docs/settings_example.png")


def crop_settings_img(size):
    width, height = settings_img.size

    left = (width - size) / 2
    top = (height - size) / 2
    right = (width + size) / 2
    bottom = (height + size) / 2

    return settings_img.crop((left, top, right, bottom))


def draw_circle(img, radius, color="red", thickness=3):
    w, h = img.size
    cx, cy = w // 2, h // 2
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)

    draw = ImageDraw.Draw(img)
    draw.ellipse(bbox, outline=color, width=thickness)
    return img


def get_settings_img(config):
    _, height = settings_img.size
    crop_size = int(height * settings["aimbot_box_size_percentage"])
    img = crop_settings_img(crop_size)

    radius = config["aimbot_fov_percentage"]/2 * crop_size
    img = draw_circle(img, radius)

    dead_zone_radius = config["dead_zone_radius"]
    img = draw_circle(img, dead_zone_radius, color="black")

    return img


def autosave(*args):
    # sync variables into settings/configs
    for (section, key), var in variables.items():
        if isinstance(var, list):  # list of IntVar for checkbuttons
            configs[section][key] = [
                i for i, v in enumerate(var) if v.get() == 1
            ]
        else:
            if section == "Settings":
                settings[key] = var.get()
            else:
                configs[section][key] = var.get()

    jh.saveJSON("settings", settings)
    jh.saveJSON("configs", configs)


def bind_autosave(var):
    var.trace_add("write", autosave)


def add_scale_control(frame, title, key, value, var_type, from_, to, resolution):
    var = var_type(value=value)
    bind_autosave(var)
    variables[(title, key)] = var

    def on_scale_change(val):
        global settings_img_label

        configs[title][key] = var.get()

        img = get_settings_img(configs[title])
        tk_img = ImageTk.PhotoImage(img.resize((400, 400), Image.LANCZOS))
        settings_img_label.configure(image=tk_img)
        settings_img_label.image = tk_img

    inner = ttk.Frame(frame)
    inner.pack(fill="x", padx=5)

    scale = tk.Scale(
        inner,
        from_=from_,
        to=to,
        orient="horizontal",
        resolution=resolution,
        variable=var,
        showvalue=False,
        command=on_scale_change
    )
    scale.grid(row=0, column=0, sticky="ew")

    value_label = ttk.Label(inner, textvariable=var, width=5)
    value_label.grid(row=0, column=1, padx=(5, 0))

    inner.columnconfigure(0, weight=1)


def on_btn_click(event, var, lbl):
    var.set(not var.get())
    lbl.config(background="lightblue" if var.get() else "white")


def create_tile_button(parent, text, var, on_click):
    """Create a styled label acting as a toggle button."""
    lbl = tk.Label(
        parent,
        text=text,
        borderwidth=2,
        relief="groove",
        width=15,
        height=4,
        anchor="center",
        justify="center",
        wraplength=150,
        background="lightblue" if var.get() else "white"
    )
    lbl.pack(side="left", padx=5, pady=5)
    lbl.bind("<Button-1>", lambda e, v=var, l=lbl: on_click(e, v, l))
    return lbl


def build_config_frame(parent, title):
    global configs, settings_img_label

    parent["text"] = f"Current Config: {title}".upper()
    config = configs[title]

    settings_frame = ttk.LabelFrame(parent, relief="flat", borderwidth=0)
    settings_frame.pack(side="left", fill="y", padx=5, pady=5)

    image_frame = ttk.Frame(parent, width=400, height=400, relief="solid")
    image_frame.pack_propagate(False)  # prevent shrinking to fit content
    image_frame.pack(side="left", padx=(10,5), pady=5)

    img = get_settings_img(config)
    tk_img = ImageTk.PhotoImage(img.resize((400, 400), Image.LANCZOS))

    settings_img_label = ttk.Label(image_frame, image=tk_img)
    settings_img_label.image = tk_img
    settings_img_label.pack(expand=True)

    for key, value in config.items():
        if key != "trigger_bot":
            field_text = key.replace("_", " ").title()
            ttk.Label(settings_frame, text=field_text).pack(anchor="w", pady=(4, 0))

        if key == "aimbot_fov_percentage":
            add_scale_control(settings_frame, title, key, value, tk.DoubleVar, 0.01, 1.0, 0.01)

        elif key == "dead_zone_radius":
            add_scale_control(settings_frame, title, key, value, tk.IntVar, 1, 100, 1)

        elif key == "classes" and isinstance(value, (list, tuple)):
            btn_frame = ttk.Frame(settings_frame)
            btn_frame.pack(anchor="w", pady=2)

            vars_list = []
            for i in range(4):
                var = tk.BooleanVar(value=i in value)
                bind_autosave(var)
                create_tile_button(btn_frame, classes_headers[i], var, on_btn_click)
                vars_list.append(var)

            variables[(title, key)] = vars_list

            sep = ttk.Separator(btn_frame, orient="vertical")
            sep.pack(side="left", fill="y", padx=8, pady=10)

            trig_var = tk.BooleanVar(value=configs[title].get("trigger_bot", False))
            bind_autosave(trig_var)
            create_tile_button(btn_frame, "Trigger Bot", trig_var, on_btn_click)
            variables[(title, "trigger_bot")] = trig_var

            variables[(title, "trigger_bot")] = trig_var

    start_stop_frame = tk.Frame(settings_frame)
    start_stop_frame.pack(expand=True, fill="both")

    def toggle_start_stop():
        current_text = start_stop_btn["text"]
        if current_text == "START":
            start_stop_btn.config(text="STOP", bg="#f5c6cb")
            start_AAA()
        else:
            start_stop_btn.config(text="START", bg="#c3e6cb")
            stop_AAA()

    start_stop_btn = tk.Button(
        start_stop_frame,
        text="START",
        bg="#d4edda",
        relief="solid",
        borderwidth=1,
        command=toggle_start_stop
    )
    start_stop_btn.pack(expand=True, anchor="center", ipadx=20, ipady=10, pady=(0, 5))



def on_config_change(_, parent, title_var):
    new_title = title_var.get()
    for widget in parent.winfo_children():
        widget.destroy()
    build_config_frame(parent, new_title)
    autosave()


def build_frame(parent):
    global settings_img_label
    title = "Settings"
    style = ttk.Style()
    style.configure("Custom.TLabelframe.Label", font=("Arial", 11, "bold"))

    frame = ttk.LabelFrame(parent, text=title.upper(), style="Custom.TLabelframe", padding=10)
    frame.pack(fill="x", padx=10, pady=5)
    frame.columnconfigure(0, weight=1)

    config_frame = ttk.LabelFrame(parent, text="", style="Custom.TLabelframe", padding=10)
    config_frame.pack(fill="x", padx=5, pady=5)

    row = 0
    for key, value in settings.items():
        field_text = key.replace("_", " ").title()

        if key in ("sensitivity", "aimbot_box_size_percentage", "confidence"):
            var = tk.DoubleVar(value=value)
            bind_autosave(var)
            variables[(title, key)] = var

            if key == "aimbot_box_size_percentage":
                def on_box_size_change(*_):
                    config_name = settings["current_config"]
                    tmp_var = variables[(title, "aimbot_box_size_percentage")]
                    settings["aimbot_box_size_percentage"] = tmp_var.get()

                    img = get_settings_img(configs[config_name])
                    tk_img = ImageTk.PhotoImage(img.resize((400, 400), Image.LANCZOS))
                    settings_img_label.configure(image=tk_img)
                    settings_img_label.image = tk_img

                var.trace_add("write", on_box_size_change)

            ttk.Label(frame, text=field_text, font=setting_font).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 20))
            ttk.Entry(frame, textvariable=var, width=18, justify="right").grid(row=row, column=1, sticky="w", pady=5)

        elif key == "current_config":
            ttk.Label(frame, text=field_text, font=setting_font).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 20))

            choices = list(configs.keys())
            var = tk.StringVar(value=value if value in choices else choices[0])
            bind_autosave(var)
            variables[(title, key)] = var

            combo = ttk.Combobox(
                frame,
                textvariable=var,
                values=choices,
                state="readonly",
                width=15,
                justify="right"
            )
            combo.grid(row=row, column=1, sticky="w", pady=2)
            combo.bind("<<ComboboxSelected>>", lambda e: on_config_change(e, config_frame, var))

            build_config_frame(config_frame, value)

        row += 1


def run_bot(stop_event, settings, config):
    bot = Aimbot("model.pt", "COM5", settings, config, debug=False)
    while not stop_event.is_set():
        bot.run()


def start_AAA():
    global bot_stop_event, bot_process

    bot_stop_event = Event()
    bot_process = Process(target=run_bot, args=(bot_stop_event, settings, configs[settings["current_config"]]))
    bot_process.start()


def stop_AAA():
    try:
        if bot_stop_event and not bot_stop_event.is_set():
            bot_stop_event.set()
        if bot_process.is_alive():
            bot_process.join(timeout=2)
            if bot_process.is_alive():
                bot_process.terminate()
    except:
        pass


if __name__ == '__main__':
    settings = jh.loadJSON("settings")
    configs = jh.loadJSON("configs")

    root.title("AI Aim Assistant")

    # lock size to the minimal size to display everything
    root.update_idletasks()
    root.resizable(False, False)

    build_frame(root)
    
    try:
        root.mainloop()
    finally:
        stop_AAA()
