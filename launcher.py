from __future__ import annotations

import subprocess
import sys
import tkinter as tk
import traceback
import webbrowser
from pathlib import Path
from tkinter import messagebox

from focusaway.config import AppConfig, load_config, save_config


LOG_PATH = Path(__file__).resolve().parent / "focusaway-launcher.log"
LANGUAGE_OPTIONS = {"한국어": "ko", "English": "en"}
LANGUAGE_LABELS = {value: label for label, value in LANGUAGE_OPTIONS.items()}
TEXT = {
    "ko": {
        "subtitle": "로컬 OpenAI 호환 백엔드용 미들웨어 런처",
        "status_ready": "준비됨",
        "save": "저장",
        "start": "서버 시작",
        "stop": "서버 중지",
        "open_panel": "웹 패널 열기",
        "language": "언어:",
        "saved": "설정을 저장했습니다: {name}",
        "saved_dialog": "설정을 저장했습니다.\n{path}",
        "already_running": "이미 실행 중입니다.",
        "port_error": "Port 값은 숫자여야 합니다.",
        "running": "실행 중: {url}",
        "stopped": "중지됨",
        "startup_error": "런처 시작 중 오류가 발생했습니다.\nfocusaway-launcher.log 파일을 확인해 주세요.",
    },
    "en": {
        "subtitle": "Middleware launcher for local OpenAI-compatible backends",
        "status_ready": "Ready",
        "save": "Save",
        "start": "Start Server",
        "stop": "Stop Server",
        "open_panel": "Open Web Panel",
        "language": "Language:",
        "saved": "Settings saved: {name}",
        "saved_dialog": "Settings saved.\n{path}",
        "already_running": "Already running.",
        "port_error": "Port must be a number.",
        "running": "Running: {url}",
        "stopped": "Stopped",
        "startup_error": "An error occurred while starting the launcher.\nPlease check focusaway-launcher.log.",
    },
}


def write_log(message: str) -> None:
    LOG_PATH.write_text(message + "\n", encoding="utf-8")


class Launcher:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.root = tk.Tk()
        self.root.title("FocusAway Launcher")
        self.root.geometry("860x600")
        self.root.minsize(760, 560)
        self.root.configure(bg="#f5f5f7")

        self.config = load_config()
        self.host_var = tk.StringVar(value=self.config.host)
        self.port_var = tk.StringVar(value=str(self.config.port))
        self.upstream_var = tk.StringVar(value=self.config.upstream_base_url)
        self.upstream_prefix_var = tk.StringVar(value=self.config.upstream_api_prefix)
        self.upstream_models_var = tk.StringVar(value=self.config.upstream_models_path)
        self.api_key_var = tk.StringVar(value=self.config.upstream_api_key)
        self.auth_mode_var = tk.StringVar(value=self.config.upstream_auth_mode)
        self.auth_header_var = tk.StringVar(value=self.config.upstream_auth_header)
        self.auth_scheme_var = tk.StringVar(value=self.config.upstream_auth_scheme)
        self.language_var = tk.StringVar(value=LANGUAGE_LABELS.get(self.config.launcher_language, "English"))
        self.status_var = tk.StringVar(value=self.t("status_ready"))
        self.translated_widgets: dict[str, tk.Widget] = {}

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#f5f5f7", padx=18, pady=18)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#f5f5f7")
        header.pack(fill="x", pady=(0, 18))

        title_row = tk.Frame(header, bg="#f5f5f7")
        title_row.pack(fill="x")

        tk.Label(
            title_row,
            text="FocusAway",
            font=("Helvetica", 24, "bold"),
            bg="#f5f5f7",
            fg="#18181b",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        language_box = tk.Frame(title_row, bg="#f5f5f7")
        language_box.pack(side="right")
        self.translated_widgets["language_label"] = tk.Label(
            language_box,
            text=self.t("language"),
            font=("Helvetica", 10),
            bg="#f5f5f7",
            fg="#4b5563",
        )
        self.translated_widgets["language_label"].pack(side="left", padx=(0, 6))
        menu = tk.OptionMenu(language_box, self.language_var, *LANGUAGE_OPTIONS.keys(), command=self.change_language)
        menu.configure(bg="#ffffff", fg="#18181b", highlightthickness=0, bd=1, relief="solid", activebackground="#f4f4f5")
        menu.pack(side="left")

        self.translated_widgets["subtitle"] = tk.Label(
            header,
            text=self.t("subtitle"),
            font=("Helvetica", 12),
            bg="#f5f5f7",
            fg="#6b7280",
            anchor="w",
        )
        self.translated_widgets["subtitle"].pack(fill="x", pady=(6, 0))

        form = tk.Frame(shell, bg="#ffffff", bd=1, relief="solid", padx=16, pady=16)
        form.pack(fill="both", expand=True)

        grid = tk.Frame(form, bg="#ffffff")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        self.add_labeled_entry(grid, "Host", self.host_var, row=0, column=0)
        self.add_labeled_entry(grid, "Port", self.port_var, row=0, column=1)
        self.add_labeled_entry(grid, "Upstream Base URL", self.upstream_var, row=1, column=0, columnspan=2)
        self.add_labeled_entry(grid, "Upstream API Prefix", self.upstream_prefix_var, row=2, column=0)
        self.add_labeled_entry(grid, "Upstream Models Path", self.upstream_models_var, row=2, column=1)
        self.add_labeled_entry(grid, "Upstream Auth Mode", self.auth_mode_var, row=3, column=0)
        self.add_labeled_entry(grid, "Upstream Auth Header", self.auth_header_var, row=3, column=1)
        self.add_labeled_entry(grid, "Upstream Auth Scheme", self.auth_scheme_var, row=4, column=0)
        self.add_labeled_entry(grid, "Upstream API Key", self.api_key_var, row=4, column=1, show="*")

        tk.Label(
            form,
            textvariable=self.status_var,
            bg="#ffffff",
            fg="#3f3f46",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(8, 12))

        actions = tk.Frame(form, bg="#ffffff")
        actions.pack(fill="x")

        self.translated_widgets["save_button"] = self.make_button(actions, self.t("save"), self.save)
        self.translated_widgets["save_button"].pack(side="left")
        self.translated_widgets["start_button"] = self.make_button(actions, self.t("start"), self.start)
        self.translated_widgets["start_button"].pack(side="left", padx=8)
        self.translated_widgets["stop_button"] = self.make_button(actions, self.t("stop"), self.stop)
        self.translated_widgets["stop_button"].pack(side="left")
        self.translated_widgets["open_panel_button"] = self.make_button(actions, self.t("open_panel"), self.open_panel)
        self.translated_widgets["open_panel_button"].pack(side="right")

    def current_language(self) -> str:
        return LANGUAGE_OPTIONS.get(self.language_var.get(), "en")

    def t(self, key: str, **values) -> str:
        return TEXT.get(getattr(self, "config", AppConfig()).launcher_language or "en", TEXT["en"])[key].format(**values)

    def change_language(self, _choice: str | None = None) -> None:
        self.config.launcher_language = self.current_language()
        save_config(self.current_config())
        self.translated_widgets["language_label"].configure(text=self.t("language"))
        self.translated_widgets["subtitle"].configure(text=self.t("subtitle"))
        self.set_button_text(self.translated_widgets["save_button"], self.t("save"))
        self.set_button_text(self.translated_widgets["start_button"], self.t("start"))
        self.set_button_text(self.translated_widgets["stop_button"], self.t("stop"))
        self.set_button_text(self.translated_widgets["open_panel_button"], self.t("open_panel"))
        self.status_var.set(self.t("status_ready"))

    def set_button_text(self, container: tk.Widget, text: str) -> None:
        for child in container.winfo_children():
            if isinstance(child, tk.Label):
                child.configure(text=text)

    def add_labeled_entry(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
        columnspan: int = 1,
        show: str | None = None,
    ) -> None:
        field = tk.Frame(parent, bg="#ffffff")
        field.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=6, pady=6)
        tk.Label(field, text=label, bg="#ffffff", fg="#18181b", anchor="w").pack(fill="x", pady=(0, 4))
        entry = tk.Entry(
            field,
            textvariable=variable,
            show=show or "",
            bg="white",
            fg="#18181b",
            relief="solid",
            highlightthickness=0,
            bd=1,
        )
        entry.pack(fill="x", ipady=6)

    def make_button(self, parent: tk.Widget, text: str, command) -> tk.Frame:
        container = tk.Frame(parent, bg="#27272a", bd=0, highlightthickness=0, cursor="hand2")
        label = tk.Label(
            container,
            text=text,
            bg="#27272a",
            fg="#ffffff",
            font=("Helvetica", 12, "bold"),
            padx=14,
            pady=10,
            cursor="hand2",
        )
        label.pack()

        def on_enter(_event) -> None:
            container.configure(bg="#18181b")
            label.configure(bg="#18181b", fg="#ffffff")

        def on_leave(_event) -> None:
            container.configure(bg="#27272a")
            label.configure(bg="#27272a", fg="#ffffff")

        def on_click(_event) -> None:
            command()

        for widget in (container, label):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

        return container

    def current_config(self) -> AppConfig:
        return AppConfig(
            host=self.host_var.get().strip() or "127.0.0.1",
            port=int(self.port_var.get().strip() or "8787"),
            upstream_base_url=self.upstream_var.get().strip(),
            upstream_api_prefix=self.upstream_prefix_var.get().strip() or "/v1",
            upstream_models_path=self.upstream_models_var.get().strip() or "/v1/models",
            upstream_api_key=self.api_key_var.get().strip(),
            upstream_auth_mode=self.auth_mode_var.get().strip() or "bearer",
            upstream_auth_header=self.auth_header_var.get().strip() or "Authorization",
            upstream_auth_scheme=self.auth_scheme_var.get().strip() or "Bearer",
            timezone=self.config.timezone,
            database_path=self.config.database_path,
            max_request_bytes=self.config.max_request_bytes,
            cors_allowed_origins=self.config.cors_allowed_origins,
            upstream_extra_headers=self.config.upstream_extra_headers,
            upstream_timeout_seconds=self.config.upstream_timeout_seconds,
            session_hours=self.config.session_hours,
            signup_cooldown_seconds=self.config.signup_cooldown_seconds,
            carrier_signup_cooldown_seconds=self.config.carrier_signup_cooldown_seconds,
            carrier_ip_ranges=self.config.carrier_ip_ranges,
            trusted_proxy_cidrs=self.config.trusted_proxy_cidrs,
            app_name=self.config.app_name,
            operator_name=self.config.operator_name,
            contact_email=self.config.contact_email,
            contact_address=self.config.contact_address,
            launcher_language=self.current_language(),
        )

    def save(self) -> None:
        self.config = self.current_config()
        path = save_config(self.config)
        self.status_var.set(self.t("saved", name=path.name))
        messagebox.showinfo("FocusAway", self.t("saved_dialog", path=Path(path).resolve()))

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            self.status_var.set(self.t("already_running"))
            return

        try:
            self.config = self.current_config()
        except ValueError:
            messagebox.showerror("FocusAway", self.t("port_error"))
            return

        save_config(self.config)
        app_path = Path(__file__).resolve().parent / "app.py"
        stdout_path = Path(__file__).resolve().parent / "focusaway-server.log"
        handle = stdout_path.open("a", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, str(app_path)],
            cwd=Path(__file__).resolve().parent,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        self.status_var.set(self.t("running", url=f"http://{self.config.host}:{self.config.port}"))

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            self.status_var.set(self.t("stopped"))
            return
        self.process.terminate()
        self.process.wait(timeout=5)
        self.status_var.set(self.t("stopped"))

    def open_panel(self) -> None:
        try:
            config = self.current_config()
        except ValueError:
            messagebox.showerror("FocusAway", self.t("port_error"))
            return
        webbrowser.open(f"http://{config.host}:{config.port}")

    def on_close(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    try:
        Launcher().run()
    except Exception:
        trace = traceback.format_exc()
        write_log(trace)
        print(trace)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "FocusAway Launcher Error",
                TEXT["en"]["startup_error"],
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
