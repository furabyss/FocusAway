from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from .config import AppConfig
from .quota import current_time_iso, current_week_anchor
from .security import generate_token, hash_password, verify_password

USERNAME_RE = re.compile(r"^[a-z0-9]+$")


class FocusAwayDB:
    def __init__(self, config: AppConfig):
        self.config = config
        Path(config.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._secure_database_file()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.config.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _secure_database_file(self) -> None:
        try:
            os.chmod(self.config.database_path, 0o600)
        except OSError:
            pass

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    api_key TEXT NOT NULL UNIQUE,
                    weekly_balance REAL NOT NULL DEFAULT 0,
                    bonus_balance REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sort_order INTEGER NOT NULL UNIQUE,
                    weekly_quota REAL NOT NULL DEFAULT 100,
                    is_system INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS model_policies (
                    model_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    model_kind TEXT NOT NULL DEFAULT '',
                    custom_model_kind TEXT NOT NULL DEFAULT '',
                    access_mode TEXT NOT NULL DEFAULT 'tier',
                    minimum_tier_id INTEGER,
                    context_window INTEGER,
                    max_output_tokens INTEGER,
                    custom_context_window INTEGER,
                    custom_max_output_tokens INTEGER,
                    cost_per_request REAL NOT NULL DEFAULT 1,
                    members_allowed INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quota_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    balance_type TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    model_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    cost REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            self._ensure_tiers(conn)
            self._ensure_user_columns(conn)
            self._ensure_model_columns(conn)
            self._ensure_setting(conn, "weekly_quota", "100")
            self._ensure_setting(conn, "last_week_anchor", current_week_anchor(self.config.timezone))
            self._ensure_setting(conn, "timezone", self.config.timezone)
            self._ensure_setting(conn, "signup_open", "1")
            self._ensure_setting(conn, "exclude_assistant_models", "0")

    def _ensure_tiers(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) AS count FROM tiers").fetchone()["count"]
        if count == 0:
            created_at = current_time_iso(self.config.timezone)
            weekly_quota = float(self.get_setting("weekly_quota", "100"))
            conn.execute(
                """
                INSERT INTO tiers(name, sort_order, weekly_quota, is_system, created_at)
                VALUES('Tier 0', 0, ?, 1, ?)
                """,
                (weekly_quota, created_at),
            )

    def _base_tier_id(self, conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT id FROM tiers WHERE is_system = 1 ORDER BY sort_order ASC, id ASC LIMIT 1"
        ).fetchone()
        if row:
            return int(row["id"])
        row = conn.execute("SELECT id FROM tiers ORDER BY sort_order ASC, id ASC LIMIT 1").fetchone()
        if not row:
            raise ValueError("기본 티어가 존재하지 않습니다.")
        return int(row["id"])

    def base_tier_sort_order(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT sort_order FROM tiers WHERE is_system = 1 ORDER BY sort_order ASC, id ASC LIMIT 1"
            ).fetchone()
            if row and row["sort_order"] is not None:
                return int(row["sort_order"])
            row = conn.execute("SELECT sort_order FROM tiers ORDER BY sort_order ASC, id ASC LIMIT 1").fetchone()
            if row and row["sort_order"] is not None:
                return int(row["sort_order"])
            return 0

    def _ensure_user_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "username" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "tier_id" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN tier_id INTEGER")
        if "is_suspended" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_suspended INTEGER NOT NULL DEFAULT 0")
        if "last_seen_ip" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_seen_ip TEXT NOT NULL DEFAULT ''")
        if "last_seen_at" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''")
        self._populate_missing_usernames(conn)
        self._populate_missing_tiers(conn)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")

    def _derive_username(self, source: str, fallback_id: int, used: set[str]) -> str:
        base = re.sub(r"[^a-z0-9]+", "", (source or "").split("@", 1)[0].lower())
        if not base:
            base = f"user{fallback_id}"
        candidate = base
        suffix = 1
        while candidate in used:
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

    def _populate_missing_usernames(self, conn: sqlite3.Connection) -> None:
        rows = conn.execute("SELECT id, email, username FROM users ORDER BY id ASC").fetchall()
        used = {str(row["username"]).strip().lower() for row in rows if row["username"]}
        for row in rows:
            username = str(row["username"] or "").strip().lower()
            if username:
                continue
            candidate = self._derive_username(str(row["email"] or ""), int(row["id"]), used)
            conn.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, row["id"]))
            used.add(candidate)

    def _populate_missing_tiers(self, conn: sqlite3.Connection) -> None:
        base_tier_id = self._base_tier_id(conn)
        conn.execute("UPDATE users SET tier_id = ? WHERE tier_id IS NULL", (base_tier_id,))

    def normalize_username(self, username: str) -> str:
        return username.strip().lower()

    def username_is_valid(self, username: str) -> bool:
        normalized = self.normalize_username(username)
        return bool(normalized) and bool(USERNAME_RE.fullmatch(normalized))

    def legacy_identity_for_username(self, username: str) -> str:
        return f"{self.normalize_username(username)}@local.focusaway"

    def _ensure_model_columns(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(model_policies)").fetchall()}
        if "model_kind" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN model_kind TEXT NOT NULL DEFAULT ''")
        if "custom_model_kind" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN custom_model_kind TEXT NOT NULL DEFAULT ''")
        if "access_mode" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN access_mode TEXT NOT NULL DEFAULT 'tier'")
        if "minimum_tier_id" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN minimum_tier_id INTEGER")
            base_tier_id = self._base_tier_id(conn)
            conn.execute(
                "UPDATE model_policies SET minimum_tier_id = ? WHERE members_allowed = 1",
                (base_tier_id,),
            )
        base_tier_id = self._base_tier_id(conn)
        conn.execute(
            "UPDATE model_policies SET access_mode = 'admin' WHERE members_allowed = 0 OR minimum_tier_id IS NULL"
        )
        conn.execute(
            "UPDATE model_policies SET access_mode = 'tier' WHERE access_mode IS NULL OR access_mode NOT IN ('admin', 'tier')"
        )
        conn.execute(
            "UPDATE model_policies SET minimum_tier_id = NULL WHERE access_mode = 'admin'"
        )
        conn.execute(
            "UPDATE model_policies SET minimum_tier_id = ? WHERE access_mode = 'tier' AND minimum_tier_id IS NULL",
            (base_tier_id,),
        )
        if "context_window" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN context_window INTEGER")
        if "max_output_tokens" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN max_output_tokens INTEGER")
        if "custom_context_window" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN custom_context_window INTEGER")
        if "custom_max_output_tokens" not in columns:
            conn.execute("ALTER TABLE model_policies ADD COLUMN custom_max_output_tokens INTEGER")

    def _coerce_positive_int(self, value) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _model_metadata_value(self, model: dict, keys: tuple[str, ...]) -> int | None:
        containers = [model]
        for nested_key in ("metadata", "meta", "limits", "capabilities"):
            nested = model.get(nested_key)
            if isinstance(nested, dict):
                containers.append(nested)
        for container in containers:
            for key in keys:
                value = self._coerce_positive_int(container.get(key))
                if value is not None:
                    return value
        return None

    def _model_metadata_text(self, model: dict, keys: tuple[str, ...]) -> str:
        containers = [model]
        for nested_key in ("metadata", "meta", "limits", "capabilities", "architecture"):
            nested = model.get(nested_key)
            if isinstance(nested, dict):
                containers.append(nested)
        for container in containers:
            for key in keys:
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, list):
                    parts = [str(item).strip() for item in value if str(item).strip()]
                    if parts:
                        return " ".join(parts)
        return ""

    def _model_kind_value(self, model: dict) -> str:
        explicit = self._model_metadata_text(
            model,
            (
                "model_kind",
                "kind",
                "modality",
                "type",
                "model_type",
                "architecture",
            ),
        ).lower()
        if explicit:
            if any(token in explicit for token in ("vlm", "vision", "multimodal", "image")):
                return "VLM"
            if any(token in explicit for token in ("llm", "text", "language")):
                return "LLM"

        modality_text = self._model_metadata_text(
            model,
            (
                "modalities",
                "input_modalities",
                "output_modalities",
                "supported_modalities",
            ),
        ).lower()
        if modality_text:
            if "image" in modality_text or "vision" in modality_text:
                return "VLM"
            if "text" in modality_text:
                return "LLM"

        for key in ("vision", "multimodal"):
            value = model.get(key)
            if isinstance(value, bool) and value:
                return "VLM"
        capabilities = model.get("capabilities")
        if isinstance(capabilities, dict):
            for key in ("vision", "image_input", "multimodal"):
                value = capabilities.get(key)
                if isinstance(value, bool) and value:
                    return "VLM"
        return ""

    def _ensure_setting(self, conn: sqlite3.Connection, key: str, value: str) -> None:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO NOTHING",
            (key, value),
        )

    def _normalize_admin_balances(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            UPDATE users
            SET weekly_balance = 0,
                bonus_balance = 0
            WHERE is_admin = 1
              AND (weekly_balance != 0 OR bonus_balance != 0)
            """
        )

    def ensure_weekly_reset(self) -> None:
        with self.connect() as conn:
            self._normalize_admin_balances(conn)
            anchor = current_week_anchor(self.config.timezone)
            row = conn.execute("SELECT value FROM settings WHERE key = 'last_week_anchor'").fetchone()
            if row and row["value"] == anchor:
                return

            base_quota = float(self.get_setting("weekly_quota", "100"))
            conn.execute(
                """
                UPDATE users
                SET weekly_balance = COALESCE(
                    (SELECT weekly_quota FROM tiers WHERE tiers.id = users.tier_id),
                    ?
                )
                WHERE users.is_admin = 0
                """,
                (base_quota,),
            )
            conn.execute(
                "UPDATE settings SET value = ? WHERE key = 'last_week_anchor'",
                (anchor,),
            )
            for user in conn.execute(
                """
                SELECT users.id, COALESCE(tiers.weekly_quota, ?) AS weekly_quota
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE users.is_admin = 0
                """,
                (base_quota,),
            ).fetchall():
                conn.execute(
                    """
                    INSERT INTO quota_ledger(user_id, amount, balance_type, event_type, description, created_at)
                    VALUES(?, ?, 'weekly', 'reset', 'Weekly recharge', ?)
                    """,
                    (user["id"], float(user["weekly_quota"]), current_time_iso(self.config.timezone)),
                )

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def auto_promotion_settings(self) -> dict:
        target_raw = self.get_setting("auto_promo_target_tier_id", "").strip()
        time_unit = self.get_setting("auto_promo_time_unit", "days").strip().lower()
        if time_unit not in {"days", "hours"}:
            time_unit = "days"
        return {
            "time_enabled": self.get_setting("auto_promo_time_enabled", "0") == "1",
            "time_value": self.get_setting("auto_promo_time_value", "7").strip() or "7",
            "time_unit": time_unit,
            "usage_enabled": self.get_setting("auto_promo_usage_enabled", "0") == "1",
            "usage_value": self.get_setting("auto_promo_usage_value", "10").strip() or "10",
            "target_tier_id": int(target_raw) if target_raw.isdigit() else None,
        }

    def set_auto_promotion_settings(self, settings: dict) -> None:
        self.set_setting("auto_promo_time_enabled", "1" if settings.get("time_enabled") else "0")
        self.set_setting("auto_promo_time_value", str(settings.get("time_value", "7")).strip() or "7")
        unit = str(settings.get("time_unit", "days")).strip().lower()
        self.set_setting("auto_promo_time_unit", unit if unit in {"days", "hours"} else "days")
        self.set_setting("auto_promo_usage_enabled", "1" if settings.get("usage_enabled") else "0")
        self.set_setting("auto_promo_usage_value", str(settings.get("usage_value", "10")).strip() or "10")
        target_tier_id = settings.get("target_tier_id")
        self.set_setting("auto_promo_target_tier_id", "" if target_tier_id in (None, "") else str(int(target_tier_id)))

    def _set_user_tier(
        self,
        conn: sqlite3.Connection,
        user: sqlite3.Row,
        new_tier: sqlite3.Row,
        promotion_event_type: str = "tier_promotion",
        promotion_description: str | None = None,
    ) -> None:
        user_id = int(user["id"])
        new_tier_id = int(new_tier["id"])
        conn.execute("UPDATE users SET tier_id = ? WHERE id = ?", (new_tier_id, user_id))

        current_sort_order = user["current_tier_sort_order"]
        new_sort_order = new_tier["sort_order"]
        current_weekly_balance = float(user["weekly_balance"] or 0)
        new_weekly_quota = float(new_tier["weekly_quota"] or 0)
        if (
            current_sort_order is not None
            and new_sort_order is not None
            and int(new_sort_order) > int(current_sort_order)
            and current_weekly_balance < new_weekly_quota
        ):
            top_up_amount = new_weekly_quota - current_weekly_balance
            conn.execute(
                "UPDATE users SET weekly_balance = ? WHERE id = ?",
                (new_weekly_quota, user_id),
            )
            conn.execute(
                """
                INSERT INTO quota_ledger(user_id, amount, balance_type, event_type, description, created_at)
                VALUES(?, ?, 'weekly', ?, ?, ?)
                """,
                (
                    user_id,
                    top_up_amount,
                    promotion_event_type,
                    promotion_description or f"Tier promotion to {new_tier['name']}",
                    current_time_iso(self.config.timezone),
                ),
            )

    def ensure_automatic_promotions(self) -> None:
        config = self.auto_promotion_settings()
        if not config["time_enabled"] and not config["usage_enabled"]:
            return

        try:
            target_tier_id = int(config["target_tier_id"])
        except (TypeError, ValueError):
            return

        with self.connect() as conn:
            target_tier = conn.execute(
                "SELECT id, name, sort_order, weekly_quota, is_system FROM tiers WHERE id = ?",
                (target_tier_id,),
            ).fetchone()
            if not target_tier or target_tier["is_system"]:
                return

            try:
                time_value = int(float(config["time_value"]))
            except (TypeError, ValueError):
                time_value = 0
            try:
                usage_value = float(config["usage_value"])
            except (TypeError, ValueError):
                usage_value = 0.0

            if config["time_enabled"] and time_value <= 0:
                return
            if config["usage_enabled"] and usage_value < 0:
                return

            now = datetime.now(ZoneInfo(self.config.timezone))
            usage_rows = conn.execute(
                """
                SELECT users.id, users.created_at, users.weekly_balance, users.tier_id,
                       tiers.sort_order AS current_tier_sort_order,
                       COALESCE(usage.total_cost, 0) AS total_usage_cost
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                LEFT JOIN (
                    SELECT user_id, SUM(cost) AS total_cost
                    FROM api_usage
                    GROUP BY user_id
                ) AS usage ON usage.user_id = users.id
                WHERE users.is_admin = 0
                  AND COALESCE(tiers.sort_order, -1) < ?
                """,
                (target_tier["sort_order"],),
            ).fetchall()

            if config["time_enabled"]:
                threshold_delta = (
                    timedelta(hours=time_value)
                    if config["time_unit"] == "hours"
                    else timedelta(days=time_value)
                )
            else:
                threshold_delta = None

            for user in usage_rows:
                time_met = False
                usage_met = False

                if config["time_enabled"] and threshold_delta is not None:
                    try:
                        created_at = datetime.fromisoformat(str(user["created_at"]))
                    except ValueError:
                        created_at = None
                    if created_at is not None:
                        try:
                            created_at = created_at.astimezone(ZoneInfo(self.config.timezone))
                        except ValueError:
                            pass
                        time_met = created_at <= now - threshold_delta

                if config["usage_enabled"]:
                    usage_met = float(user["total_usage_cost"] or 0) + 1e-9 >= usage_value

                if time_met or usage_met:
                    self._set_user_tier(
                        conn,
                        user,
                        target_tier,
                        promotion_event_type="auto_tier_promotion",
                        promotion_description=f"Automatic promotion to {target_tier['name']}",
                    )

    def list_tiers(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, name, sort_order, weekly_quota, is_system, created_at
                FROM tiers
                ORDER BY sort_order DESC, id DESC
                """
            ).fetchall()

    def create_tier(self) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) AS max_sort FROM tiers"
            ).fetchone()
            next_sort = int(row["max_sort"]) + 1
            existing_names = {str(item["name"]) for item in conn.execute("SELECT name FROM tiers").fetchall()}
            index = 1
            while f"Tier {index}" in existing_names:
                index += 1
            base_tier = conn.execute(
                "SELECT weekly_quota FROM tiers WHERE is_system = 1 ORDER BY sort_order ASC, id ASC LIMIT 1"
            ).fetchone()
            default_quota = float(base_tier["weekly_quota"]) if base_tier and base_tier["weekly_quota"] is not None else 100.0
            conn.execute(
                """
                INSERT INTO tiers(name, sort_order, weekly_quota, is_system, created_at)
                VALUES(?, ?, ?, 0, ?)
                """,
                (f"Tier {index}", next_sort, default_quota, current_time_iso(self.config.timezone)),
            )

    def update_tiers_bulk(self, updates: list[dict]) -> None:
        with self.connect() as conn:
            seen_names: set[str] = set()
            for update in updates:
                tier_id = int(update["id"])
                name = str(update["name"]).strip() or f"Tier {tier_id}"
                weekly_quota = float(update["weekly_quota"])
                if weekly_quota < 0:
                    raise ValueError("주간 충전량은 0 이상이어야 합니다.")
                if name in seen_names:
                    raise ValueError("티어 이름은 중복될 수 없습니다.")
                existing = conn.execute(
                    "SELECT id FROM tiers WHERE name = ? AND id != ?",
                    (name, tier_id),
                ).fetchone()
                if existing:
                    raise ValueError("티어 이름은 중복될 수 없습니다.")
                seen_names.add(name)
                conn.execute(
                    "UPDATE tiers SET name = ?, weekly_quota = ? WHERE id = ?",
                    (name, weekly_quota, tier_id),
                )

    def move_tier(self, tier_id: int, direction: str) -> None:
        with self.connect() as conn:
            current = conn.execute("SELECT id, sort_order FROM tiers WHERE id = ?", (tier_id,)).fetchone()
            if not current:
                return
            if direction == "up":
                other = conn.execute(
                    "SELECT id, sort_order FROM tiers WHERE sort_order > ? ORDER BY sort_order ASC LIMIT 1",
                    (current["sort_order"],),
                ).fetchone()
            else:
                other = conn.execute(
                    "SELECT id, sort_order FROM tiers WHERE sort_order < ? ORDER BY sort_order DESC LIMIT 1",
                    (current["sort_order"],),
                ).fetchone()
            if not other:
                return
            conn.execute("UPDATE tiers SET sort_order = -1 WHERE id = ?", (current["id"],))
            conn.execute("UPDATE tiers SET sort_order = ? WHERE id = ?", (current["sort_order"], other["id"]))
            conn.execute("UPDATE tiers SET sort_order = ? WHERE id = ?", (other["sort_order"], current["id"]))

    def delete_tier(self, tier_id: int) -> None:
        with self.connect() as conn:
            tier = conn.execute("SELECT id, sort_order, is_system FROM tiers WHERE id = ?", (tier_id,)).fetchone()
            if not tier:
                return
            if tier["is_system"]:
                raise ValueError("기본 티어는 삭제할 수 없습니다.")
            fallback = conn.execute(
                """
                SELECT id FROM tiers
                WHERE id != ?
                ORDER BY CASE WHEN sort_order < ? THEN 0 ELSE 1 END, sort_order DESC, id DESC
                LIMIT 1
                """,
                (tier_id, tier["sort_order"]),
            ).fetchone()
            if not fallback:
                raise ValueError("삭제 가능한 대체 티어가 없습니다.")
            fallback_id = int(fallback["id"])
            conn.execute("UPDATE users SET tier_id = ? WHERE tier_id = ?", (fallback_id, tier_id))
            conn.execute("UPDATE model_policies SET minimum_tier_id = ? WHERE minimum_tier_id = ?", (fallback_id, tier_id))
            conn.execute("DELETE FROM tiers WHERE id = ?", (tier_id,))

    def update_user_tier(self, user_id: int, tier_id: int) -> None:
        with self.connect() as conn:
            user = conn.execute(
                """
                SELECT users.id, users.is_admin, users.tier_id, users.weekly_balance,
                       tiers.sort_order AS current_tier_sort_order
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
            if not user:
                raise ValueError("회원을 찾을 수 없습니다.")
            if user["is_admin"]:
                raise ValueError("관리자 계정의 티어는 변경할 수 없습니다.")
            new_tier = conn.execute(
                "SELECT id, sort_order, weekly_quota, name FROM tiers WHERE id = ?",
                (tier_id,),
            ).fetchone()
            if not new_tier:
                raise ValueError("티어를 찾을 수 없습니다.")
            self._set_user_tier(conn, user, new_tier)

    def create_user(self, username: str, password: str) -> sqlite3.Row:
        self.ensure_weekly_reset()
        normalized_username = self.normalize_username(username)
        if not self.username_is_valid(normalized_username):
            raise ValueError("invalid_username")
        with self.connect() as conn:
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            is_admin = 1 if user_count == 0 else 0
            base_tier_id = self._base_tier_id(conn)
            tier = conn.execute("SELECT weekly_quota FROM tiers WHERE id = ?", (base_tier_id,)).fetchone()
            weekly_quota = (
                0.0
                if is_admin
                else (float(tier["weekly_quota"]) if tier else float(self.get_setting("weekly_quota", "100")))
            )
            created_at = current_time_iso(self.config.timezone)
            conn.execute(
                """
                INSERT INTO users(username, email, password_hash, is_admin, api_key, weekly_balance, bonus_balance, created_at, tier_id)
                VALUES(?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    normalized_username,
                    self.legacy_identity_for_username(normalized_username),
                    hash_password(password),
                    is_admin,
                    generate_token("fk"),
                    weekly_quota,
                    created_at,
                    base_tier_id,
                ),
            )
            user = conn.execute("SELECT * FROM users WHERE username = ?", (normalized_username,)).fetchone()
            if not is_admin:
                conn.execute(
                    """
                    INSERT INTO quota_ledger(user_id, amount, balance_type, event_type, description, created_at)
                    VALUES(?, ?, 'weekly', 'signup', 'Initial weekly balance', ?)
                    """,
                    (user["id"], weekly_quota, created_at),
                )
            return user

    def record_user_activity(self, user_id: int, ip_address: str) -> None:
        timestamp = current_time_iso(self.config.timezone)
        with self.connect() as conn:
            conn.execute(
                "UPDATE users SET last_seen_ip = ?, last_seen_at = ? WHERE id = ?",
                (ip_address[:255], timestamp, user_id),
            )

    def update_user_password(self, user_id: int, current_password: str, new_password: str) -> None:
        with self.connect() as conn:
            user = conn.execute("SELECT id, password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise ValueError("사용자를 찾을 수 없습니다.")
            if not verify_password(current_password, user["password_hash"]):
                raise ValueError("현재 비밀번호가 올바르지 않습니다.")
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user_id),
            )
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def authenticate_user(self, username: str, password: str):
        normalized_username = self.normalize_username(username)
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (normalized_username,)).fetchone()
            if not user or not verify_password(password, user["password_hash"]):
                return None
            if user["is_suspended"]:
                return None
            return user

    def create_session(self, user_id: int) -> str:
        token = generate_token("sess")
        created_at = current_time_iso(self.config.timezone)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(token, user_id, expires_at, created_at)
                VALUES(?, ?, datetime('now', ?), ?)
                """,
                (token, user_id, f"+{self.config.session_hours} hours", created_at),
            )
        return token

    def get_user_by_session(self, token: str):
        self.ensure_weekly_reset()
        self.ensure_automatic_promotions()
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.*, tiers.name AS tier_name, tiers.sort_order AS tier_sort_order
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE sessions.token = ?
                  AND sessions.expires_at > datetime('now')
                  AND users.is_suspended = 0
                """,
                (token,),
            ).fetchone()
            return row

    def delete_session(self, token: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def get_user_by_api_key(self, api_key: str):
        self.ensure_weekly_reset()
        self.ensure_automatic_promotions()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT users.*, tiers.name AS tier_name, tiers.sort_order AS tier_sort_order
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE api_key = ? AND is_suspended = 0
                """,
                (api_key,),
            ).fetchone()

    def rotate_user_api_key(self, user_id: int) -> str:
        api_key = generate_token("fk")
        with self.connect() as conn:
            conn.execute("UPDATE users SET api_key = ? WHERE id = ?", (api_key, user_id))
        return api_key

    def list_users(self) -> list[sqlite3.Row]:
        self.ensure_weekly_reset()
        self.ensure_automatic_promotions()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT users.id, users.username, users.is_admin, users.is_suspended, users.weekly_balance, users.bonus_balance,
                       users.last_seen_ip, users.last_seen_at, users.created_at, users.tier_id, tiers.name AS tier_name
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                ORDER BY users.id ASC
                """
            ).fetchall()

    def get_user(self, user_id: int):
        self.ensure_weekly_reset()
        self.ensure_automatic_promotions()
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT users.id, users.username, users.is_admin, users.is_suspended, users.weekly_balance, users.bonus_balance,
                       users.api_key, users.last_seen_ip, users.last_seen_at, users.created_at, users.tier_id,
                       tiers.name AS tier_name, tiers.sort_order AS tier_sort_order
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()

    def update_user_suspension(self, user_id: int, suspended: bool) -> None:
        with self.connect() as conn:
            user = conn.execute("SELECT id, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return
            if user["is_admin"]:
                raise ValueError("관리자 계정은 정지할 수 없습니다.")
            conn.execute("UPDATE users SET is_suspended = ? WHERE id = ?", (1 if suspended else 0, user_id))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    def delete_user(self, user_id: int, allow_admin: bool = False) -> None:
        with self.connect() as conn:
            user = conn.execute("SELECT id, is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return
            if user["is_admin"] and not allow_admin:
                raise ValueError("관리자 계정은 삭제할 수 없습니다.")
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def update_weekly_quota(self, amount: float) -> None:
        self.set_setting("weekly_quota", str(amount))

    def grant_bonus(self, amount: float, description: str, username: str | None = None) -> None:
        with self.connect() as conn:
            target_rows = (
                conn.execute(
                    "SELECT id FROM users WHERE username = ? AND is_admin = 0",
                    (self.normalize_username(username),),
                ).fetchall()
                if username
                else conn.execute("SELECT id FROM users WHERE is_admin = 0").fetchall()
            )
            created_at = current_time_iso(self.config.timezone)
            for row in target_rows:
                conn.execute(
                    "UPDATE users SET bonus_balance = bonus_balance + ? WHERE id = ?",
                    (amount, row["id"]),
                )
                conn.execute(
                    """
                    INSERT INTO quota_ledger(user_id, amount, balance_type, event_type, description, created_at)
                    VALUES(?, ?, 'bonus', 'grant', ?, ?)
                    """,
                    (row["id"], amount, description, created_at),
                )

    def list_models(self, include_restricted: bool = True):
        with self.connect() as conn:
            if include_restricted:
                return conn.execute(
                    """
                    SELECT model_policies.*, tiers.name AS minimum_tier_name, tiers.sort_order AS minimum_tier_sort_order
                    FROM model_policies
                    LEFT JOIN tiers ON tiers.id = model_policies.minimum_tier_id
                    ORDER BY display_name COLLATE NOCASE ASC
                    """
                ).fetchall()
            return conn.execute(
                """
                SELECT model_policies.*, tiers.name AS minimum_tier_name, tiers.sort_order AS minimum_tier_sort_order
                FROM model_policies
                LEFT JOIN tiers ON tiers.id = model_policies.minimum_tier_id
                WHERE access_mode = 'tier'
                ORDER BY display_name COLLATE NOCASE ASC
                """
            ).fetchall()

    def accessible_models_for_user(self, is_admin: bool, tier_sort_order: int | None = None):
        with self.connect() as conn:
            if is_admin:
                return conn.execute(
                    """
                    SELECT model_policies.*, tiers.name AS minimum_tier_name, tiers.sort_order AS minimum_tier_sort_order
                    FROM model_policies
                    LEFT JOIN tiers ON tiers.id = model_policies.minimum_tier_id
                    ORDER BY display_name COLLATE NOCASE ASC
                    """
                ).fetchall()
            return conn.execute(
                """
                SELECT model_policies.*, tiers.name AS minimum_tier_name, tiers.sort_order AS minimum_tier_sort_order
                FROM model_policies
                LEFT JOIN tiers ON tiers.id = model_policies.minimum_tier_id
                WHERE access_mode = 'tier'
                  AND tiers.sort_order <= ?
                ORDER BY display_name COLLATE NOCASE ASC
                """,
                (tier_sort_order if tier_sort_order is not None else -1,),
            ).fetchall()

    def upsert_models(self, models: list[dict]) -> None:
        timestamp = current_time_iso(self.config.timezone)
        model_ids = []
        with self.connect() as conn:
            for model in models:
                model_id = model.get("id") or model.get("name")
                if not model_id:
                    continue
                model_ids.append(model_id)
                model_kind = self._model_kind_value(model)
                context_window = self._model_metadata_value(
                    model,
                    (
                        "context_window",
                        "context_length",
                        "max_context_length",
                        "max_input_tokens",
                        "context_tokens",
                        "num_ctx",
                        "max_model_len",
                    ),
                )
                max_output_tokens = self._model_metadata_value(
                    model,
                    (
                        "max_output_tokens",
                        "max_completion_tokens",
                        "max_tokens",
                        "completion_tokens",
                        "output_tokens",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO model_policies(
                        model_id, display_name, model_kind, access_mode, minimum_tier_id, context_window, max_output_tokens, cost_per_request, members_allowed, updated_at
                    )
                    VALUES(?, ?, ?, 'tier', ?, ?, ?, 1, 1, ?)
                    ON CONFLICT(model_id) DO UPDATE SET
                        display_name = excluded.display_name,
                        model_kind = excluded.model_kind,
                        access_mode = model_policies.access_mode,
                        minimum_tier_id = model_policies.minimum_tier_id,
                        context_window = excluded.context_window,
                        max_output_tokens = excluded.max_output_tokens,
                        updated_at = excluded.updated_at
                    """,
                    (model_id, model_id, model_kind, self._base_tier_id(conn), context_window, max_output_tokens, timestamp),
                )
            if model_ids:
                placeholders = ",".join("?" for _ in model_ids)
                conn.execute(
                    f"DELETE FROM model_policies WHERE model_id NOT IN ({placeholders})",
                    model_ids,
                )
            else:
                conn.execute("DELETE FROM model_policies")

    def update_model_policy(self, model_id: str, cost_per_request: float, members_allowed: bool) -> None:
        with self.connect() as conn:
            minimum_tier_id = self._base_tier_id(conn) if members_allowed else None
            conn.execute(
                """
                UPDATE model_policies
                SET cost_per_request = ?, members_allowed = ?, access_mode = ?, minimum_tier_id = ?, updated_at = ?
                WHERE model_id = ?
                """,
                (
                    round(cost_per_request, 2),
                    1 if members_allowed else 0,
                    "tier" if members_allowed else "admin",
                    minimum_tier_id,
                    current_time_iso(self.config.timezone),
                    model_id,
                ),
            )

    def update_model_policies_bulk(self, updates: list[dict]) -> None:
        with self.connect() as conn:
            timestamp = current_time_iso(self.config.timezone)
            for update in updates:
                conn.execute(
                    """
                    UPDATE model_policies
                    SET cost_per_request = ?, members_allowed = ?, access_mode = ?, minimum_tier_id = ?, custom_model_kind = ?, custom_context_window = ?, custom_max_output_tokens = ?, updated_at = ?
                    WHERE model_id = ?
                    """,
                    (
                        round(float(update["cost_per_request"]), 2),
                        1 if update.get("access_mode") == "tier" else 0,
                        update.get("access_mode", "tier"),
                        update.get("minimum_tier_id"),
                        update.get("custom_model_kind", ""),
                        update.get("custom_context_window"),
                        update.get("custom_max_output_tokens"),
                        timestamp,
                        update["model_id"],
                    ),
                )

    def get_model_policy(self, model_id: str):
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT model_policies.*, tiers.name AS minimum_tier_name, tiers.sort_order AS minimum_tier_sort_order
                FROM model_policies
                LEFT JOIN tiers ON tiers.id = model_policies.minimum_tier_id
                WHERE model_id = ?
                """,
                (model_id,),
            ).fetchone()

    def charge_request(self, user_id: int, model_id: str, endpoint: str, cost: float) -> tuple[bool, str]:
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                return False, "User not found."
            timestamp = current_time_iso(self.config.timezone)
            if user["is_admin"]:
                conn.execute(
                    """
                    INSERT INTO api_usage(user_id, model_id, endpoint, cost, created_at)
                    VALUES(?, ?, ?, 0, ?)
                    """,
                    (user_id, model_id, endpoint, timestamp),
                )
                return True, ""
            total_balance = float(user["weekly_balance"]) + float(user["bonus_balance"])
            if total_balance + 1e-9 < cost:
                return False, "Insufficient premium request balance."

            weekly_spend = min(float(user["weekly_balance"]), cost)
            bonus_spend = cost - weekly_spend
            conn.execute(
                "UPDATE users SET weekly_balance = weekly_balance - ?, bonus_balance = bonus_balance - ? WHERE id = ?",
                (weekly_spend, bonus_spend, user_id),
            )
            conn.execute(
                """
                INSERT INTO api_usage(user_id, model_id, endpoint, cost, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (user_id, model_id, endpoint, cost, timestamp),
            )
            conn.execute(
                """
                INSERT INTO quota_ledger(user_id, amount, balance_type, event_type, description, created_at)
                VALUES(?, ?, 'mixed', 'usage', ?, ?)
                """,
                (user_id, -cost, f"{endpoint} via {model_id}", timestamp),
            )
            return True, ""

    def dashboard_payload_for_user(self, user_id: int) -> dict:
        user = self.get_user(user_id)
        models = (
            self.list_models(include_restricted=True)
            if user["is_admin"]
            else self.list_models(include_restricted=False)
        )
        tier_quota = self.user_tier_quota(user_id)
        return {
            "user": dict(user),
            "models": [dict(row) for row in models],
            "weekly_quota": float(tier_quota),
        }

    def user_tier_quota(self, user_id: int) -> float:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT tiers.weekly_quota
                FROM users
                LEFT JOIN tiers ON tiers.id = users.tier_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
            if row and row["weekly_quota"] is not None:
                return float(row["weekly_quota"])
            return float(self.get_setting("weekly_quota", "100"))

    def recent_usage_for_user(self, user_id: int) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT model_id, endpoint, cost, created_at
                FROM api_usage
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 20
                """,
                (user_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def usage_series_for_user(self, user_id: int, days: int = 7) -> list[dict]:
        timezone = ZoneInfo(self.config.timezone)
        today = datetime.now(timezone).date()
        start_day = today - timedelta(days=days - 1)
        buckets = {}

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT cost, created_at
                FROM api_usage
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()

        for row in rows:
            try:
                created_at = datetime.fromisoformat(row["created_at"]).astimezone(timezone).date()
            except ValueError:
                continue
            if created_at < start_day or created_at > today:
                continue
            key = created_at.isoformat()
            buckets[key] = buckets.get(key, 0.0) + float(row["cost"])

        series = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            key = day.isoformat()
            series.append(
                {
                    "date": key,
                    "label": day.strftime("%m/%d"),
                    "cost": round(buckets.get(key, 0.0), 2),
                }
            )
        return series

    def usage_hourly_series_for_user(self, user_id: int, hours: int = 24) -> list[dict]:
        timezone = ZoneInfo(self.config.timezone)
        now = datetime.now(timezone).replace(minute=0, second=0, microsecond=0)
        start_time = now - timedelta(hours=hours - 1)
        buckets = {}

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT cost, created_at
                FROM api_usage
                WHERE user_id = ?
                ORDER BY created_at ASC
                """,
                (user_id,),
            ).fetchall()

        for row in rows:
            try:
                created_at = datetime.fromisoformat(row["created_at"]).astimezone(timezone)
            except ValueError:
                continue
            created_bucket = created_at.replace(minute=0, second=0, microsecond=0)
            if created_bucket < start_time or created_bucket > now:
                continue
            key = created_bucket.isoformat()
            buckets[key] = buckets.get(key, 0.0) + float(row["cost"])

        series = []
        for offset in range(hours):
            point = start_time + timedelta(hours=offset)
            key = point.isoformat()
            series.append(
                {
                    "date": key,
                    "label": point.strftime("%H:%M"),
                    "cost": round(buckets.get(key, 0.0), 2),
                }
            )
        return series

    def admin_snapshot(self) -> dict:
        return {
            "weekly_quota": float(self.get_setting("weekly_quota", "100")),
            "auto_promotion": self.auto_promotion_settings(),
            "tiers": [dict(row) for row in self.list_tiers()],
            "users": [dict(row) for row in self.list_users()],
            "models": [dict(row) for row in self.list_models()],
        }
