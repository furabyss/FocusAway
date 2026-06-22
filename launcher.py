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
        self.status_var = tk.StringVar(value="준비됨")

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#f5f5f7", padx=18, pady=18)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg="#f5f5f7")
        header.pack(fill="x", pady=(0, 18))

        tk.Label(
            header,
            text="FocusAway",
            font=("Helvetica", 24, "bold"),
            bg="#f5f5f7",
            fg="#18181b",
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            header,
            text="로컬 OpenAI 호환 백엔드용 미들웨어 런처",
            font=("Helvetica", 12),
            bg="#f5f5f7",
            fg="#6b7280",
            anchor="w",
        ).pack(fill="x", pady=(6, 0))

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

        self.make_button(actions, "저장", self.save).pack(side="left")
        self.make_button(actions, "서버 시작", self.start).pack(side="left", padx=8)
        self.make_button(actions, "서버 중지", self.stop).pack(side="left")
        self.make_button(actions, "웹 패널 열기", self.open_panel).pack(side="right")

        hints = tk.Label(
            shell,
            text="문제가 생기면 같은 폴더의 focusaway-launcher.log 를 확인해 주세요.",
            font=("Helvetica", 11),
            bg="#f5f5f7",
            fg="#6b7280",
            anchor="w",
        )
        hints.pack(fill="x", pady=(12, 0))

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
            app_name=self.config.app_name,
            operator_name=self.config.operator_name,
            contact_email=self.config.contact_email,
            contact_address=self.config.contact_address,
        )

    def save(self) -> None:
        self.config = self.current_config()
        path = save_config(self.config)
        self.status_var.set(f"설정을 저장했습니다: {path.name}")
        messagebox.showinfo("FocusAway", f"설정을 저장했습니다.\n{Path(path).resolve()}")

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            self.status_var.set("이미 실행 중입니다.")
            return

        try:
            self.config = self.current_config()
        except ValueError:
            messagebox.showerror("FocusAway", "Port 값은 숫자여야 합니다.")
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
        self.status_var.set(f"실행 중: http://{self.config.host}:{self.config.port}")

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            self.status_var.set("중지됨")
            return
        self.process.terminate()
        self.process.wait(timeout=5)
        self.status_var.set("중지됨")

    def open_panel(self) -> None:
        try:
            config = self.current_config()
        except ValueError:
            messagebox.showerror("FocusAway", "Port 값은 숫자여야 합니다.")
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
                "런처 시작 중 오류가 발생했습니다.\nfocusaway-launcher.log 파일을 확인해 주세요.",
            )
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
