from __future__ import annotations

import html
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .config import AppConfig
from .db import FocusAwayDB
from .security import generate_token
from .upstream import UpstreamClient


APP_VERSION = "1.0.2"
APP_COPYRIGHT = "ⓒ 2026 Fur-Abyss."
LANGUAGE_OPTIONS = {"ko": "한국어", "en": "English"}
TEXT = {
    "ko": {
        "language": "언어:",
        "login": "로그인",
        "signup": "회원가입",
        "dashboard": "대시보드",
        "admin_panel": "관리자 패널",
        "logout": "로그아웃",
        "username": "아이디",
        "password": "비밀번호",
        "current_password": "현재 비밀번호",
        "new_password": "새 비밀번호",
        "create_account": "계정 만들기",
        "already_have_account": "이미 계정이 있어요",
        "terms": "이용약관",
        "privacy": "개인정보처리방침",
        "copy": "복사",
        "copied": "복사됨",
        "refresh_failed": "새로고침 실패",
        "refresh": "새로고침",
        "save": "저장",
        "member": "회원",
        "admin": "관리자",
        "admin_fixed": "관리자 고정",
        "admin_protected": "관리자 보호",
        "normal": "정상",
        "suspended": "정지됨",
        "suspend": "정지",
        "unsuspend": "정지 해제",
        "delete": "강퇴",
        "apply": "적용",
        "tier_or_higher": "{name} 이상",
        "admin_only": "관리자 전용",
        "base_tier": "기본 티어",
        "fixed": "고정",
        "none": "-",
        "unassigned": "미지정",
        "model_name_copy": "모델 이름 복사",
        "context_window": "컨텍스트 윈도우",
        "output_token_limit": "출력 토큰 한도",
        "cost_per_request": "1회 비용",
        "recent_24h_calls": "최근 24시간 호출 횟수",
        "total_calls": "총 {count}회",
        "no_models": "아직 동기화된 모델이 없습니다.",
        "no_models_refresh": "아직 동기화된 모델이 없습니다. 아래 버튼으로 새로고침해 주세요.",
        "no_usage": "아직 사용 내역이 없습니다.",
        "model": "모델",
        "endpoint": "엔드포인트",
        "cost": "비용",
        "time": "시각",
        "remaining_premium": "남은 프리미엄 요청",
        "admin_privileges": "관리자 권한",
        "unlimited": "Unlimited",
        "weekly_balance": "주간 잔액",
        "bonus_balance": "보너스 잔액",
        "weekly_quota": "내 주간 충전량",
        "api_key": "API 키",
        "my_api_key": "내 전용 API 키",
        "api_base": "프론트엔드 입력용 API 주소",
        "api_root": "OpenAI 호환 API 루트",
        "loading": "불러오는 중...",
        "rotate_api_key": "API 키 재발급",
        "models": "모델 목록",
        "recent_usage": "최근 사용 내역",
        "account": "계정 관리",
        "change_password": "비밀번호 변경",
        "delete_account": "계정 탈퇴",
    },
    "en": {
        "language": "Language:",
        "login": "Log In",
        "signup": "Sign Up",
        "dashboard": "Dashboard",
        "admin_panel": "Admin Panel",
        "logout": "Log Out",
        "username": "Username",
        "password": "Password",
        "current_password": "Current Password",
        "new_password": "New Password",
        "create_account": "Create Account",
        "already_have_account": "I already have an account",
        "terms": "Terms of Service",
        "privacy": "Privacy Policy",
        "copy": "Copy",
        "copied": "Copied",
        "refresh_failed": "Refresh failed",
        "refresh": "Refresh",
        "save": "Save",
        "member": "Member",
        "admin": "Admin",
        "admin_fixed": "Admin fixed",
        "admin_protected": "Admin protected",
        "normal": "Active",
        "suspended": "Suspended",
        "suspend": "Suspend",
        "unsuspend": "Unsuspend",
        "delete": "Delete",
        "apply": "Apply",
        "tier_or_higher": "{name}+",
        "admin_only": "Admin only",
        "base_tier": "Base tier",
        "fixed": "Fixed",
        "none": "-",
        "unassigned": "Unassigned",
        "model_name_copy": "Copy model name",
        "context_window": "Context Window",
        "output_token_limit": "Output Token Limit",
        "cost_per_request": "Cost",
        "recent_24h_calls": "Calls in the last 24h",
        "total_calls": "Total {count}",
        "no_models": "No models have been synchronized yet.",
        "no_models_refresh": "No models have been synchronized yet. Use the refresh button below.",
        "no_usage": "No usage yet.",
        "model": "Model",
        "endpoint": "Endpoint",
        "cost": "Cost",
        "time": "Time",
        "remaining_premium": "Premium Requests Left",
        "admin_privileges": "Admin Privileges",
        "unlimited": "Unlimited",
        "weekly_balance": "Weekly balance",
        "bonus_balance": "Bonus balance",
        "weekly_quota": "My weekly quota",
        "api_key": "API Key",
        "my_api_key": "My API Key",
        "api_base": "API base URL for frontends",
        "api_root": "OpenAI-compatible API root",
        "loading": "Loading...",
        "rotate_api_key": "Rotate API Key",
        "models": "Models",
        "recent_usage": "Recent Usage",
        "account": "Account",
        "change_password": "Change Password",
        "delete_account": "Delete Account",
    },
}
EN_REPLACEMENTS = {
    "관리자 패널": "Admin Panel",
    "사용자 대시보드": "User Dashboard",
    "회원 티어, 티어별 주간 충전량, 모델 접근 정책을 관리합니다.": "Manage member tiers, weekly quotas, and model access policies.",
    "서비스 설정": "Service Settings",
    "회원가입 상태": "Signup Status",
    "모델명에 assistant가 포함된 모델은 동기화 시 제외": "Exclude models containing assistant in their name during sync",
    "티어 자동 승격": "Automatic Tier Promotion",
    "선택한 조건 중 하나를 만족하면 아래 티어로 자동 승격됩니다.": "Users are promoted to the tier below when any selected condition is met.",
    "가입 후 경과 시간 조건 사용": "Use elapsed time since signup",
    "가입 후 프리미엄 요청 누적 사용량 조건 사용": "Use cumulative premium request usage since signup",
    "이상 사용 시": "or more used",
    "자동 승격 티어": "Target promotion tier",
    "선택 안 함": "Not selected",
    "티어 관리": "Tier Management",
    "티어 추가": "Add Tier",
    "티어 이름": "Tier Name",
    "순서": "Order",
    "주간 충전량": "Weekly Quota",
    "작업": "Actions",
    "1회 비용": "Cost",
    "티어 전체 저장": "Save All Tiers",
    "보너스 일괄/개별 지급": "Bulk/Individual Bonus Grant",
    "지급량": "Amount",
    "설명": "Description",
    "대상 아이디 (비우면 전체 지급)": "Target username (blank means all users)",
    "지급": "Grant",
    "모델 정책": "Model Policies",
    "백엔드에서 모델 새로고침": "Refresh Models from Backend",
    "사용자에게 제공할 모델명": "Public model name",
    "백엔드 모델 ID": "Backend model ID",
    "모델 종류": "Model Kind",
    "서버 기본값": "Server default",
    "커스텀 컨텍스트 한도": "Custom context limit",
    "커스텀 출력 한도": "Custom output limit",
    "비우면 백엔드 기본값": "Blank uses backend default",
    "사용 가능 티어": "Available Tier",
    "모델 정책 전체 저장": "Save All Model Policies",
    "회원 현황": "Users",
    "고유 번호": "User No.",
    "아이디": "Username",
    "현재 티어": "Current Tier",
    "티어 변경": "Change Tier",
    "권한": "Role",
    "상태": "Status",
    "마지막 접속 IP": "Last Seen IP",
    "보너스 잔액": "Bonus Balance",
    "주간 잔액": "Weekly Balance",
    "회원이 없습니다.": "No users.",
    "티어가 없습니다.": "No tiers.",
    "관리자 전용": "Admin only",
    "기본 티어": "Base tier",
    "관리자 고정": "Admin fixed",
    "관리자 보호": "Admin protected",
    "회원가입 불가": "Signup Closed",
    "현재는 신규 회원가입을 받고 있지 않습니다.": "New signups are currently closed.",
    "로그인으로 돌아가기": "Back to Login",
    "관리자가 회원가입을 다시 열기 전까지 새 계정을 만들 수 없습니다.": "New accounts cannot be created until the administrator reopens signup.",
}


def html_page(title: str, body: str, language: str = "ko") -> bytes:
    labels = TEXT.get(language, TEXT["en"])
    language_options = "".join(
        f'<option value="{code}" {"selected" if language == code else ""}>{html.escape(label)}</option>'
        for code, label in LANGUAGE_OPTIONS.items()
    )
    return f"""<!doctype html>
<html lang="{html.escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f5f5f7;
      --panel: #ffffff;
      --ink: #18181b;
      --muted: #6b7280;
      --line: #e5e7eb;
      --accent: #3f3f46;
      --accent-soft: #f0f1f3;
      --danger: #b42318;
    }}
    html, body {{ min-height: 100%; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.9), transparent 30%),
        linear-gradient(180deg, #fafafa 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: "SF Pro Display", "SF Pro Text", "Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", "Helvetica Neue", Arial, sans-serif;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    .shell {{ max-width: 1080px; margin: 0 auto; padding: 32px 20px 64px; }}
    .footer {{
      margin-top: 28px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.88rem;
      text-align: center;
    }}
    .hero {{ display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 28px; }}
    .hero-copy {{ display: grid; gap: 12px; justify-items: start; }}
    .hero h1 {{ margin: 0; font-size: 2.6rem; line-height: 1; }}
    .hero p {{ margin: 8px 0 0; color: var(--muted); }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 22px;
      box-shadow: 0 10px 30px rgba(24,24,27,0.05);
      margin-bottom: 18px;
    }}
    .grid {{ display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    .card h2, .card h3 {{ margin: 0 0 14px; }}
    .metric {{ font-size: 2rem; font-weight: 700; }}
    .chart {{
      margin-top: 14px;
      padding-top: 10px;
      border-top: 1px solid var(--line);
    }}
    .chart-tabs {{
      display: flex;
      gap: 8px;
      margin: 10px 0 12px;
      flex-wrap: wrap;
    }}
    .chart-tab {{
      background: var(--accent-soft);
      color: var(--ink);
      border: 1px solid var(--line);
    }}
    .chart-panel[hidden] {{ display: none; }}
    .chart svg {{
      display: block;
      width: 100%;
      height: auto;
      aspect-ratio: 1000 / 150;
    }}
    .chart-summary {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .chart-grid {{
      stroke: #e5e7eb;
      stroke-width: 1;
    }}
    .chart-line {{
      fill: none;
      stroke: #3f3f46;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .chart-area {{
      fill: rgba(63, 63, 70, 0.08);
    }}
    .chart-point {{
      fill: #3f3f46;
    }}
    .chart-axis-label {{
      fill: #6b7280;
      font-size: 18px;
    }}
    .chart-y-label {{
      fill: #6b7280;
      font-size: 16px;
    }}
    .stack {{ display: grid; gap: 16px; }}
    .model-grid {{ display: grid; gap: 16px; grid-template-columns: 1fr; }}
    .model-card {{
      background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      display: grid;
      gap: 14px;
    }}
    .model-card-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .model-card-title {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      min-width: 0;
    }}
    .model-card h3 {{ margin: 0; }}
    .model-kind {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 48px;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid #dcdfe4;
      background: #f5f6f8;
      color: #4b5563;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.03em;
    }}
    .model-access-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 32px;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid #dcdfe4;
      background: #f8f9fb;
      color: #52525b;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.01em;
      white-space: nowrap;
      line-height: 1;
    }}
    .model-copy-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      padding: 0;
      border-radius: 10px;
      border: 1px solid #dcdfe4;
      background: #f8f9fb;
      color: #52525b;
      cursor: pointer;
      transition: background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
    }}
    .model-copy-btn svg {{
      width: 15px;
      height: 15px;
      stroke: currentColor;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .model-copy-btn.is-copied {{
      background: #e8f0ea;
      border-color: #b9d0be;
      color: #245c35;
    }}
    .model-card-main {{
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 0.8fr) minmax(0, 2.4fr);
      align-items: stretch;
    }}
    .model-meta {{
      background: #f7f7f8;
      border: 1px solid #ececef;
      border-radius: 16px;
      padding: 12px 13px;
      min-width: 0;
    }}
    .model-meta-label {{
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 6px;
    }}
    .model-meta-value {{
      display: block;
      font-size: 1rem;
      font-weight: 700;
      overflow-wrap: anywhere;
    }}
    .model-status {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      background: #f3f4f6;
      color: #4b5563;
      font-size: 0.84rem;
      font-weight: 700;
    }}
    .model-chart {{
      display: grid;
      gap: 10px;
      min-width: 0;
      background: #fcfcfc;
      border: 1px solid #ececef;
      border-radius: 16px;
      padding: 12px 13px;
    }}
    .model-chart-summary {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 0.86rem;
    }}
    .model-chart svg {{
      display: block;
      width: 100%;
      height: auto;
      aspect-ratio: 1000 / 165;
    }}
    .model-chart-grid {{
      stroke: #e7e7ea;
      stroke-width: 1;
    }}
    .model-chart-line {{
      fill: none;
      stroke: #2f2f35;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .model-chart-area {{
      fill: rgba(63, 63, 70, 0.1);
    }}
    .model-chart-point {{
      fill: #3f3f46;
    }}
    .model-chart-axis-label {{
      fill: #6b7280;
      font-size: 18px;
    }}
    .model-chart-y-label {{
      fill: #6b7280;
      font-size: 18px;
    }}
    .admin-model-card {{
      display: grid;
      gap: 18px;
      align-content: start;
    }}
    .admin-model-card h3 {{
      margin: 0;
    }}
    .admin-model-card label {{
      gap: 10px;
    }}
    .copy-row {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .copy-row-nowrap {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      min-width: 0;
      align-items: center;
    }}
    .copy-row code {{
      flex: 1 1 260px;
      display: inline-block;
      padding: 10px 12px;
      overflow-wrap: anywhere;
    }}
    .copy-row-nowrap code {{
      width: 100%;
      min-width: 0;
      white-space: nowrap;
      overflow-x: auto;
      overflow-y: hidden;
      overflow-wrap: normal;
    }}
    .copy-row-nowrap .copy-btn {{
      flex: 0 0 auto;
    }}
    .copy-btn {{
      background: var(--accent-soft);
      color: var(--ink);
      border: 1px solid var(--line);
    }}
    .section-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .section-head-main {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      min-width: 0;
    }}
    .section-head h2 {{
      margin: 0;
    }}
    .icon-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 38px;
      height: 38px;
      padding: 0;
      border-radius: 12px;
      background: var(--accent-soft);
      color: var(--ink);
      border: 1px solid var(--line);
    }}
    .icon-btn svg {{
      width: 18px;
      height: 18px;
      stroke: currentColor;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .icon-btn.is-loading svg {{
      animation: focusAwaySpin 0.85s linear infinite;
    }}
    @keyframes focusAwaySpin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    .hint {{
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .form-note {{
      margin-top: 8px;
      line-height: 1.55;
    }}
    .form-links {{
      margin-top: 10px;
    }}
    .table-wrap {{
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); font-size: 0.96rem; }}
    th {{ color: var(--muted); font-weight: 700; }}
    form {{ display: grid; gap: 14px; }}
    label {{ display: grid; gap: 8px; font-size: 0.95rem; }}
    input, button, select {{
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 11px 12px;
      font: inherit;
    }}
    button {{
      background: var(--accent);
      color: white;
      border: 0;
      cursor: pointer;
      font-weight: 700;
    }}
    button.secondary {{ background: var(--accent-soft); color: var(--ink); border: 1px solid var(--line); }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .pill {{
      display: inline-flex;
      width: fit-content;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line);
      background: #f8f9fa;
      color: var(--muted);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.88rem;
      font-weight: 600;
    }}
    .error {{ color: var(--danger); font-weight: 700; }}
    .success {{ color: var(--accent); font-weight: 700; }}
    .nav {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }}
    .topbar {{ display: flex; justify-content: flex-end; margin-bottom: 14px; }}
    .language-form {{ display: inline-flex; align-items: center; gap: 8px; }}
    .language-form label {{ display: inline-flex; align-items: center; gap: 8px; }}
    .language-form select {{ padding: 7px 10px; border-radius: 10px; background: #fff; }}
    code {{
      background: #f4f4f5;
      padding: 2px 6px;
      border-radius: 8px;
      font-family: "SF Mono", "Menlo", monospace;
    }}
    @media (max-width: 720px) {{
      .hero {{ display: block; }}
      .hero h1 {{ font-size: 2rem; }}
      .model-card-main {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <form class="language-form" method="post" action="/language">
        <label>{html.escape(labels["language"])}
          <select name="language" onchange="this.form.submit()">
            {language_options}
          </select>
        </label>
      </form>
    </div>
    {body}
    <footer class="footer">FocusAway v{APP_VERSION}, {APP_COPYRIGHT}</footer>
  </div>
  <script>
    function focusAwayCopyText(text) {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        return navigator.clipboard.writeText(text);
      }}
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.focus();
      area.select();
      document.execCommand("copy");
      document.body.removeChild(area);
      return Promise.resolve();
    }}

    function focusAwayCopyFromElement(elementId, button) {{
      const element = document.getElementById(elementId);
      if (!element) return;
      focusAwayCopyText(element.textContent || "").then(() => {{
        const original = button.textContent;
        button.textContent = {json.dumps(labels["copied"], ensure_ascii=False)};
        setTimeout(() => {{
          button.textContent = original;
        }}, 1400);
      }});
    }}

    function focusAwayCopyWithFlash(text, button) {{
      if (!button) return;
      focusAwayCopyText(text).then(() => {{
        button.classList.add("is-copied");
        window.clearTimeout(button._focusAwayCopyFlashTimer);
        button._focusAwayCopyFlashTimer = window.setTimeout(() => {{
          button.classList.remove("is-copied");
        }}, 1100);
      }});
    }}

    function focusAwayFillCurrentOrigin() {{
      document.querySelectorAll("[data-current-origin]").forEach((element) => {{
        const suffix = element.getAttribute("data-path-suffix") || "";
        element.textContent = window.location.origin + suffix;
      }});
    }}

    document.addEventListener("DOMContentLoaded", () => {{
      focusAwayFillCurrentOrigin();
    }});

    function focusAwaySelectChart(chartId, panelId, button) {{
      const root = document.getElementById(chartId);
      if (!root) return;
      root.querySelectorAll(".chart-panel").forEach((panel) => {{
        panel.hidden = panel.id !== panelId;
      }});
      root.querySelectorAll(".chart-tab").forEach((tab) => {{
        tab.style.background = "var(--accent-soft)";
        tab.style.color = "var(--ink)";
      }});
      button.style.background = "var(--accent)";
      button.style.color = "white";
    }}

    async function focusAwayRefreshDashboard(button, section) {{
      if (!button) return;
      const originalLabel = button.getAttribute("aria-label") || {json.dumps(labels["refresh"], ensure_ascii=False)};
      button.disabled = true;
      button.classList.add("is-loading");
      try {{
        const response = await fetch("/dashboard/refresh", {{
          method: "GET",
          headers: {{
            "Accept": "application/json"
          }},
          credentials: "same-origin"
        }});
        if (!response.ok) {{
          throw new Error("새로고침에 실패했습니다.");
        }}
        const payload = await response.json();
        if (section === "quota") {{
          const heading = document.getElementById("dashboard-quota-heading");
          if (heading && payload.quota_heading_html) heading.innerHTML = payload.quota_heading_html;
          const root = document.getElementById("dashboard-quota-content");
          if (root && payload.quota_html) root.innerHTML = payload.quota_html;
        }}
        if (section === "models") {{
          const root = document.getElementById("dashboard-models-content");
          if (root && payload.models_html) root.innerHTML = payload.models_html;
        }}
      }} catch (_error) {{
        button.setAttribute("aria-label", {json.dumps(labels["refresh_failed"], ensure_ascii=False)});
        setTimeout(() => button.setAttribute("aria-label", originalLabel), 1400);
      }} finally {{
        button.disabled = false;
        button.classList.remove("is-loading");
      }}
    }}
  </script>
</body>
</html>""".encode("utf-8")


class FocusAwayHandler(BaseHTTPRequestHandler):
    server_version = "FocusAway/0.1"
    protocol_version = "HTTP/1.1"
    DEFAULT_STREAM_CHUNK_SIZE = 1024
    PRIORITY_STREAM_CHUNK_SIZE = 256
    STREAM_CAPABLE_PATHS = {
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/responses",
    }

    @property
    def app(self) -> "FocusAwayApp":
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        try:
            self.route()
        except ValueError as exc:
            self.render_json({"error": {"message": str(exc)}}, 413)

    def do_POST(self) -> None:
        try:
            self.route()
        except ValueError as exc:
            self.render_json({"error": {"message": str(exc)}}, 413)

    def do_OPTIONS(self) -> None:
        self.handle_options()

    def log_message(self, format: str, *args) -> None:
        return

    def route(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.render_home()
        if parsed.path == "/signup" and self.command == "GET":
            return self.render_signup()
        if parsed.path == "/signup" and self.command == "POST":
            return self.handle_signup()
        if parsed.path == "/login" and self.command == "GET":
            return self.render_login()
        if parsed.path == "/login" and self.command == "POST":
            return self.handle_login()
        if parsed.path == "/language" and self.command == "POST":
            return self.handle_language_change()
        if parsed.path == "/terms":
            return self.render_terms()
        if parsed.path == "/privacy":
            return self.render_privacy()
        if parsed.path == "/logout" and self.command == "POST":
            return self.handle_logout()
        if parsed.path == "/dashboard":
            return self.render_dashboard()
        if parsed.path == "/dashboard/refresh" and self.command == "GET":
            return self.handle_dashboard_refresh()
        if parsed.path == "/admin" and self.command == "GET":
            return self.render_admin()
        if parsed.path == "/admin/settings" and self.command == "POST":
            return self.handle_admin_settings()
        if parsed.path == "/admin/tiers/create" and self.command == "POST":
            return self.handle_admin_tier_create()
        if parsed.path == "/admin/tiers/update" and self.command == "POST":
            return self.handle_admin_tier_update()
        if parsed.path == "/admin/tiers/move" and self.command == "POST":
            return self.handle_admin_tier_move()
        if parsed.path == "/admin/tiers/delete" and self.command == "POST":
            return self.handle_admin_tier_delete()
        if parsed.path == "/admin/grant" and self.command == "POST":
            return self.handle_admin_grant()
        if parsed.path == "/admin/models/refresh" and self.command == "POST":
            return self.handle_model_refresh()
        if parsed.path == "/admin/models/update" and self.command == "POST":
            return self.handle_model_update()
        if parsed.path == "/admin/users/tier" and self.command == "POST":
            return self.handle_admin_user_tier()
        if parsed.path == "/account/api-key/rotate" and self.command == "POST":
            return self.handle_rotate_api_key()
        if parsed.path == "/account/password" and self.command == "POST":
            return self.handle_password_change()
        if parsed.path == "/account/delete" and self.command == "POST":
            return self.handle_account_delete()
        if parsed.path == "/api/me":
            return self.render_json(self.current_user_payload())
        if parsed.path == "/health":
            return self.render_json({"ok": True, "app": self.app.config.app_name})
        if parsed.path == "/admin/users/suspend" and self.command == "POST":
            return self.handle_admin_user_suspend()
        if parsed.path == "/admin/users/delete" and self.command == "POST":
            return self.handle_admin_user_delete()
        if parsed.path == "/v1/models":
            return self.handle_models_api()
        if parsed.path.startswith("/v1/"):
            return self.handle_proxy_api(parsed.path)
        self.send_error(HTTPStatus.NOT_FOUND)

    def parse_body(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > self.app.config.max_request_bytes:
            raise ValueError("Request body too large.")
        raw = self.rfile.read(length) if length else b""
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(raw.decode("utf-8") or "{}")
        parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        result = {}
        for key, values in parsed.items():
            result[key] = values if len(values) > 1 else values[0]
        return result

    def apply_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        allowed = [item.strip() for item in self.app.config.cors_allowed_origins.split(",") if item.strip()]
        if not origin:
            return
        if "*" in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        elif origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            return
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Credentials", "false")

    def is_api_request(self) -> bool:
        parsed = urlparse(self.path)
        return parsed.path.startswith("/v1/") or parsed.path in {"/health", "/api/me"}

    def handle_options(self) -> None:
        if not self.is_api_request():
            self.send_response(204)
            self.end_headers()
            return
        self.send_response(204)
        self.apply_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def render_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if self.is_api_request():
            self.apply_cors_headers()
        self.apply_common_security_headers()
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)

    def redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Connection", "close")
        self.send_header("Location", location)
        self.end_headers()
        self.close_connection = True

    def current_session_user(self):
        cookie = SimpleCookie(self.headers.get("Cookie"))
        token = cookie.get("focusaway_session")
        if not token:
            return None
        user = self.app.db.get_user_by_session(token.value)
        if user:
            self.app.db.record_user_activity(user["id"], self.client_ip())
        return user

    def current_csrf_token(self) -> str:
        pending = getattr(self, "_pending_csrf_token", "")
        if pending:
            return pending
        cookie = SimpleCookie(self.headers.get("Cookie"))
        token = cookie.get("focusaway_csrf")
        return token.value if token else ""

    def request_is_secure(self) -> bool:
        forwarded_proto = self.headers.get("X-Forwarded-Proto", "")
        return forwarded_proto.lower() == "https"

    def client_ip(self) -> str:
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return self.client_address[0]

    def validate_csrf(self) -> bool:
        if not self.is_same_origin_request():
            return False
        cookie_token = self.current_csrf_token()
        if not cookie_token:
            return False
        form = self.parse_body()
        request_token = form.get("csrf_token", "")
        if isinstance(request_token, list):
            request_token = request_token[0] if request_token else ""
        if request_token != cookie_token:
            return False
        self._parsed_body = form
        return True

    def parsed_body(self) -> dict:
        cached = getattr(self, "_parsed_body", None)
        if cached is not None:
            delattr(self, "_parsed_body")
            return cached
        return self.parse_body()

    def is_same_origin_request(self) -> bool:
        expected_host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")
        expected_scheme = "https" if self.request_is_secure() else "http"
        origin = self.headers.get("Origin", "")
        referer = self.headers.get("Referer", "")

        source = origin or referer
        if not source:
            return True

        parsed = urlparse(source)
        return parsed.scheme == expected_scheme and parsed.netloc == expected_host

    def require_session_user(self):
        user = self.current_session_user()
        if not user:
            self.redirect("/login")
            return None
        return user

    def require_admin(self):
        user = self.require_session_user()
        if not user:
            return None
        if not user["is_admin"]:
            self.send_error(HTTPStatus.FORBIDDEN)
            return None
        return user

    def set_session_cookie(self, token: str) -> None:
        cookie = SimpleCookie()
        cookie["focusaway_session"] = token
        cookie["focusaway_session"]["path"] = "/"
        cookie["focusaway_session"]["httponly"] = True
        cookie["focusaway_session"]["samesite"] = "Lax"
        if self.request_is_secure():
            cookie["focusaway_session"]["secure"] = True
        self.send_header("Set-Cookie", cookie.output(header="").strip())

    def set_csrf_cookie(self, token: str) -> None:
        cookie = SimpleCookie()
        cookie["focusaway_csrf"] = token
        cookie["focusaway_csrf"]["path"] = "/"
        cookie["focusaway_csrf"]["samesite"] = "Lax"
        if self.request_is_secure():
            cookie["focusaway_csrf"]["secure"] = True
        self.send_header("Set-Cookie", cookie.output(header="").strip())

    def clear_session_cookie(self) -> None:
        cookie = SimpleCookie()
        cookie["focusaway_session"] = ""
        cookie["focusaway_session"]["path"] = "/"
        cookie["focusaway_session"]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        self.send_header("Set-Cookie", cookie.output(header="").strip())
        csrf_cookie = SimpleCookie()
        csrf_cookie["focusaway_csrf"] = ""
        csrf_cookie["focusaway_csrf"]["path"] = "/"
        csrf_cookie["focusaway_csrf"]["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
        self.send_header("Set-Cookie", csrf_cookie.output(header="").strip())

    def current_language(self) -> str:
        cookie = SimpleCookie(self.headers.get("Cookie"))
        saved = cookie.get("focusaway_language")
        if saved and saved.value in LANGUAGE_OPTIONS:
            return saved.value
        accept_language = self.headers.get("Accept-Language", "")
        return "ko" if accept_language.lower().startswith("ko") else "en"

    def t(self, key: str, **values) -> str:
        text = TEXT.get(self.current_language(), TEXT["en"]).get(key, key)
        return text.format(**values)

    def set_language_cookie(self, language: str) -> None:
        cookie = SimpleCookie()
        cookie["focusaway_language"] = language if language in LANGUAGE_OPTIONS else "en"
        cookie["focusaway_language"]["path"] = "/"
        cookie["focusaway_language"]["max-age"] = str(60 * 60 * 24 * 365 * 5)
        cookie["focusaway_language"]["samesite"] = "Lax"
        if self.request_is_secure():
            cookie["focusaway_language"]["secure"] = True
        self.send_header("Set-Cookie", cookie.output(header="").strip())

    def handle_language_change(self) -> None:
        if not self.is_same_origin_request():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parse_body()
        language = str(form.get("language", "")).strip()
        if language not in LANGUAGE_OPTIONS:
            language = "en"
        referer = self.headers.get("Referer", "")
        location = "/"
        if referer:
            parsed = urlparse(referer)
            if parsed.netloc == (self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")):
                location = parsed.path or "/"
        self.send_response(302)
        self.set_language_cookie(language)
        self.send_header("Connection", "close")
        self.send_header("Location", location)
        self.end_headers()
        self.close_connection = True

    def render_csrf_input(self) -> str:
        token = self.current_csrf_token()
        if not token:
            token = generate_token("csrf")
            self._pending_csrf_token = token
        return f'<input type="hidden" name="csrf_token" value="{html.escape(token)}">'

    def maybe_refresh_csrf_cookie(self) -> None:
        token = self.current_csrf_token()
        if token:
            self.set_csrf_cookie(token)
            return
        pending = getattr(self, "_pending_csrf_token", "")
        if pending:
            self.set_csrf_cookie(pending)
            return
        user = self.current_session_user()
        if user:
            token = generate_token("csrf")
            self._pending_csrf_token = token
            self.set_csrf_cookie(token)

    def apply_common_security_headers(self) -> None:
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
        )

    def render_home(self) -> None:
        user = self.current_session_user()
        if user:
            return self.redirect("/dashboard")
        signup_link = f'<a href="/signup">{html.escape(self.t("signup"))}</a>' if self.signup_open() else ""
        subtitle = "FocusAway 웹 패널과 사용자 API 키를 관리할 수 있습니다." if self.current_language() == "ko" else "Manage the FocusAway web panel and user API keys."
        body = f"""
        <div class="hero">
          <div><h1>{html.escape(self.t("login"))}</h1><p>{html.escape(subtitle)}</p></div>
          <div class="row">{signup_link}</div>
        </div>
        <section class="card">
          <form method="post" action="/login">
            {self.render_csrf_input()}
            <label>{html.escape(self.t("username"))}<input type="text" name="username" pattern="[a-z0-9]+" required></label>
            <label>{html.escape(self.t("password"))}<input type="password" name="password" required></label>
            <button type="submit">{html.escape(self.t("login"))}</button>
          </form>
        </section>
        """
        self.respond_html("FocusAway", body)

    def render_signup(self, error: str = "") -> None:
        if not self.signup_open():
            return self.render_signup_closed()
        error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
        subtitle = "처음 생성되는 계정은 관리자 권한을 가집니다." if self.current_language() == "ko" else "The first account created becomes the administrator."
        username_hint = "아이디는 영어 소문자와 숫자만 사용할 수 있습니다." if self.current_language() == "ko" else "Usernames may contain lowercase English letters and numbers only."
        body = f"""
        <div class="hero">
          <div><h1>{html.escape(self.t("signup"))}</h1><p>{html.escape(subtitle)}</p></div>
          <div class="row"><a href="/login">{html.escape(self.t("already_have_account"))}</a></div>
        </div>
        <section class="card">
          {error_html}
          <form method="post" action="/signup">
            {self.render_csrf_input()}
            <label>{html.escape(self.t("username"))}<input type="text" name="username" pattern="[a-z0-9]+" required></label>
            <label>{html.escape(self.t("password"))}<input type="password" name="password" minlength="8" required></label>
            <button type="submit">{html.escape(self.t("create_account"))}</button>
          </form>
          <p class="hint form-note">{html.escape(username_hint)}</p>
          <div class="row form-links">
            <a href="/terms">{html.escape(self.t("terms"))}</a>
            <a href="/privacy">{html.escape(self.t("privacy"))}</a>
          </div>
        </section>
        """
        self.respond_html(self.t("signup"), body)

    def render_signup_closed(self) -> None:
        body = """
        <div class="hero">
          <div><h1>회원가입 불가</h1><p>현재는 신규 회원가입을 받고 있지 않습니다.</p></div>
          <div class="row"><a href="/login">로그인으로 돌아가기</a></div>
        </div>
        <section class="card">
          <p>관리자가 회원가입을 다시 열기 전까지 새 계정을 만들 수 없습니다.</p>
        </section>
        """
        self.respond_html("회원가입 불가", body)

    def handle_signup(self) -> None:
        if not self.is_same_origin_request():
            return self.send_error(HTTPStatus.FORBIDDEN)
        if not self.signup_open():
            return self.render_signup_closed()
        form = self.parse_body()
        username = form.get("username", "").strip()
        password = form.get("password", "")
        if not self.app.db.username_is_valid(username) or not password or len(password) < 8:
            return self.render_signup("아이디는 영어 소문자와 숫자만 사용할 수 있으며, 비밀번호는 8자 이상이어야 합니다.")
        try:
            user = self.app.db.create_user(username, password)
        except ValueError as exc:
            if str(exc) == "invalid_username":
                return self.render_signup("아이디는 영어 소문자와 숫자만 사용할 수 있습니다.")
            raise
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                return self.render_signup("이미 사용 중인 아이디입니다.")
            raise
        token = self.app.db.create_session(user["id"])
        csrf_token = generate_token("csrf")
        self.send_response(302)
        self.set_session_cookie(token)
        self.set_csrf_cookie(csrf_token)
        self.send_header("Location", "/dashboard")
        self.end_headers()

    def render_login(self, error: str = "") -> None:
        error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
        signup_link = f'<a href="/signup">{html.escape(self.t("signup"))}</a>' if self.signup_open() else ""
        subtitle = "FocusAway 웹 패널과 사용자 API 키를 관리할 수 있습니다." if self.current_language() == "ko" else "Manage the FocusAway web panel and user API keys."
        body = f"""
        <div class="hero">
          <div><h1>{html.escape(self.t("login"))}</h1><p>{html.escape(subtitle)}</p></div>
          <div class="row">{signup_link}</div>
        </div>
        <section class="card">
          {error_html}
          <form method="post" action="/login">
            <label>{html.escape(self.t("username"))}<input type="text" name="username" pattern="[a-z0-9]+" required></label>
            <label>{html.escape(self.t("password"))}<input type="password" name="password" required></label>
            <button type="submit">{html.escape(self.t("login"))}</button>
          </form>
        </section>
        """
        self.respond_html(self.t("login"), body)

    def render_terms(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        operator_name = html.escape(self.app.config.operator_name)
        contact_email = html.escape(self.app.config.contact_email or "미설정")
        if self.current_language() == "en":
            contact_email = html.escape(self.app.config.contact_email or "Not set")
            body = f"""
            <div class="hero">
              <div><h1>Terms of Service</h1><p>Basic terms for the {html.escape(self.app.config.app_name)} service.</p></div>
              <div class="row"><a href="/signup">Back to Sign Up</a></div>
            </div>
            <section class="card">
              <p class="hint">Effective date: {today}</p>
              <h2>1. Purpose</h2>
              <p>These terms define the conditions, rights, obligations, and responsibilities between {operator_name} and users of {html.escape(self.app.config.app_name)}.</p>
              <h2>2. Service</h2>
              <p>The operator provides an AI model middleware service, including the web panel, per-user API keys, model access controls, and request balance management.</p>
              <h2>3. Accounts</h2>
              <p>Users become members by agreeing to these terms and the privacy policy and completing signup. Members must protect their account information and API keys.</p>
              <h2>4. Prohibited Conduct</h2>
              <p>Users must not violate applicable law, infringe others' rights, disrupt service stability, attempt unauthorized access, perform abnormal bulk calls, or interfere with operations.</p>
              <h2>5. Restrictions</h2>
              <p>The operator may restrict or terminate use if a member violates these terms, applicable law, or materially disrupts service operation.</p>
              <h2>6. Account Deletion</h2>
              <p>Regular members may delete their account from the web panel. Information required by law or internal policy may be retained for the required period.</p>
              <h2>7. Disclaimer</h2>
              <p>The operator is not responsible for failures caused by force majeure, system failures, external network issues, or third-party service outages, and does not guarantee output accuracy or fitness for a particular purpose.</p>
              <h2>8. Changes</h2>
              <p>The operator may revise these terms to reflect legal or service changes and will notify users through the web panel or another available channel.</p>
              <h2>9. Contact</h2>
              <p>Terms contact: {contact_email}</p>
            </section>
            """
            self.respond_html("Terms of Service", body)
            return
        body = f"""
        <div class="hero">
          <div><h1>이용약관</h1><p>{html.escape(self.app.config.app_name)} 서비스 기본 이용약관입니다.</p></div>
          <div class="row"><a href="/signup">회원가입으로 돌아가기</a></div>
        </div>
        <section class="card">
          <p class="hint">시행일: {today}</p>
          <h2>제1조 목적</h2>
          <p>본 약관은 {html.escape(self.app.config.app_name)} 서비스를 제공하는 {operator_name}(이하 "운영자")와 이용자 간의 서비스 이용조건, 권리·의무 및 책임사항을 정하는 것을 목적으로 합니다.</p>
          <h2>제2조 서비스 내용</h2>
          <p>운영자는 회원에게 웹 패널, 사용자별 API 키, 모델 접근 제어, 요청량 관리 기능 등 인공지능 모델 중계 서비스를 제공합니다.</p>
          <h2>제3조 회원가입 및 계정</h2>
          <p>이용자는 본 약관 및 개인정보처리방침에 동의하고 회원가입 절차를 완료함으로써 회원이 됩니다. 회원은 자신의 계정정보와 API 키를 스스로 관리해야 하며, 이를 제3자에게 공유해서는 안 됩니다.</p>
          <h2>제4조 금지행위</h2>
          <p>회원은 관계 법령에 위반되는 행위, 타인의 권리 침해, 서비스 안정성 저해, 무단 접근 시도, 비정상적 대량 호출, 운영 방해 행위를 해서는 안 됩니다.</p>
          <h2>제5조 서비스 이용 제한</h2>
          <p>운영자는 회원이 약관 또는 관련 법령을 위반하거나 서비스 운영을 현저히 방해하는 경우 사전 통지 후 또는 긴급한 경우 사후 통지로 서비스 이용을 제한하거나 회원 자격을 정지·해지할 수 있습니다.</p>
          <h2>제6조 회원 탈퇴</h2>
          <p>일반 회원은 웹 패널에서 직접 탈퇴할 수 있습니다. 다만 관계 법령 또는 내부 운영정책상 보관이 필요한 정보는 해당 기간 동안 별도로 보관될 수 있습니다.</p>
          <h2>제7조 면책</h2>
          <p>운영자는 천재지변, 시스템 장애, 외부 네트워크 문제, 제3자 서비스 장애 등 불가항력 사유로 서비스를 제공할 수 없는 경우 책임을 지지 않습니다. 운영자는 제공 결과물의 정확성, 완전성, 특정 목적 적합성을 보증하지 않습니다.</p>
          <h2>제8조 약관 변경</h2>
          <p>운영자는 법령 또는 서비스 변경 사항을 반영하기 위해 약관을 수정할 수 있으며, 변경 시 웹 패널 또는 공지 가능한 수단을 통해 고지합니다.</p>
          <h2>제9조 문의</h2>
          <p>이용약관 관련 문의처: {contact_email}</p>
        </section>
        """
        self.respond_html("이용약관", body)

    def render_privacy(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        operator_name = html.escape(self.app.config.operator_name)
        contact_email = html.escape(self.app.config.contact_email or "미설정")
        contact_address = html.escape(self.app.config.contact_address or "미설정")
        if self.current_language() == "en":
            contact_email = html.escape(self.app.config.contact_email or "Not set")
            contact_address = html.escape(self.app.config.contact_address or "Not set")
            body = f"""
            <div class="hero">
              <div><h1>Privacy Policy</h1><p>How {html.escape(self.app.config.app_name)} handles personal information.</p></div>
              <div class="row"><a href="/signup">Back to Sign Up</a></div>
            </div>
            <section class="card">
              <p class="hint">Effective date: {today}</p>
              <h2>1. Purpose of Processing</h2>
              <p>{operator_name} processes personal information for user identification, login authentication, API key issuance, service delivery, access restriction management, support, security, and abuse prevention.</p>
              <h2>2. Information Processed</h2>
              <p>Required items include username, password hash, session information, per-user API key, and service usage records such as model usage, request time, and charged amount. Access logs and error logs may also be generated during operation.</p>
              <h2>3. Retention Period</h2>
              <p>Member information is retained until account deletion, unless applicable law requires a separate retention period.</p>
              <h2>4. Third-Party Provision</h2>
              <p>The operator does not provide personal information to third parties except where required by law or separately consented to by the user.</p>
              <h2>5. Outsourcing</h2>
              <p>The operator does not currently outsource personal information processing. Future outsourcing, if any, will be disclosed in this policy.</p>
              <h2>6. User Rights</h2>
              <p>Users may request access, correction, deletion, or suspension of processing through service features or the contact information below.</p>
              <h2>7. Deletion</h2>
              <p>Personal information is deleted without delay when the retention period ends or the processing purpose is fulfilled. Electronic files are deleted in a difficult-to-recover manner.</p>
              <h2>8. Safeguards</h2>
              <p>The operator applies reasonable safeguards, including password hashing, separate account API keys, access control, log retention, and minimal collection.</p>
              <h2>9. Contact</h2>
              <p>Operator: {operator_name}</p>
              <p>Email: {contact_email}</p>
              <p>Address: {contact_address}</p>
              <h2>10. Changes</h2>
              <p>This policy may be revised due to legal, service, or internal policy changes, and updates will be announced through the web panel or another available channel.</p>
            </section>
            """
            self.respond_html("Privacy Policy", body)
            return
        body = f"""
        <div class="hero">
          <div><h1>개인정보처리방침</h1><p>{html.escape(self.app.config.app_name)} 서비스의 개인정보 처리 기준입니다.</p></div>
          <div class="row"><a href="/signup">회원가입으로 돌아가기</a></div>
        </div>
        <section class="card">
          <p class="hint">시행일: {today}</p>
          <h2>1. 개인정보 처리 목적</h2>
          <p>{operator_name}는 회원 식별, 로그인 인증, API 키 발급, 서비스 제공, 이용 제한 관리, 문의 대응, 보안 및 부정사용 방지를 위해 개인정보를 처리합니다.</p>
          <h2>2. 처리하는 개인정보 항목</h2>
          <p>필수 항목: 아이디, 비밀번호 해시값, 세션 정보, 사용자별 API 키, 서비스 이용기록(모델 사용 기록, 요청 시각, 차감량). 서비스 운영 과정에서 접속 로그 및 오류 로그가 추가로 생성될 수 있습니다.</p>
          <h2>3. 개인정보의 처리 및 보유 기간</h2>
          <p>회원 개인정보는 회원 탈퇴 시까지 보유합니다. 다만 관계 법령에 따라 보존이 필요한 경우 해당 법령에서 정한 기간 동안 별도 보관할 수 있습니다.</p>
          <h2>4. 개인정보의 제3자 제공</h2>
          <p>운영자는 원칙적으로 이용자의 개인정보를 외부에 제공하지 않습니다. 다만 법령상 근거가 있거나 이용자의 별도 동의가 있는 경우에 한해 제공합니다.</p>
          <h2>5. 개인정보 처리의 위탁</h2>
          <p>운영자는 현재 개인정보 처리 업무를 외부에 위탁하지 않습니다. 향후 위탁이 발생하는 경우 관련 사항을 본 방침에 공개합니다.</p>
          <h2>6. 이용자와 법정대리인의 권리</h2>
          <p>이용자는 자신의 개인정보 열람, 정정, 삭제, 처리정지 요구를 할 수 있으며, 서비스 내 기능 또는 아래 문의처를 통해 요청할 수 있습니다.</p>
          <h2>7. 개인정보 파기 절차 및 방법</h2>
          <p>개인정보 보유기간이 종료되거나 처리 목적이 달성된 경우 지체 없이 파기합니다. 전자적 파일은 복구가 어려운 방식으로 삭제하며, 별도 출력물은 분쇄 또는 소각 등의 방식으로 파기합니다.</p>
          <h2>8. 개인정보의 안전성 확보조치</h2>
          <p>운영자는 비밀번호 해시 저장, 계정별 API 키 분리, 접근권한 관리, 로그 보존, 최소한의 개인정보 수집 등 합리적인 안전성 확보조치를 시행합니다.</p>
          <h2>9. 개인정보 보호책임자 및 문의처</h2>
          <p>운영자: {operator_name}</p>
          <p>이메일: {contact_email}</p>
          <p>주소: {contact_address}</p>
          <h2>10. 방침 변경</h2>
          <p>본 개인정보처리방침은 법령, 서비스 내용 또는 내부 운영정책 변경에 따라 수정될 수 있으며, 변경 시 웹 패널 또는 공지 가능한 수단을 통해 안내합니다.</p>
        </section>
        """
        self.respond_html("개인정보처리방침", body)

    def handle_login(self) -> None:
        if not self.is_same_origin_request():
            return self.send_error(HTTPStatus.FORBIDDEN)
        client_ip = self.client_ip()
        if not self.app.allow_login_attempt(client_ip):
            return self.render_login("로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        form = self.parse_body()
        user = self.app.db.authenticate_user(form.get("username", ""), form.get("password", ""))
        if not user:
            self.app.record_login_failure(client_ip)
            return self.render_login("아이디 또는 비밀번호가 올바르지 않거나 계정이 정지되었습니다.")
        self.app.clear_login_failures(client_ip)
        self.app.db.record_user_activity(user["id"], client_ip)
        token = self.app.db.create_session(user["id"])
        csrf_token = generate_token("csrf")
        self.send_response(302)
        self.set_session_cookie(token)
        self.set_csrf_cookie(csrf_token)
        self.send_header("Location", "/dashboard")
        self.end_headers()

    def handle_logout(self) -> None:
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        cookie = SimpleCookie(self.headers.get("Cookie"))
        token = cookie.get("focusaway_session")
        if token:
            self.app.db.delete_session(token.value)
        self.send_response(302)
        self.clear_session_cookie()
        self.send_header("Location", "/")
        self.end_headers()

    def render_dashboard(self) -> None:
        user = self.require_session_user()
        if not user:
            return
        data = self.app.db.dashboard_payload_for_user(user["id"])
        usage = self.app.db.recent_usage_for_user(user["id"])
        usage_series_daily = self.app.db.usage_series_for_user(user["id"], days=7)
        usage_series_hourly = self.app.db.usage_hourly_series_for_user(user["id"], hours=24)
        model_usage_series = self.app.live_model_usage_series(hours=24)
        usage_chart = self.render_usage_chart_switcher(usage_series_hourly, usage_series_daily)
        usage_rows = "".join(
            f"<tr><td>{html.escape(item['model_id'])}</td><td>{html.escape(item['endpoint'])}</td><td>{item['cost']:.2f}</td><td>{html.escape(self.format_usage_timestamp(item['created_at']))}</td></tr>"
            for item in usage
        ) or f"<tr><td colspan='4'>{html.escape(self.t('no_usage'))}</td></tr>"
        admin_link = f'<a href="/admin">{html.escape(self.t("admin_panel"))}</a>' if user["is_admin"] else ""
        dashboard_subtitle = (
            f"{user['username']}님, 현재 사용 가능한 모델과 계정 상태를 확인할 수 있습니다."
            if self.current_language() == "ko"
            else f"{user['username']}, you can review your available models and account status."
        )
        api_hint = (
            "대부분의 OpenAI 호환 프론트엔드는 위 첫 번째 주소를 입력하면 내부적으로 /v1를 붙여 사용합니다."
            if self.current_language() == "ko"
            else "Most OpenAI-compatible frontends add /v1 internally when you enter the first URL above."
        )
        delete_confirm = (
            "정말로 계정을 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다."
            if self.current_language() == "ko"
            else "Are you sure you want to delete your account? This cannot be undone."
        )
        delete_account_form = ""
        if not user["is_admin"]:
            delete_account_form = f"""
          <form method="post" action="/account/delete" onsubmit="return confirm({html.escape(json.dumps(delete_confirm))});">
            {self.render_csrf_input()}
            <button class="secondary" type="submit">{html.escape(self.t("delete_account"))}</button>
          </form>
          """
        account_actions = f"""
        <section class="card">
          <h2>{html.escape(self.t("account"))}</h2>
          <form method="post" action="/account/password">
            {self.render_csrf_input()}
            <label>{html.escape(self.t("current_password"))}<input type="password" name="current_password" required></label>
            <label>{html.escape(self.t("new_password"))}<input type="password" name="new_password" minlength="8" required></label>
            <button type="submit">{html.escape(self.t("change_password"))}</button>
          </form>
          {delete_account_form}
        </section>
        """
        body = f"""
        <section class="hero">
          <div class="hero-copy">
            <h1>{html.escape(self.t("dashboard"))}</h1>
            <p>{html.escape(dashboard_subtitle)}</p>
          </div>
          <div class="row">
            {admin_link}
            <form method="post" action="/logout">{self.render_csrf_input()}<button class="secondary" type="submit">{html.escape(self.t("logout"))}</button></form>
          </div>
        </section>
        <section class="grid">
          <article class="card">
            <div class="section-head">
              <div id="dashboard-quota-heading" class="section-head-main">{self.render_dashboard_quota_heading(data["user"])}</div>
              <button class="icon-btn" type="button" aria-label="{html.escape(self.t("refresh"))}" onclick="focusAwayRefreshDashboard(this, 'quota')">{self.refresh_icon_svg()}</button>
            </div>
            <div id="dashboard-quota-content">{self.render_dashboard_quota_content(data, usage_chart)}</div>
          </article>
          <article class="card">
            <h2>{html.escape(self.t("my_api_key"))}</h2>
            <div class="stack">
              <div>
                <p class="hint">{html.escape(self.t("api_key"))}</p>
                <div class="copy-row copy-row-nowrap">
                  <code id="user-api-key">{html.escape(user['api_key'])}</code>
                  <button class="copy-btn" type="button" onclick="focusAwayCopyFromElement('user-api-key', this)">{html.escape(self.t("copy"))}</button>
                </div>
              </div>
              <div>
                <p class="hint">{html.escape(self.t("api_base"))}</p>
                <div class="copy-row copy-row-nowrap">
                  <code id="user-api-base" data-current-origin data-path-suffix="">{html.escape(self.t("loading"))}</code>
                  <button class="copy-btn" type="button" onclick="focusAwayCopyFromElement('user-api-base', this)">{html.escape(self.t("copy"))}</button>
                </div>
              </div>
              <div>
                <p class="hint">{html.escape(self.t("api_root"))}</p>
                <div class="copy-row copy-row-nowrap">
                  <code id="user-api-v1-base" data-current-origin data-path-suffix="/v1">{html.escape(self.t("loading"))}</code>
                  <button class="copy-btn" type="button" onclick="focusAwayCopyFromElement('user-api-v1-base', this)">{html.escape(self.t("copy"))}</button>
                </div>
              </div>
            </div>
            <p>{html.escape(api_hint).replace('/v1', '<code>/v1</code>')}</p>
            <form method="post" action="/account/api-key/rotate">{self.render_csrf_input()}<button type="submit">{html.escape(self.t("rotate_api_key"))}</button></form>
          </article>
        </section>
        <section class="card">
          <div class="section-head">
            <h2>{html.escape(self.t("models"))}</h2>
            <button class="icon-btn" type="button" aria-label="{html.escape(self.t("refresh"))}" onclick="focusAwayRefreshDashboard(this, 'models')">{self.refresh_icon_svg()}</button>
          </div>
          <div id="dashboard-models-content">{self.render_dashboard_models_content(data["models"], usage_series_hourly, model_usage_series)}</div>
        </section>
        <section class="card">
          <h2>{html.escape(self.t("recent_usage"))}</h2>
          <div class="table-wrap">
            <table><thead><tr><th>{html.escape(self.t("model"))}</th><th>{html.escape(self.t("endpoint"))}</th><th>{html.escape(self.t("cost"))}</th><th>{html.escape(self.t("time"))}</th></tr></thead><tbody>{usage_rows}</tbody></table>
          </div>
        </section>
        {account_actions}
        """
        self.respond_html(self.t("dashboard"), body)

    def handle_dashboard_refresh(self) -> None:
        user = self.require_session_user()
        if not user:
            return
        data = self.app.db.dashboard_payload_for_user(user["id"])
        usage_series_daily = self.app.db.usage_series_for_user(user["id"], days=7)
        usage_series_hourly = self.app.db.usage_hourly_series_for_user(user["id"], hours=24)
        model_usage_series = self.app.live_model_usage_series(hours=24)
        usage_chart = self.render_usage_chart_switcher(usage_series_hourly, usage_series_daily)
        self.render_json(
            {
                "quota_heading_html": self.render_dashboard_quota_heading(data["user"]),
                "quota_html": self.render_dashboard_quota_content(data, usage_chart),
                "models_html": self.render_dashboard_models_content(data["models"], usage_series_hourly, model_usage_series),
            }
        )

    def render_dashboard_quota_heading(self, user: dict) -> str:
        if user["is_admin"]:
            return f"<h2>{html.escape(self.t('admin_privileges'))}</h2>"
        tier_name = (user.get("tier_name") or "").strip() or self.t("unassigned")
        return (
            f"<h2>{html.escape(self.t('remaining_premium'))}</h2>"
            f"<span class=\"pill\">{html.escape(tier_name)}</span>"
        )

    def format_usage_timestamp(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return "-"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return text.split(".", 1)[0]
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    def render_dashboard_quota_content(self, data: dict, usage_chart: str) -> str:
        user = data["user"]
        if user["is_admin"]:
            admin_text = (
                "<p>관리자 계정은 모든 모델을 프리미엄 요청 차감 없이 사용할 수 있습니다.</p>"
                "<p>관리자 계정에는 주간 잔액과 보너스 잔액이 적용되지 않습니다.</p>"
                if self.current_language() == "ko"
                else "<p>Admin accounts can use all models without premium-request charges.</p><p>Weekly and bonus balances do not apply to admin accounts.</p>"
            )
            return (
                f"<div class=\"metric\">{html.escape(self.t('unlimited'))}</div>"
                f"{admin_text}"
            )
        return (
            f"<div class=\"metric\">{user['weekly_balance'] + user['bonus_balance']:.2f}</div>"
            f"<p>{html.escape(self.t('weekly_balance'))}: {user['weekly_balance']:.2f}</p>"
            f"<p>{html.escape(self.t('bonus_balance'))}: {user['bonus_balance']:.2f}</p>"
            f"<p>{html.escape(self.t('weekly_quota'))}: {data['weekly_quota']:.2f}</p>"
            f"{usage_chart}"
        )

    def render_dashboard_models_content(self, models: list[dict], usage_series_hourly: list[dict], model_usage_series: dict[str, list[dict]]) -> str:
        max_model_calls = max(
            (max((int(point["count"]) for point in series), default=0) for series in model_usage_series.values()),
            default=0,
        )
        model_cards = "".join(
            (
                f"<article class=\"model-card\">"
                f"<div class=\"model-card-head\">"
                f"<div class=\"model-card-title\">"
                f"<h3>{html.escape(model['display_name'])}</h3>"
                f"{self.render_model_access_badge(model)}"
                f"{self.render_model_copy_button(model['display_name'])}"
                f"</div>"
                f"{self.render_model_kind_badge(self.effective_model_kind(model))}"
                f"</div>"
                f"<div class=\"model-card-main\">"
                f"<div class=\"model-meta\"><span class=\"model-meta-label\">{html.escape(self.t('context_window'))}</span><span class=\"model-meta-value\">{self.format_token_count(self.effective_model_limit(model, 'context_window', 'custom_context_window'))}</span></div>"
                f"<div class=\"model-meta\"><span class=\"model-meta-label\">{html.escape(self.t('output_token_limit'))}</span><span class=\"model-meta-value\">{self.format_token_count(self.effective_model_limit(model, 'max_output_tokens', 'custom_max_output_tokens'))}</span></div>"
                f"<div class=\"model-meta\"><span class=\"model-meta-label\">{html.escape(self.t('cost_per_request'))}</span><span class=\"model-meta-value\">{float(model['cost_per_request']):.2f}</span></div>"
                f"{self.render_model_calls_chart(model_usage_series.get(model['model_id'], []), usage_series_hourly, max_model_calls, model['model_id'])}"
                f"</div>"
                f"</article>"
            )
            for model in models
        ) or f"<p>{html.escape(self.t('no_models'))}</p>"
        return f'<div class="model-grid">{model_cards}</div>'

    def refresh_icon_svg(self) -> str:
        return """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M21 12a9 9 0 0 1-15.36 6.36"></path>
          <path d="M3 12A9 9 0 0 1 18.36 5.64"></path>
          <path d="M18 3v4h-4"></path>
          <path d="M6 21v-4h4"></path>
        </svg>
        """

    def arrow_up_icon_svg(self) -> str:
        return """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 18V6"></path>
          <path d="M7 11l5-5 5 5"></path>
        </svg>
        """

    def arrow_down_icon_svg(self) -> str:
        return """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 6v12"></path>
          <path d="M7 13l5 5 5-5"></path>
        </svg>
        """

    def trash_icon_svg(self) -> str:
        return """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 7h16"></path>
          <path d="M9 7V5h6v2"></path>
          <path d="M7 7l1 12h8l1-12"></path>
          <path d="M10 11v5"></path>
          <path d="M14 11v5"></path>
        </svg>
        """

    def copy_icon_svg(self) -> str:
        return """
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 14V6.5A1.5 1.5 0 0 1 8.5 5H14"></path>
          <rect x="9" y="7" width="8" height="12" rx="1.5"></rect>
        </svg>
        """

    def render_model_kind_badge(self, model_kind: str) -> str:
        kind = (model_kind or "").strip().upper()
        if kind not in {"LLM", "VLM"}:
            return ""
        return f'<span class="model-kind">{html.escape(kind)}</span>'

    def render_model_access_badge(self, model: dict) -> str:
        minimum_tier_name = (model.get("minimum_tier_name") or "").strip()
        if minimum_tier_name:
            return f'<span class="model-access-badge">{html.escape(self.t("tier_or_higher", name=minimum_tier_name))}</span>'
        return f'<span class="model-access-badge">{html.escape(self.admin_tier_label())}</span>'

    def render_model_copy_button(self, display_name: str) -> str:
        encoded_name = html.escape(json.dumps(str(display_name)))
        return (
            f'<button class="model-copy-btn" type="button" '
            f'aria-label="{html.escape(self.t("model_name_copy"))}" title="{html.escape(self.t("model_name_copy"))}" '
            f'onclick="focusAwayCopyWithFlash({encoded_name}, this)">{self.copy_icon_svg()}</button>'
        )

    def effective_model_kind(self, model) -> str:
        custom_kind = (model.get("custom_model_kind") or "").strip().upper()
        if custom_kind in {"LLM", "VLM"}:
            return custom_kind
        base_kind = (model.get("model_kind") or "").strip().upper()
        return base_kind if base_kind in {"LLM", "VLM"} else ""

    def effective_model_limit(self, model, default_key: str, custom_key: str):
        custom_value = model[custom_key]
        return custom_value if custom_value not in (None, "", 0) else model[default_key]

    def format_token_count(self, value) -> str:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return "-"
        if number <= 0:
            return "-"
        if number >= 1_000_000:
            scaled = number / 1_000_000
            suffix = "M"
        elif number >= 10_000:
            scaled = number / 1_000
            suffix = "K"
        else:
            return str(number)
        if scaled >= 100 or float(scaled).is_integer():
            return f"{int(round(scaled))}{suffix}"
        return f"{scaled:.1f}{suffix}"

    def render_model_calls_chart(self, usage_series: list[dict], baseline_series: list[dict], max_count: int, model_id: str) -> str:
        if not usage_series:
            usage_series = [{"label": item["label"], "count": 0} for item in baseline_series]
        scale_max = max(max_count, 1)
        width = 1000
        height = 220
        padding_left = 56
        padding_right = 16
        padding_top = 16
        padding_bottom = 34
        usable_width = width - padding_left - padding_right
        usable_height = height - padding_top - padding_bottom
        step_x = usable_width / max(len(usage_series) - 1, 1)
        points = []
        for index, item in enumerate(usage_series):
            count = int(item.get("count", 0))
            x = padding_left + index * step_x
            y = padding_top + usable_height - ((count / scale_max) * usable_height if scale_max else 0)
            points.append((x, y, count))

        polyline_points = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
        area_points = f"{padding_left:.2f},{padding_top + usable_height:.2f} " + polyline_points + f" {padding_left + usable_width:.2f},{padding_top + usable_height:.2f}"
        circles = "".join(
            f'<circle class="model-chart-point" cx="{x:.2f}" cy="{y:.2f}" r="3"><title>{html.escape(usage_series[index]["label"])}: {count}</title></circle>'
            for index, (x, y, count) in enumerate(points)
        )
        grid_lines = "".join(
            f'<line class="model-chart-grid" x1="{padding_left}" y1="{padding_top + usable_height * ratio:.2f}" x2="{padding_left + usable_width}" y2="{padding_top + usable_height * ratio:.2f}"></line>'
            for ratio in (0, 0.5, 1)
        )
        axis_labels = []
        for index, (x, _, _) in enumerate(points):
            if index not in (0, 6, 12, 18, len(points) - 1):
                continue
            anchor = "middle"
            if index == 0:
                anchor = "start"
            elif index == len(points) - 1:
                anchor = "end"
            axis_labels.append(
                f'<text class="model-chart-axis-label" x="{x:.2f}" y="{height - 6}" text-anchor="{anchor}">{html.escape(usage_series[index]["label"])}</text>'
            )
        mid_value = int(round(scale_max / 2))
        y_axis_labels = []
        for y, value in (
            (padding_top, scale_max),
            (padding_top + usable_height / 2, mid_value),
            (padding_top + usable_height, 0),
        ):
            y_axis_labels.append(
                f'<text class="model-chart-y-label" x="{padding_left - 10}" y="{y + 5:.2f}" text-anchor="end">{value}</text>'
            )
        total_calls = sum(int(item.get("count", 0)) for item in usage_series)
        safe_chart_id = re.sub(r"[^a-zA-Z0-9_-]", "-", str(model_id))
        return f"""
        <div class="model-chart">
          <div class="model-chart-summary">
            <span>{html.escape(self.t("recent_24h_calls"))}</span>
            <span>{html.escape(self.t("total_calls", count=total_calls))}</span>
          </div>
          <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-labelledby="model-chart-title-{safe_chart_id}">
            <title id="model-chart-title-{safe_chart_id}">{html.escape(self.t("recent_24h_calls"))}</title>
            {grid_lines}
            <polygon class="model-chart-area" points="{area_points}"></polygon>
            <polyline class="model-chart-line" points="{polyline_points}"></polyline>
            {circles}
            {''.join(y_axis_labels)}
            {''.join(axis_labels)}
          </svg>
        </div>
        """

    def render_usage_chart(self, usage_series: list[dict], title: str, chart_id: str) -> str:
        if not usage_series:
            return ""
        max_cost = max((float(item["cost"]) for item in usage_series), default=0.0)
        max_cost = max(max_cost, 1.0)
        width = 1000
        height = 150
        padding_left = 72
        padding_right = 18
        padding_top = 16
        padding_bottom = 26
        usable_width = width - padding_left - padding_right
        usable_height = height - padding_top - padding_bottom
        step_x = usable_width / max(len(usage_series) - 1, 1)
        points = []
        for index, item in enumerate(usage_series):
            cost = float(item["cost"])
            x = padding_left + index * step_x
            y = padding_top + usable_height - ((cost / max_cost) * usable_height if max_cost else 0)
            points.append((x, y, cost))

        polyline_points = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
        area_points = f"{padding_left:.2f},{padding_top + usable_height:.2f} " + polyline_points + f" {padding_left + usable_width:.2f},{padding_top + usable_height:.2f}"
        circles = "".join(
            f'<circle class="chart-point" cx="{x:.2f}" cy="{y:.2f}" r="3.5"><title>{usage_series[index]["label"]}: {cost:.2f}</title></circle>'
            for index, (x, y, cost) in enumerate(points)
        )
        grid_lines = "".join(
            f'<line class="chart-grid" x1="{padding_left}" y1="{padding_top + usable_height * ratio:.2f}" x2="{padding_left + usable_width}" y2="{padding_top + usable_height * ratio:.2f}"></line>'
            for ratio in (0, 0.5, 1)
        )
        label_step = max(1, len(usage_series) // 6)
        axis_labels = []
        for index, (x, _, _) in enumerate(points):
            if index % label_step != 0 and index != len(points) - 1:
                continue
            anchor = "middle"
            if index == 0:
                anchor = "start"
            elif index == len(points) - 1:
                anchor = "end"
            axis_labels.append(
                f'<text class="chart-axis-label" x="{x:.2f}" y="{height - 4}" text-anchor="{anchor}">{html.escape(usage_series[index]["label"])}</text>'
            )
        y_axis_labels = []
        y_ticks = [
            (padding_top, max_cost),
            (padding_top + usable_height / 2, max_cost / 2),
            (padding_top + usable_height, 0.0),
        ]
        for y, value in y_ticks:
            y_axis_labels.append(
                f'<text class="chart-y-label" x="{padding_left - 10}" y="{y + 5:.2f}" text-anchor="end">{int(round(value))}</text>'
            )
        total = sum(float(item["cost"]) for item in usage_series)
        return f"""
        <div class="chart-panel" id="{chart_id}">
          <div class="chart-summary">
            <span>{html.escape(title)}</span>
            <span>{'합계' if self.current_language() == 'ko' else 'Total'} {total:.2f}</span>
          </div>
          <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-label="{html.escape(title)}">
            {grid_lines}
            <polygon class="chart-area" points="{area_points}"></polygon>
            <polyline class="chart-line" points="{polyline_points}"></polyline>
            {circles}
            {''.join(y_axis_labels)}
            {''.join(axis_labels)}
          </svg>
        </div>
        """

    def render_usage_chart_switcher(self, hourly_series: list[dict], daily_series: list[dict]) -> str:
        chart_id = "usage-chart-switcher"
        hourly_title = "최근 24시간 프리미엄 요청 사용량" if self.current_language() == "ko" else "Premium request usage in the last 24h"
        daily_title = "최근 7일 프리미엄 요청 사용량" if self.current_language() == "ko" else "Premium request usage in the last 7 days"
        hourly_panel = self.render_usage_chart(hourly_series, hourly_title, "usage-chart-24h")
        daily_panel = self.render_usage_chart(daily_series, daily_title, "usage-chart-7d")
        return f"""
        <div class="chart" id="{chart_id}">
          <div class="chart-tabs">
            <button class="chart-tab" type="button" onclick="focusAwaySelectChart('{chart_id}', 'usage-chart-24h', this)" style="background: var(--accent); color: white;">{'24시간' if self.current_language() == 'ko' else '24h'}</button>
            <button class="chart-tab" type="button" onclick="focusAwaySelectChart('{chart_id}', 'usage-chart-7d', this)">{'7일' if self.current_language() == 'ko' else '7d'}</button>
          </div>
          {hourly_panel}
          {daily_panel.replace('class="chart-panel"', 'class="chart-panel" hidden', 1)}
        </div>
        """

    def render_tier_options(self, tiers: list[dict], selected_tier_id, include_admin_only: bool = False) -> str:
        options = []
        if include_admin_only:
            options.append(f"<option value=\"\" {'selected' if selected_tier_id in (None, '', 0, '0') else ''}>{html.escape(self.admin_tier_label())}</option>")
        selected_text = str(selected_tier_id) if selected_tier_id not in (None, "") else ""
        for tier in tiers:
            selected = "selected" if selected_text == str(tier["id"]) else ""
            options.append(f"<option value=\"{tier['id']}\" {selected}>{html.escape(self.t('tier_or_higher', name=tier['name']))}</option>")
        return "".join(options)

    def render_exact_tier_options(self, tiers: list[dict], selected_tier_id) -> str:
        selected_text = str(selected_tier_id) if selected_tier_id not in (None, "") else ""
        return "".join(
            f"<option value=\"{tier['id']}\" {'selected' if selected_text == str(tier['id']) else ''}>{html.escape(tier['name'])}</option>"
            for tier in tiers
        )

    def admin_tier_label(self) -> str:
        return self.t("admin")

    def render_admin(self) -> None:
        user = self.require_admin()
        if not user:
            return
        snapshot = self.app.db.admin_snapshot()
        signup_open = self.signup_open()
        exclude_assistant_models = self.exclude_assistant_models_enabled()
        tiers = snapshot["tiers"]
        auto_promotion = snapshot["auto_promotion"]
        promotion_target_tiers = [tier for tier in tiers if not tier["is_system"]]
        user_rows = "".join(
            f"""
            <tr>
              <td>{row['id']}</td>
              <td>{html.escape(row['username'])}</td>
              <td>{html.escape(self.admin_tier_label() if row['is_admin'] else (row['tier_name'] or '-'))}</td>
              <td>{self.render_user_tier_control(row, tiers)}</td>
              <td>{html.escape(self.t('admin') if row['is_admin'] else self.t('member'))}</td>
              <td>{html.escape(self.t('suspended') if row['is_suspended'] else self.t('normal'))}</td>
              <td>{html.escape(row['last_seen_ip'] or '-')}</td>
              <td>{'-' if row['is_admin'] else f"{row['weekly_balance']:.2f}"}</td>
              <td>{'-' if row['is_admin'] else f"{row['bonus_balance']:.2f}"}</td>
              <td>{self.render_user_admin_actions(row, tiers)}</td>
            </tr>
            """
            for row in snapshot["users"]
        ) or f"<tr><td colspan='10'>{html.escape('회원이 없습니다.' if self.current_language() == 'ko' else 'No users.')}</td></tr>"
        admin_tier_row = f"""
            <tr>
              <td>
                <input type="text" value="{html.escape(self.admin_tier_label())}" disabled style="width: 100%;">
              </td>
              <td>{html.escape(self.t('fixed'))}</td>
              <td>-</td>
              <td><span class="hint">{html.escape(self.t('admin_only'))}</span></td>
            </tr>
        """
        tier_row_parts = []
        for tier in tiers:
            if tier["is_system"]:
                tier_action = f'<span class="hint">{html.escape(self.t("base_tier"))}</span>'
            else:
                delete_confirm = (
                    "이 티어를 삭제하시겠습니까? 소속 회원과 모델 설정은 인접 티어로 이동됩니다."
                    if self.current_language() == "ko"
                    else "Delete this tier? Assigned users and model settings will move to a neighboring tier."
                )
                tier_action = f"""
                  <form method="post" action="/admin/tiers/delete" onsubmit="return confirm({html.escape(json.dumps(delete_confirm))});">
                    {self.render_csrf_input()}
                    <input type="hidden" name="tier_id" value="{tier['id']}">
                    <button class="icon-btn" type="submit" aria-label="{html.escape('티어 삭제' if self.current_language() == 'ko' else 'Delete tier')}" title="{html.escape('삭제' if self.current_language() == 'ko' else 'Delete')}">{self.trash_icon_svg()}</button>
                  </form>
                """
            tier_row_parts.append(
                f"""
            <tr>
              <td>
                <input type="hidden" name="tier_id" value="{tier['id']}" form="tier-bulk-form">
                <input type="text" name="name" value="{html.escape(tier['name'])}" required style="width: 100%;" form="tier-bulk-form">
              </td>
              <td>{tier['sort_order']}</td>
              <td>
                <input type="number" step="0.1" min="0" name="weekly_quota" value="{float(tier['weekly_quota']):.2f}" required style="width: 8.5rem;" form="tier-bulk-form">
              </td>
              <td>
                <div class="row">
                  <form method="post" action="/admin/tiers/move">
                    {self.render_csrf_input()}
                    <input type="hidden" name="tier_id" value="{tier['id']}">
                    <input type="hidden" name="direction" value="up">
                    <button class="icon-btn" type="submit" aria-label="{html.escape('티어 위로 이동' if self.current_language() == 'ko' else 'Move tier up')}" title="{html.escape('위로' if self.current_language() == 'ko' else 'Up')}">{self.arrow_up_icon_svg()}</button>
                  </form>
                  <form method="post" action="/admin/tiers/move">
                    {self.render_csrf_input()}
                    <input type="hidden" name="tier_id" value="{tier['id']}">
                    <input type="hidden" name="direction" value="down">
                    <button class="icon-btn" type="submit" aria-label="{html.escape('티어 아래로 이동' if self.current_language() == 'ko' else 'Move tier down')}" title="{html.escape('아래로' if self.current_language() == 'ko' else 'Down')}">{self.arrow_down_icon_svg()}</button>
                  </form>
                  {tier_action}
                </div>
              </td>
            </tr>
            """
            )
        tier_rows = "".join(tier_row_parts)
        tier_rows = admin_tier_row + (tier_rows or f"<tr><td colspan='4'>{html.escape('티어가 없습니다.' if self.current_language() == 'ko' else 'No tiers.')}</td></tr>")
        context_placeholder = (
            "비우면 백엔드 기본값({value}) 사용"
            if self.current_language() == "ko"
            else "Blank uses backend default ({value})"
        )
        model_cards = "".join(
            f"""
            <div class="card admin-model-card">
              <input type="hidden" name="model_id" value="{html.escape(model['model_id'])}">
              <h3>{html.escape(model['display_name'])}</h3>
              <label>사용자에게 제공할 모델명
                <input type="text" name="display_name" value="{html.escape(model['display_name'])}" required>
              </label>
              <p class="hint">백엔드 모델 ID: <code>{html.escape(model['model_id'])}</code></p>
              <label>모델 종류
                <select name="custom_model_kind">
                  <option value="" {'selected' if not (model['custom_model_kind'] or '').strip() else ''}>서버 기본값</option>
                  <option value="LLM" {'selected' if (model['custom_model_kind'] or '').strip().upper() == 'LLM' else ''}>LLM</option>
                  <option value="VLM" {'selected' if (model['custom_model_kind'] or '').strip().upper() == 'VLM' else ''}>VLM</option>
                </select>
              </label>
              <label>커스텀 컨텍스트 한도
                <input type="number" step="1" min="1" name="custom_context_window" value="{'' if model['custom_context_window'] is None else int(model['custom_context_window'])}" placeholder="{html.escape(context_placeholder.format(value=self.format_token_count(model['context_window'])))}">
              </label>
              <label>커스텀 출력 한도
                <input type="number" step="1" min="1" name="custom_max_output_tokens" value="{'' if model['custom_max_output_tokens'] is None else int(model['custom_max_output_tokens'])}" placeholder="{html.escape(context_placeholder.format(value=self.format_token_count(model['max_output_tokens'])))}">
              </label>
              <label>1회 비용<input type="number" step="0.01" min="0" name="cost_per_request" value="{float(model['cost_per_request']):.2f}" required></label>
              <label>사용 가능 티어
                <select name="minimum_tier_id">
                  {self.render_tier_options(tiers, model['minimum_tier_id'], include_admin_only=True)}
                </select>
              </label>
            </div>
            """
            for model in snapshot["models"]
        ) or f"<p>{html.escape(self.t('no_models_refresh'))}</p>"
        body = f"""
        <section class="hero">
          <div>
            <h1>관리자 패널</h1>
            <p>회원 티어, 티어별 주간 충전량, 모델 접근 정책을 관리합니다.</p>
          </div>
          <div class="row"><a href="/dashboard">사용자 대시보드</a></div>
        </section>
        <section class="grid">
          <article class="card">
            <h2>서비스 설정</h2>
            <form method="post" action="/admin/settings">
              {self.render_csrf_input()}
              <label>회원가입 상태
                <select name="signup_open">
                  <option value="1" {'selected' if signup_open else ''}>{html.escape('열기' if self.current_language() == 'ko' else 'Open')}</option>
                  <option value="0" {'selected' if not signup_open else ''}>{html.escape('닫기' if self.current_language() == 'ko' else 'Closed')}</option>
                </select>
              </label>
              <div class="row">
                <input id="exclude-assistant-models" type="checkbox" name="exclude_assistant_models" value="1" {'checked' if exclude_assistant_models else ''}>
                <label for="exclude-assistant-models" style="display: block;">모델명에 assistant가 포함된 모델은 동기화 시 제외</label>
              </div>
              {self.render_auto_promotion_settings(auto_promotion, promotion_target_tiers)}
              <button type="submit">{html.escape(self.t('save'))}</button>
            </form>
          </article>
          <article class="card">
            <h2>티어 관리</h2>
            <div class="row" style="margin-bottom: 14px;">
              <form method="post" action="/admin/tiers/create">
                {self.render_csrf_input()}
                <button type="submit">티어 추가</button>
              </form>
            </div>
            <div class="table-wrap">
              <table><thead><tr><th style="width: 24%;">티어 이름</th><th style="width: 12%;">순서</th><th style="width: 18%;">주간 충전량</th><th>작업</th></tr></thead><tbody>{tier_rows}</tbody></table>
            </div>
            <form id="tier-bulk-form" method="post" action="/admin/tiers/update">
              {self.render_csrf_input()}
              <div class="row" style="justify-content: flex-end; margin-top: 16px;">
                <button type="submit">티어 전체 저장</button>
              </div>
            </form>
          </article>
        </section>
        <section class="grid">
          <article class="card">
            <h2>보너스 일괄/개별 지급</h2>
            <form method="post" action="/admin/grant">
              {self.render_csrf_input()}
              <label>지급량<input type="number" step="0.1" min="0.1" name="amount" required></label>
              <label>설명<input type="text" name="description" value="Admin grant" required></label>
              <label>대상 아이디 (비우면 전체 지급)<input type="text" name="username" pattern="[a-z0-9]*"></label>
              <button type="submit">지급</button>
            </form>
          </article>
        </section>
        <section class="card">
          <div class="row" style="justify-content: space-between; margin-bottom: 18px;">
            <h2>모델 정책</h2>
            <form method="post" action="/admin/models/refresh">{self.render_csrf_input()}<button type="submit">백엔드에서 모델 새로고침</button></form>
          </div>
          <form method="post" action="/admin/models/update">
            {self.render_csrf_input()}
            <div class="grid">{model_cards}</div>
            <div class="row" style="justify-content: flex-end; margin-top: 16px;">
              <button type="submit">모델 정책 전체 저장</button>
            </div>
          </form>
        </section>
        <section class="card">
          <h2>회원 현황</h2>
          <div class="table-wrap">
            <table><thead><tr><th>고유 번호</th><th>아이디</th><th>현재 티어</th><th>티어 변경</th><th>권한</th><th>상태</th><th>마지막 접속 IP</th><th>주간 잔액</th><th>보너스 잔액</th><th>작업</th></tr></thead><tbody>{user_rows}</tbody></table>
          </div>
        </section>
        """
        self.respond_html("관리자 패널", body)

    def render_auto_promotion_settings(self, settings: dict, tiers: list[dict]) -> str:
        if not tiers:
            return ""
        day_label = "일" if self.current_language() == "ko" else "days"
        hour_label = "시간" if self.current_language() == "ko" else "hours"
        target_value = "" if settings.get("target_tier_id") in (None, "") else str(settings["target_tier_id"])
        target_options = "".join(
            f"<option value=\"{tier['id']}\" {'selected' if target_value == str(tier['id']) else ''}>{html.escape(tier['name'])}</option>"
            for tier in tiers
        )
        return f"""
        <div class="stack" style="padding-top: 8px; border-top: 1px solid var(--line);">
          <h3 style="margin: 0;">티어 자동 승격</h3>
          <p class="hint">선택한 조건 중 하나를 만족하면 아래 티어로 자동 승격됩니다.</p>
          <div class="stack">
            <div class="stack">
              <div class="row">
                <input id="auto-promo-time-enabled" type="checkbox" name="auto_promo_time_enabled" value="1" {'checked' if settings.get('time_enabled') else ''}>
                <label for="auto-promo-time-enabled" style="display: block;">가입 후 경과 시간 조건 사용</label>
              </div>
              <div class="row">
                <input type="number" min="1" step="1" name="auto_promo_time_value" value="{html.escape(str(settings.get('time_value', '7')))}" style="width: 8rem;">
                <label class="pill"><input type="radio" name="auto_promo_time_unit" value="days" {'checked' if settings.get('time_unit') != 'hours' else ''}>{html.escape(day_label)}</label>
                <label class="pill"><input type="radio" name="auto_promo_time_unit" value="hours" {'checked' if settings.get('time_unit') == 'hours' else ''}>{html.escape(hour_label)}</label>
              </div>
            </div>
            <div class="stack">
              <div class="row">
                <input id="auto-promo-usage-enabled" type="checkbox" name="auto_promo_usage_enabled" value="1" {'checked' if settings.get('usage_enabled') else ''}>
                <label for="auto-promo-usage-enabled" style="display: block;">가입 후 프리미엄 요청 누적 사용량 조건 사용</label>
              </div>
              <div class="row">
                <input type="number" min="0" step="0.1" name="auto_promo_usage_value" value="{html.escape(str(settings.get('usage_value', '10')))}" style="width: 8rem;">
                <span class="hint">이상 사용 시</span>
              </div>
            </div>
            <label>자동 승격 티어
              <select name="auto_promo_target_tier_id">
                <option value="">선택 안 함</option>
                {target_options}
              </select>
            </label>
          </div>
        </div>
        """

    def render_user_tier_control(self, row, tiers: list[dict]) -> str:
        if row["is_admin"]:
            return f'<span class="hint">{html.escape(self.t("admin_fixed"))}</span>'
        return f"""
        <form method="post" action="/admin/users/tier" class="row">
          {self.render_csrf_input()}
          <input type="hidden" name="user_id" value="{row['id']}">
          <select name="tier_id" style="min-width: 9rem;">
            {self.render_exact_tier_options(tiers, row['tier_id'])}
          </select>
          <button class="secondary" type="submit">{html.escape(self.t("apply"))}</button>
        </form>
        """

    def render_user_admin_actions(self, row, tiers: list[dict]) -> str:
        if row["is_admin"]:
            return f'<span class="hint">{html.escape(self.t("admin_protected"))}</span>'
        suspend_label = self.t("unsuspend") if row["is_suspended"] else self.t("suspend")
        suspend_value = "0" if row["is_suspended"] else "1"
        delete_confirm = (
            "이 회원을 강퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다."
            if self.current_language() == "ko"
            else "Delete this user? This cannot be undone."
        )
        return f"""
        <div class="row">
          <form method="post" action="/admin/users/suspend">
            {self.render_csrf_input()}
            <input type="hidden" name="user_id" value="{row['id']}">
            <input type="hidden" name="suspended" value="{suspend_value}">
            <button class="secondary" type="submit">{html.escape(suspend_label)}</button>
          </form>
          <form method="post" action="/admin/users/delete" onsubmit="return confirm({html.escape(json.dumps(delete_confirm))});">
            {self.render_csrf_input()}
            <input type="hidden" name="user_id" value="{row['id']}">
            <button class="secondary" type="submit">{html.escape(self.t("delete"))}</button>
          </form>
        </div>
        """

    def handle_admin_settings(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        self.app.db.set_setting("signup_open", "1" if form.get("signup_open") == "1" else "0")
        self.app.db.set_setting(
            "exclude_assistant_models",
            "1" if form.get("exclude_assistant_models") == "1" else "0",
        )
        promotion_target_tiers = [tier for tier in self.app.db.list_tiers() if not tier["is_system"]]
        if promotion_target_tiers:
            time_enabled = form.get("auto_promo_time_enabled") == "1"
            usage_enabled = form.get("auto_promo_usage_enabled") == "1"
            time_value = str(form.get("auto_promo_time_value", "7")).strip() or "7"
            usage_value = str(form.get("auto_promo_usage_value", "10")).strip() or "10"
            time_unit = str(form.get("auto_promo_time_unit", "days")).strip().lower()
            target_tier_raw = str(form.get("auto_promo_target_tier_id", "")).strip()
            eligible_target_ids = {int(tier["id"]) for tier in promotion_target_tiers}

            if time_enabled or usage_enabled:
                try:
                    if time_enabled and int(float(time_value)) <= 0:
                        raise ValueError("시간 기반 자동 승격 값은 1 이상이어야 합니다.")
                    if usage_enabled and float(usage_value) < 0:
                        raise ValueError("누적 사용량 조건은 0 이상이어야 합니다.")
                    target_tier_id = int(target_tier_raw)
                except (TypeError, ValueError):
                    self.respond_html("서비스 설정 저장 실패", '<section class="card"><p class="error">자동 승격 티어와 조건 값을 올바르게 입력해 주세요.</p></section>')
                    return
                if target_tier_id not in eligible_target_ids:
                    self.respond_html("서비스 설정 저장 실패", '<section class="card"><p class="error">자동 승격 티어는 기본 티어를 제외한 일반 티어 중에서 선택해 주세요.</p></section>')
                    return
            else:
                target_tier_id = None

            self.app.db.set_auto_promotion_settings(
                {
                    "time_enabled": time_enabled,
                    "time_value": time_value,
                    "time_unit": time_unit,
                    "usage_enabled": usage_enabled,
                    "usage_value": usage_value,
                    "target_tier_id": target_tier_id,
                }
            )
        else:
            self.app.db.set_auto_promotion_settings(
                {
                    "time_enabled": False,
                    "time_value": "7",
                    "time_unit": "days",
                    "usage_enabled": False,
                    "usage_value": "10",
                    "target_tier_id": None,
                }
            )
        self.redirect("/admin")

    def handle_admin_tier_create(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        self.app.db.create_tier()
        self.redirect("/admin")

    def handle_admin_tier_update(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        def ensure_list(value):
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        tier_ids = ensure_list(form.get("tier_id", []))
        names = ensure_list(form.get("name", []))
        weekly_quotas = ensure_list(form.get("weekly_quota", []))
        try:
            updates = []
            for index, tier_id in enumerate(tier_ids):
                updates.append(
                    {
                        "id": int(tier_id),
                        "name": str(names[index] if index < len(names) else "").strip(),
                        "weekly_quota": float(weekly_quotas[index] if index < len(weekly_quotas) else 0),
                    }
                )
            self.app.db.update_tiers_bulk(updates)
        except ValueError as exc:
            self.respond_html("티어 저장 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.redirect("/admin")

    def handle_admin_tier_move(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        self.app.db.move_tier(int(form["tier_id"]), str(form.get("direction", "down")))
        self.redirect("/admin")

    def handle_admin_tier_delete(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        try:
            self.app.db.delete_tier(int(form["tier_id"]))
        except ValueError as exc:
            self.respond_html("티어 삭제 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.redirect("/admin")

    def handle_admin_grant(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        username = form.get("username", "").strip()
        self.app.db.grant_bonus(
            float(form.get("amount", "0")),
            form.get("description", "Admin grant"),
            username or None,
        )
        self.redirect("/admin")

    def handle_model_refresh(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        try:
            models = self.app.filter_upstream_models(self.app.upstream.fetch_models())
            self.app.db.upsert_models(models)
            self.redirect("/admin")
        except Exception as exc:
            self.respond_html(
                "모델 동기화 실패",
                f"""
                <section class="hero">
                  <div><h1>모델 동기화 실패</h1><p>백엔드 연결 설정을 확인한 뒤 다시 시도해 주세요.</p></div>
                  <div class="row"><a href="/admin">관리자 패널로 돌아가기</a></div>
                </section>
                <section class="card"><p class="error">{html.escape(str(exc))}</p></section>
                """,
            )

    def handle_model_update(self) -> None:
        if not self.require_admin():
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        def ensure_list(value):
            if isinstance(value, list):
                return value
            if value is None:
                return []
            return [value]

        model_ids = ensure_list(form.get("model_id", []))
        display_names = ensure_list(form.get("display_name", []))
        costs = ensure_list(form.get("cost_per_request", []))
        minimum_tier_ids = ensure_list(form.get("minimum_tier_id", []))
        custom_kinds = ensure_list(form.get("custom_model_kind", []))
        custom_contexts = ensure_list(form.get("custom_context_window", []))
        custom_outputs = ensure_list(form.get("custom_max_output_tokens", []))
        updates = []
        public_names = set()
        backend_ids = {str(model_id) for model_id in model_ids}
        for index, model_id in enumerate(model_ids):
            minimum_tier_id = self.parse_optional_tier_id(minimum_tier_ids[index] if index < len(minimum_tier_ids) else "")
            display_name = str(display_names[index] if index < len(display_names) else model_id).strip() or str(model_id)
            public_key = display_name.casefold()
            if public_key in public_names:
                self.respond_html("모델 정책 저장 실패", '<section class="card"><p class="error">사용자에게 제공할 모델명은 서로 달라야 합니다.</p></section>')
                return
            if display_name != str(model_id) and display_name in backend_ids:
                self.respond_html("모델 정책 저장 실패", '<section class="card"><p class="error">공개 모델명은 다른 백엔드 모델 ID와 같을 수 없습니다.</p></section>')
                return
            public_names.add(public_key)
            updates.append(
                {
                    "model_id": model_id,
                    "display_name": display_name,
                    "cost_per_request": float(costs[index] if index < len(costs) else 0),
                    "access_mode": "tier" if minimum_tier_id is not None else "admin",
                    "minimum_tier_id": minimum_tier_id,
                    "custom_model_kind": self.normalize_custom_model_kind(custom_kinds[index] if index < len(custom_kinds) else ""),
                    "custom_context_window": self.parse_optional_positive_int(custom_contexts[index] if index < len(custom_contexts) else ""),
                    "custom_max_output_tokens": self.parse_optional_positive_int(custom_outputs[index] if index < len(custom_outputs) else ""),
                }
            )
        self.app.db.update_model_policies_bulk(updates)
        self.redirect("/admin")

    def normalize_custom_model_kind(self, value: str) -> str:
        kind = str(value).strip().upper()
        return kind if kind in {"LLM", "VLM"} else ""

    def parse_optional_positive_int(self, value: str):
        text = str(value).strip()
        if not text:
            return None
        number = int(float(text))
        return number if number > 0 else None

    def parse_optional_tier_id(self, value: str):
        text = str(value).strip()
        if not text:
            return None
        return int(text)

    def handle_rotate_api_key(self) -> None:
        user = self.require_session_user()
        if not user:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        self.app.db.rotate_user_api_key(user["id"])
        self.redirect("/dashboard")

    def handle_password_change(self) -> None:
        user = self.require_session_user()
        if not user:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        new_password = form.get("new_password", "")
        if len(new_password) < 8:
            self.respond_html("비밀번호 변경 실패", '<section class="card"><p class="error">새 비밀번호는 8자 이상이어야 합니다.</p></section>')
            return
        try:
            self.app.db.update_user_password(user["id"], form.get("current_password", ""), new_password)
        except ValueError as exc:
            self.respond_html("비밀번호 변경 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.send_response(302)
        self.clear_session_cookie()
        self.send_header("Location", "/login")
        self.end_headers()

    def handle_account_delete(self) -> None:
        user = self.require_session_user()
        if not user:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        if user["is_admin"]:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        cookie = SimpleCookie(self.headers.get("Cookie"))
        token = cookie.get("focusaway_session")
        if token:
            self.app.db.delete_session(token.value)
        self.app.db.delete_user(user["id"])
        self.send_response(302)
        self.clear_session_cookie()
        self.send_header("Location", "/")
        self.end_headers()

    def handle_admin_user_suspend(self) -> None:
        admin = self.require_admin()
        if not admin:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        try:
            self.app.db.update_user_suspension(int(form["user_id"]), form.get("suspended") == "1")
        except ValueError as exc:
            self.respond_html("회원 상태 변경 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.redirect("/admin")

    def handle_admin_user_delete(self) -> None:
        admin = self.require_admin()
        if not admin:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        try:
            self.app.db.delete_user(int(form["user_id"]))
        except ValueError as exc:
            self.respond_html("회원 삭제 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.redirect("/admin")

    def handle_admin_user_tier(self) -> None:
        admin = self.require_admin()
        if not admin:
            return
        if not self.validate_csrf():
            return self.send_error(HTTPStatus.FORBIDDEN)
        form = self.parsed_body()
        user_id = int(form["user_id"])
        target = self.app.db.get_user(user_id)
        if not target:
            self.respond_html("티어 변경 실패", '<section class="card"><p class="error">회원을 찾을 수 없습니다.</p></section>')
            return
        if target["is_admin"]:
            self.respond_html("티어 변경 실패", '<section class="card"><p class="error">관리자 계정의 티어는 변경할 수 없습니다.</p></section>')
            return
        try:
            self.app.db.update_user_tier(user_id, int(form["tier_id"]))
        except ValueError as exc:
            self.respond_html("티어 변경 실패", f'<section class="card"><p class="error">{html.escape(str(exc))}</p></section>')
            return
        self.redirect("/admin")

    def current_user_payload(self) -> dict:
        user = self.current_session_user()
        if not user:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "username": user["username"],
            "is_admin": bool(user["is_admin"]),
            "weekly_balance": 0 if user["is_admin"] else user["weekly_balance"],
            "bonus_balance": 0 if user["is_admin"] else user["bonus_balance"],
            "api_key": user["api_key"],
        }

    def signup_open(self) -> bool:
        return self.app.db.get_setting("signup_open", "1") == "1"

    def exclude_assistant_models_enabled(self) -> bool:
        return self.app.db.get_setting("exclude_assistant_models", "0") == "1"

    def handle_models_api(self) -> None:
        api_user = self.api_user()
        if not api_user:
            return
        self.ensure_models_seeded()
        rows = self.app.db.accessible_models_for_user(bool(api_user["is_admin"]), api_user["tier_sort_order"])
        data = [
            {"id": row["display_name"], "object": "model", "owned_by": self.app.config.app_name}
            for row in rows
        ]
        self.render_json({"object": "list", "data": data})

    def api_user(self):
        auth = self.headers.get("Authorization", "")
        match = re.match(r"Bearer\s+(.+)", auth)
        if not match:
            self.render_json({"error": {"message": "Missing Bearer token."}}, 401)
            return None
        user = self.app.db.get_user_by_api_key(match.group(1))
        if not user:
            self.render_json({"error": {"message": "Invalid API key."}}, 401)
            return None
        self.app.db.record_user_activity(user["id"], self.client_ip())
        return user

    def handle_proxy_api(self, path: str) -> None:
        api_user = self.api_user()
        if not api_user:
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        payload = json.loads(body.decode("utf-8") or "{}") if body else {}
        wants_stream = self.normalize_stream_preference(path, payload)
        model_id = payload.get("model")
        if model_id:
            self.ensure_model_available(model_id)
        policy = self.app.db.get_model_policy_by_public_id(model_id) if model_id else None
        if not policy:
            return self.render_json({"error": {"message": "Model is not registered in FocusAway."}}, 400)
        self.enforce_output_token_limit(path, payload, policy)
        if isinstance(payload, dict):
            payload["model"] = policy["model_id"]
        if body and isinstance(payload, dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if not api_user["is_admin"]:
            required_sort_order = policy["minimum_tier_sort_order"]
            if policy["access_mode"] == "admin" or required_sort_order is None:
                return self.render_json({"error": {"message": "This model is restricted to administrators."}}, 403)
            user_sort_order = api_user["tier_sort_order"]
            if user_sort_order is None or int(user_sort_order) < int(required_sort_order):
                return self.render_json({"error": {"message": "Your tier does not allow access to this model."}}, 403)

        billable_paths = {
            "/v1/chat/completions",
            "/v1/completions",
            "/v1/responses",
            "/v1/embeddings",
            "/v1/images/generations",
        }
        if self.command == "POST" and path in billable_paths:
            ok, message = self.app.db.charge_request(
                api_user["id"],
                policy["model_id"],
                path,
                float(policy["cost_per_request"]),
            )
            if not ok:
                return self.render_json({"error": {"message": message}}, 402)

        if wants_stream and path in self.STREAM_CAPABLE_PATHS:
            return self.stream_proxy_response(path, body, policy["model_id"], api_user)

        status, headers, response_body = self.app.upstream.proxy(
            path,
            self.command,
            body,
            dict(self.headers),
            wants_stream,
        )
        if status >= 400:
            return self.render_json(self.upstream_error_payload(status), status)
        headers, response_body = self.coerce_non_stream_response(path, wants_stream, headers, response_body)
        headers, response_body = self.rewrite_response_model_name(headers, response_body, policy["display_name"])
        self.send_response(status)
        self.apply_cors_headers()
        self.apply_common_security_headers()
        self.send_header("Content-Type", self.header_value(headers, "Content-Type", "application/json"))
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)
        if 200 <= status < 300 and policy["model_id"]:
            self.app.record_live_model_usage(policy["model_id"])

    def rewrite_response_model_name(
        self,
        headers: dict[str, str],
        response_body: bytes,
        public_model_name: str,
    ) -> tuple[dict[str, str], bytes]:
        content_type = self.header_value(headers, "Content-Type", "")
        if "application/json" not in content_type.lower():
            return headers, response_body
        try:
            payload = json.loads(response_body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return headers, response_body
        if isinstance(payload, dict) and "model" in payload:
            payload["model"] = public_model_name
            updated_headers = dict(headers)
            updated_headers["Content-Type"] = "application/json; charset=utf-8"
            return updated_headers, json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return headers, response_body

    def stream_proxy_response(self, path: str, body: bytes | None, model_id: str, api_user) -> None:
        status, headers, upstream_response = self.app.upstream.open_proxy(
            path,
            self.command,
            body,
            dict(self.headers),
            True,
        )
        chunk_size = self.stream_chunk_size_for_user(api_user)
        try:
            if status >= 400:
                return self.render_json(self.upstream_error_payload(status), status)
            self.send_response(status)
            self.apply_cors_headers()
            self.apply_common_security_headers()
            self.send_header("Content-Type", self.header_value(headers, "Content-Type", "text/event-stream"))
            cache_control = self.header_value(headers, "Cache-Control", "no-cache")
            self.send_header("Cache-Control", cache_control)
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

            while True:
                chunk = upstream_response.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
            if 200 <= status < 300 and model_id:
                self.app.record_live_model_usage(model_id)
        finally:
            upstream_response.close()

    def stream_chunk_size_for_user(self, api_user) -> int:
        if api_user["is_admin"]:
            return self.PRIORITY_STREAM_CHUNK_SIZE
        user_sort_order = api_user["tier_sort_order"]
        if user_sort_order is None:
            return self.DEFAULT_STREAM_CHUNK_SIZE
        if int(user_sort_order) > self.app.db.base_tier_sort_order():
            return self.PRIORITY_STREAM_CHUNK_SIZE
        return self.DEFAULT_STREAM_CHUNK_SIZE

    def normalize_stream_preference(self, path: str, payload: dict) -> bool:
        if path not in self.STREAM_CAPABLE_PATHS:
            return False
        stream_value = payload.get("stream")
        if stream_value is None:
            payload["stream"] = False
            return False
        return bool(stream_value)

    def enforce_output_token_limit(self, path: str, payload: dict, policy) -> None:
        enforced_limit = policy["custom_max_output_tokens"]
        if enforced_limit in (None, "", 0):
            return
        if not isinstance(payload, dict):
            return
        keys_by_path = {
            "/v1/chat/completions": ("max_completion_tokens", "max_tokens"),
            "/v1/completions": ("max_tokens",),
            "/v1/responses": ("max_output_tokens", "max_tokens"),
        }
        keys = keys_by_path.get(path, ())
        limit = int(enforced_limit)
        for key in keys:
            requested = self.coerce_positive_int(payload.get(key))
            if requested is not None and requested > limit:
                payload[key] = limit

    def coerce_positive_int(self, value) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            number = int(float(value))
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def coerce_non_stream_response(
        self,
        path: str,
        wants_stream: bool,
        headers: dict[str, str],
        response_body: bytes,
    ) -> tuple[dict[str, str], bytes]:
        content_type = self.header_value(headers, "Content-Type")
        if wants_stream:
            return headers, response_body
        if not self.looks_like_sse(content_type, response_body):
            return headers, response_body

        payload = self.parse_sse_json(path, response_body)
        if payload is None:
            return headers, response_body
        payload = self.inject_thinking_markup(path, payload)

        coerced_headers = dict(headers)
        coerced_headers["Content-Type"] = "application/json; charset=utf-8"
        coerced_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return coerced_headers, coerced_body

    def header_value(self, headers: dict[str, str], target: str, default: str = "") -> str:
        target_lower = target.lower()
        for key, value in headers.items():
            if key.lower() == target_lower:
                return value
        return default

    def upstream_error_payload(self, status: int) -> dict:
        if 400 <= status < 500:
            message = "The upstream backend rejected the request."
        else:
            message = "The upstream backend is temporarily unavailable."
        return {"error": {"message": message}}

    def looks_like_sse(self, content_type: str, response_body: bytes) -> bool:
        if "text/event-stream" in content_type.lower():
            return True
        preview = response_body[:2048].decode("utf-8", errors="ignore").lstrip()
        if preview.startswith("data:") or preview.startswith("event:"):
            return True
        return "\ndata:" in preview or "\nevent:" in preview

    def parse_sse_json(self, path: str, response_body: bytes):
        text = response_body.decode("utf-8", errors="replace")
        events: list[dict] = []
        for chunk in text.replace("\r\n", "\n").split("\n\n"):
            data_lines = []
            for line in chunk.split("\n"):
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
            if not data_lines:
                continue
            data = "\n".join(data_lines).strip()
            if not data or data == "[DONE]":
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                continue

        if not events:
            return None
        if len(events) == 1:
            return events[0]
        if path == "/v1/chat/completions":
            return self.merge_chat_completion_events(events)
        if path == "/v1/completions":
            return self.merge_text_completion_events(events)
        if path == "/v1/responses":
            return self.merge_responses_events(events)
        return events[-1]

    def merge_chat_completion_events(self, events: list[dict]) -> dict:
        last = events[-1]
        merged_choices: dict[int, dict] = {}
        for event in events:
            for choice in event.get("choices", []):
                index = int(choice.get("index", 0))
                entry = merged_choices.setdefault(
                    index,
                    {
                        "index": index,
                        "message": {"role": "assistant", "content": "", "reasoning_content": ""},
                        "reasoning_content": "",
                        "finish_reason": None,
                    },
                )
                if "message" in choice:
                    message = choice.get("message") or {}
                    if message.get("role"):
                        entry["message"]["role"] = message["role"]
                    if isinstance(message.get("content"), str):
                        entry["message"]["content"] = message["content"]
                    if isinstance(message.get("reasoning_content"), str):
                        entry["message"]["reasoning_content"] = message["reasoning_content"]
                        entry["reasoning_content"] = message["reasoning_content"]
                    if "reasoning" in message:
                        entry["message"]["reasoning"] = message["reasoning"]
                        entry["reasoning"] = message["reasoning"]
                delta = choice.get("delta") or {}
                if delta.get("role"):
                    entry["message"]["role"] = delta["role"]
                if isinstance(delta.get("content"), str):
                    entry["message"]["content"] += delta["content"]
                if isinstance(delta.get("reasoning_content"), str):
                    entry["message"]["reasoning_content"] += delta["reasoning_content"]
                    entry["reasoning_content"] += delta["reasoning_content"]
                if "reasoning" in delta:
                    entry["message"]["reasoning"] = delta["reasoning"]
                    entry["reasoning"] = delta["reasoning"]
                if "reasoning_content" in choice and isinstance(choice.get("reasoning_content"), str):
                    entry["message"]["reasoning_content"] = choice["reasoning_content"]
                    entry["reasoning_content"] = choice["reasoning_content"]
                if "reasoning" in choice:
                    entry["message"]["reasoning"] = choice["reasoning"]
                    entry["reasoning"] = choice["reasoning"]
                if choice.get("finish_reason") is not None:
                    entry["finish_reason"] = choice["finish_reason"]

        normalized_choices = []
        for index in sorted(merged_choices):
            entry = merged_choices[index]
            if not entry["message"].get("reasoning_content"):
                entry["message"].pop("reasoning_content", None)
            if not entry.get("reasoning_content"):
                entry.pop("reasoning_content", None)
            normalized_choices.append(entry)

        return {
            "id": last.get("id"),
            "object": "chat.completion",
            "created": last.get("created"),
            "model": last.get("model"),
            "choices": normalized_choices,
            "usage": last.get("usage"),
        }

    def merge_text_completion_events(self, events: list[dict]) -> dict:
        last = events[-1]
        merged_choices: dict[int, dict] = {}
        for event in events:
            for choice in event.get("choices", []):
                index = int(choice.get("index", 0))
                entry = merged_choices.setdefault(
                    index,
                    {
                        "index": index,
                        "text": "",
                        "finish_reason": None,
                    },
                )
                if isinstance(choice.get("text"), str):
                    entry["text"] += choice["text"]
                if choice.get("finish_reason") is not None:
                    entry["finish_reason"] = choice["finish_reason"]

        return {
            "id": last.get("id"),
            "object": "text_completion",
            "created": last.get("created"),
            "model": last.get("model"),
            "choices": [merged_choices[index] for index in sorted(merged_choices)],
            "usage": last.get("usage"),
        }

    def inject_thinking_markup(self, path: str, payload: dict) -> dict:
        if path == "/v1/chat/completions":
            for choice in payload.get("choices", []) or []:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") or {}
                if not isinstance(message, dict):
                    continue
                reasoning_text = self.extract_reasoning_text(choice, message)
                content_text = message.get("content")
                if isinstance(reasoning_text, str) and reasoning_text.strip() and isinstance(content_text, str):
                    message["content"] = self.combine_thinking_and_content(reasoning_text, content_text)
                    choice["message"] = message
            return payload

        if path == "/v1/responses":
            for item in payload.get("output", []) or []:
                if not isinstance(item, dict):
                    continue
                reasoning_text = item.get("reasoning_content")
                if not isinstance(reasoning_text, str) or not reasoning_text.strip():
                    continue
                for part in item.get("content", []) or []:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                        part["text"] = self.combine_thinking_and_content(reasoning_text, part["text"])
            return payload

        return payload

    def extract_reasoning_text(self, choice: dict, message: dict) -> str:
        if isinstance(message.get("reasoning_content"), str) and message["reasoning_content"].strip():
            return message["reasoning_content"]
        if isinstance(choice.get("reasoning_content"), str) and choice["reasoning_content"].strip():
            return choice["reasoning_content"]
        reasoning = message.get("reasoning", choice.get("reasoning"))
        if isinstance(reasoning, str):
            return reasoning
        return ""

    def combine_thinking_and_content(self, reasoning_text: str, content_text: str) -> str:
        if "<thinking>" in content_text:
            return content_text
        reasoning_block = f"<thinking>{reasoning_text.strip()}</thinking>"
        if not content_text.strip():
            return reasoning_block
        return f"{reasoning_block}\n\n{content_text}"

    def merge_responses_events(self, events: list[dict]) -> dict:
        response = {}
        output_items: dict[int, dict] = {}

        for event in events:
            event_type = event.get("type", "")
            event_response = event.get("response")
            if isinstance(event_response, dict):
                response = self.deep_merge_dicts(response, event_response)
                for index, item in enumerate(event_response.get("output", []) or []):
                    if isinstance(item, dict):
                        output_items[index] = self.deep_merge_dicts(output_items.get(index, {}), item)

            if event_type == "response.output_item.added":
                output_index = int(event.get("output_index", 0))
                item = event.get("item") or {}
                if isinstance(item, dict):
                    output_items[output_index] = self.deep_merge_dicts(output_items.get(output_index, {}), item)
            elif event_type == "response.content_part.added":
                self.merge_response_content_part(output_items, event)
            elif event_type.endswith(".delta"):
                self.merge_response_delta(output_items, event)
            elif event_type.endswith(".done"):
                self.merge_response_done(output_items, event)

        if output_items:
            normalized_items = []
            for index in sorted(output_items):
                item = output_items[index]
                if item.get("reasoning_content") and not item.get("content"):
                    item["content"] = [{"type": "reasoning", "text": item["reasoning_content"]}]
                elif item.get("reasoning_content") and isinstance(item.get("content"), list):
                    content = item["content"]
                    has_reasoning_part = any(
                        isinstance(part, dict) and part.get("type") == "reasoning"
                        for part in content
                    )
                    if not has_reasoning_part:
                        content.insert(0, {"type": "reasoning", "text": item["reasoning_content"]})
                normalized_items.append(item)
            response["output"] = normalized_items
            reasoning_parts = []
            for item in normalized_items:
                if item.get("reasoning_content"):
                    reasoning_parts.append(item["reasoning_content"])
            if reasoning_parts and "reasoning_content" not in response:
                response["reasoning_content"] = "\n".join(reasoning_parts)
        return response or events[-1]

    def merge_response_content_part(self, output_items: dict[int, dict], event: dict) -> None:
        output_index = int(event.get("output_index", 0))
        item = output_items.setdefault(output_index, {})
        content = item.setdefault("content", [])
        content_index = int(event.get("content_index", len(content)))
        part = event.get("part") or {}
        while len(content) <= content_index:
            content.append({})
        if isinstance(part, dict):
            content[content_index] = self.deep_merge_dicts(content[content_index], part)

    def merge_response_delta(self, output_items: dict[int, dict], event: dict) -> None:
        output_index = int(event.get("output_index", 0))
        item = output_items.setdefault(output_index, {})
        event_type = event.get("type", "")
        delta_text = event.get("delta")

        if "reasoning" in event_type:
            item["type"] = item.get("type", "reasoning")
            if isinstance(delta_text, str):
                item["reasoning_content"] = item.get("reasoning_content", "") + delta_text
                item["text"] = item.get("text", "") + delta_text
            return

        content = item.setdefault("content", [])
        content_index = int(event.get("content_index", 0))
        while len(content) <= content_index:
            content.append({})
        part = content[content_index]

        if "output_text" in event_type:
            part["type"] = part.get("type", "output_text")
            part["text"] = part.get("text", "") + (delta_text or "")
        elif isinstance(delta_text, str):
            part["text"] = part.get("text", "") + delta_text

    def merge_response_done(self, output_items: dict[int, dict], event: dict) -> None:
        output_index = int(event.get("output_index", 0))
        item = output_items.setdefault(output_index, {})
        event_type = event.get("type", "")

        if "reasoning" in event_type:
            if "text" in event and isinstance(event["text"], str):
                item["reasoning_content"] = event["text"]
                item["text"] = event["text"]
            if "summary" in event:
                item["summary"] = event["summary"]
            return

        content = item.setdefault("content", [])
        content_index = int(event.get("content_index", 0))
        while len(content) <= content_index:
            content.append({})
        part = content[content_index]
        if "text" in event and isinstance(event["text"], str):
            part["type"] = part.get("type", "output_text")
            part["text"] = event["text"]
        if "part" in event and isinstance(event["part"], dict):
            content[content_index] = self.deep_merge_dicts(part, event["part"])

    def deep_merge_dicts(self, base: dict, incoming: dict) -> dict:
        merged = dict(base)
        for key, value in incoming.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self.deep_merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def ensure_models_seeded(self) -> None:
        if self.app.db.list_models():
            return
        try:
            models = self.app.filter_upstream_models(self.app.upstream.fetch_models())
            if models:
                self.app.db.upsert_models(models)
        except Exception as exc:
            print(f"FocusAway model auto-sync failed: {exc}")

    def ensure_model_available(self, model_id: str) -> None:
        if self.app.db.get_model_policy_by_public_id(model_id):
            return
        try:
            models = self.app.filter_upstream_models(self.app.upstream.fetch_models())
            if models:
                self.app.db.upsert_models(models)
        except Exception as exc:
            print(f"FocusAway model lookup sync failed for {model_id}: {exc}")

    def respond_html(self, title: str, body: str) -> None:
        language = self.current_language()
        if language == "en":
            title = EN_REPLACEMENTS.get(title, title)
            for source, target in sorted(EN_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True):
                body = body.replace(source, target)
        payload = html_page(title, body, language)
        self.send_response(200)
        self.maybe_refresh_csrf_cookie()
        self.apply_common_security_headers()
        self.send_header("Connection", "close")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.close_connection = True
        self.wfile.write(payload)


class FocusAwayApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.db = FocusAwayDB(config)
        self.upstream = UpstreamClient(config)
        self._login_failures: dict[str, list[float]] = {}
        self._login_lock = Lock()
        self._live_model_usage: dict[str, dict[str, int]] = defaultdict(dict)
        self._live_model_usage_lock = Lock()

    def allow_login_attempt(self, client_ip: str) -> bool:
        with self._login_lock:
            self._prune_login_failures(client_ip)
            return len(self._login_failures.get(client_ip, [])) < 10

    def record_login_failure(self, client_ip: str) -> None:
        with self._login_lock:
            self._prune_login_failures(client_ip)
            self._login_failures.setdefault(client_ip, []).append(time.time())

    def clear_login_failures(self, client_ip: str) -> None:
        with self._login_lock:
            self._login_failures.pop(client_ip, None)

    def _prune_login_failures(self, client_ip: str) -> None:
        now = time.time()
        entries = [stamp for stamp in self._login_failures.get(client_ip, []) if now - stamp < 600]
        if entries:
            self._login_failures[client_ip] = entries
        else:
            self._login_failures.pop(client_ip, None)

    def _live_usage_now(self) -> datetime:
        return datetime.now(ZoneInfo(self.config.timezone)).replace(minute=0, second=0, microsecond=0)

    def _prune_live_model_usage(self, now: datetime, hours: int = 24) -> None:
        cutoff = now - timedelta(hours=hours - 1)
        remove_models = []
        for model_id, buckets in self._live_model_usage.items():
            stale_keys = [bucket for bucket in buckets if datetime.fromisoformat(bucket) < cutoff]
            for bucket in stale_keys:
                buckets.pop(bucket, None)
            if not buckets:
                remove_models.append(model_id)
        for model_id in remove_models:
            self._live_model_usage.pop(model_id, None)

    def record_live_model_usage(self, model_id: str) -> None:
        now = self._live_usage_now()
        bucket_key = now.isoformat()
        with self._live_model_usage_lock:
            self._prune_live_model_usage(now)
            model_buckets = self._live_model_usage.setdefault(model_id, {})
            model_buckets[bucket_key] = model_buckets.get(bucket_key, 0) + 1

    def live_model_usage_series(self, hours: int = 24) -> dict[str, list[dict]]:
        now = self._live_usage_now()
        start_time = now - timedelta(hours=hours - 1)
        with self._live_model_usage_lock:
            self._prune_live_model_usage(now, hours)
            usage_snapshot = {model_id: dict(buckets) for model_id, buckets in self._live_model_usage.items()}

        series_by_model: dict[str, list[dict]] = {}
        for model_id, buckets in usage_snapshot.items():
            series = []
            for offset in range(hours):
                point = start_time + timedelta(hours=offset)
                key = point.isoformat()
                series.append(
                    {
                        "date": key,
                        "label": point.strftime("%H:%M"),
                        "count": buckets.get(key, 0),
                    }
                )
            series_by_model[model_id] = series
        return series_by_model

    def filter_upstream_models(self, models: list[dict]) -> list[dict]:
        if self.db.get_setting("exclude_assistant_models", "0") != "1":
            return models
        filtered = []
        for model in models:
            identifier = str(model.get("id") or model.get("name") or "").strip().lower()
            if "assistant" in identifier:
                continue
            filtered.append(model)
        return filtered

    def make_server(self) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer((self.config.host, self.config.port), FocusAwayHandler)
        server.app = self  # type: ignore[attr-defined]
        return server

    def run(self) -> None:
        self.db.ensure_weekly_reset()
        server = self.make_server()
        print(f"FocusAway listening on http://{self.config.host}:{self.config.port}")
        print(f"Proxy upstream: {self.config.upstream_base_url}")
        server.serve_forever()
