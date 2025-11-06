"""Helper functions for session stats in usage UI"""

from typing import Any, Dict, Optional

import pyhtml as p
import pyhtml_cem.webawesome.components as wa


def format_duration(seconds: int) -> str:
    """Format duration in human-readable form"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_countdown(seconds: int) -> str:
    """Format seconds into human-readable countdown"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def create_ooq_timer_display(timer_info: Optional[Dict[str, Any]], is_5h: bool = True):
    """Create UI element for OOQ timer

    For 5h timer:
    - green_countdown: Active session (green)
    - ready: Session ready (green)
    - red_countdown: 5h OOQ, waiting for reset (red)
    - locked_by_7d: Locked by 7d quota (red, shows 7d reset date)

    For 7d timer:
    - Shows date
    - countdown: Before reset (warning)
    - ready: After reset (success)
    - unknown: No date set (neutral)
    """
    if not timer_info:
        return wa.badge("Unknown", variant="neutral")

    status = timer_info.get("status")

    if is_5h:
        # 5-hour timer logic
        if status == "green_countdown":
            seconds = timer_info["seconds_remaining"]
            time_str = format_countdown(seconds)
            return wa.badge(f" {time_str} left", variant="success")
        elif status == "ready":
            return wa.badge(" Ready", variant="success")
        elif status == "red_countdown":
            seconds = timer_info["seconds_remaining"]
            time_str = format_countdown(seconds)
            return wa.badge(f" Locked {time_str}", variant="danger")
        elif status == "locked_by_7d":
            # Locked by 7d quota - show as red with date instead of countdown
            reset_at = timer_info.get("reset_at")
            if reset_at:
                from datetime import datetime

                dt = datetime.fromtimestamp(reset_at)
                date_str = dt.strftime("%m/%d %I:%M%p")
                return wa.badge(f"7d Lock until {date_str}", variant="danger")
            else:
                return wa.badge("Locked by 7d", variant="danger")
        else:
            return wa.badge("Unknown", variant="neutral")
    else:
        # 7-day timer logic (show as date)
        if status == "unknown":
            return wa.badge("Unknown", variant="neutral")
        elif status == "ready":
            return wa.badge("Ready", variant="success")
        elif status == "countdown":
            reset_at = timer_info.get("reset_at")
            is_predicted = timer_info.get("is_predicted", False)
            if reset_at:
                from datetime import datetime

                dt = datetime.fromtimestamp(reset_at)
                date_str = dt.strftime("%m/%d/%Y %I:%M %p")

                if is_predicted:
                    return wa.badge(f" ~{date_str} (predicted)", variant="neutral")
                else:
                    return wa.badge(f" {date_str}", variant="warning")
            else:
                return wa.badge("Unknown", variant="neutral")
        else:
            return wa.badge("Unknown", variant="neutral")


def create_session_stat_pill(
    label: str, value, icon_name: str, color: str = "cloud-dark"
):
    return p.div(
        p.div(
            wa.icon(name=icon_name, class_=f"text-sm text-{color}"),
            p.span(label, class_="text-xs text-cloud-dark ml-1"),
            class_="flex items-center mb-1",
        ),
        p.div(str(value), class_="text-xl font-bold text-dark font-heading"),
        class_="bg-white p-3 rounded-material shadow-warm-sm border border-cloud-light",
    )


def create_session_stats_section(
    session_stats: Optional[Dict[str, Any]], account_info: Optional[Dict[str, Any]]
):
    if not session_stats:
        return wa.callout(
            wa.icon(slot="icon", name="info-circle"),
            "No active session - waiting for first request",
            variant="neutral",
            open=True,
        )

    account_name = (
        account_info.get("account_name", "Unknown") if account_info else "Unknown"
    )

    ooq_5h_timer = session_stats.get("ooq_5h_timer", {})
    is_locked = ooq_5h_timer.get("status") in ["red_countdown", "locked_by_7d"]

    # Show duration or locked status
    if is_locked:
        session_duration_display = "Locked"
    else:
        session_duration_display = format_duration(session_stats["session_duration"])

    ooq_5h_display = create_ooq_timer_display(ooq_5h_timer, is_5h=True)
    ooq_7d_display = create_ooq_timer_display(
        session_stats.get("ooq_7d_timer"), is_5h=False
    )

    return wa.card(
        p.h2(
            "Current Session",
            class_="text-2xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.div(
            "Account: ",
            p.strong(account_name, class_="text-leather"),
            class_="text-cloud-dark mb-4",
        ),
        p.div(
            create_session_stat_pill("Duration", session_duration_display, "clock"),
            create_session_stat_pill(
                "Requests (OK)", session_stats["requests_ok"], "check-circle", "olive"
            ),
            create_session_stat_pill(
                "Requests (Error)",
                session_stats["requests_error"],
                "exclamation-circle",
                "coral",
            ),
            create_session_stat_pill(
                "Requests (Quota)", session_stats["requests_quota"], "ban", "clay"
            ),
            create_session_stat_pill(
                "Input Tokens",
                f"{session_stats['tokens_input']:,}",
                "arrow-down-circle",
            ),
            create_session_stat_pill(
                "Output Tokens",
                f"{session_stats['tokens_output']:,}",
                "arrow-up-circle",
            ),
            class_="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3 mb-4",
        ),
        p.div(
            p.div(
                p.span("5h Quota: ", class_="text-cloud-dark font-semibold mr-2"),
                ooq_5h_display,
                class_="mb-2",
            ),
            p.div(
                p.span("7d Quota: ", class_="text-cloud-dark font-semibold mr-2"),
                ooq_7d_display,
            ),
            class_="mt-4 pt-4 border-t border-cloud-light",
        ),
        class_="bg-ivory-light rounded-card shadow-warm-lg mb-8",
    )
