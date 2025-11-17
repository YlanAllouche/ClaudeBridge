from datetime import datetime
import time

import pyhtml as p
import pyhtml_cem.webawesome.components as wa
from pyhtml_htmx import hx

from . import usage_components, usage_formatters

format_number = usage_formatters.format_number
format_time_remaining = usage_formatters.format_time_remaining
format_duration = usage_formatters.format_duration
format_cost = usage_formatters.format_cost
calculate_total_cost = usage_formatters.calculate_total_cost
calculate_7d_tokens_with_costs = usage_formatters.calculate_7d_tokens_with_costs
create_stat_card = usage_components.create_stat_card
create_small_stat = usage_components.create_small_stat
create_token_breakdown_by_model = usage_components.create_token_breakdown_by_model
create_token_breakdown_by_user = usage_components.create_token_breakdown_by_user
create_requests_by_user = usage_components.create_requests_by_user
create_errors_by_type = usage_components.create_errors_by_type
get_termination_badge = usage_components.get_termination_badge


def create_usage_page(metrics_summary, web_usage_data=None, account_name=None):
    return p.div(
        p.div(
            p.h1(
                "Usage & Metrics",
                class_="text-3xl font-bold text-dark m-0 font-heading",
            ),
            p.p(
                "Monitor usage per users and models during a session quantified in tokens i/o",
                class_="text-cloud-dark mt-2 mb-0",
            ),
            class_="mb-8",
        ),
        create_usage_content(metrics_summary, web_usage_data, account_name),
    )


def create_web_session_stats(web_usage_data, account_name, metrics_summary):
    """Create real usage stats from Claude.ai web session polling"""
    if not web_usage_data:
        return p.div()

    return p.div(
        p.h2("Real Usage", class_="text-xl font-bold text-dark m-0 mb-2 font-heading"),
        p.p(
            f"{account_name}'s web session" if account_name else "claude.ai",
            class_="text-xs text-cloud-dark mb-3",
        ),
        p.div(
            id="real-usage-content",
            **hx(
                get="/app/usage/real", trigger="every 5s", swap="innerHTML"
            ),  # pyright: ignore
        )(create_web_session_stats_content(web_usage_data, metrics_summary)),
    )





def create_web_session_stats_content(web_usage_data, metrics_summary):
    """Create the polled content for real usage stats"""
    five_hour = web_usage_data.get("five_hour", {})
    seven_day = web_usage_data.get("seven_day", {})

    five_hour_util = five_hour.get("utilization", 0) if five_hour else 0
    seven_day_util = seven_day.get("utilization", 0) if seven_day else 0

    # Get countdown from metrics_summary (same as shown in current 5h/7d sections)
    current_7d = metrics_summary.get("current_7d_period")
    current_5h = current_7d.get("current_5h_session") if current_7d else None

    five_hour_countdown = None
    seven_day_countdown = None
    five_hour_cost = None
    seven_day_cost = None

    if current_5h:
        time_remaining_5h = current_5h.get("time_remaining", 0)
        if time_remaining_5h > 0:
            five_hour_countdown = format_time_remaining(time_remaining_5h)

        cost_5h = calculate_total_cost(current_5h.get("tokens_by_model", {}))
        if cost_5h > 0:
            five_hour_cost = format_cost(cost_5h)

    if current_7d:
        time_remaining_7d = current_7d.get("time_remaining", 0)
        if time_remaining_7d > 0:
            seven_day_countdown = format_time_remaining(time_remaining_7d)

        cost_7d_current = (
            calculate_total_cost(current_5h.get("tokens_by_model", {}))
            if current_5h
            else 0
        )
        for past_session in current_7d.get("past_5h_sessions", []):
            cost_7d_current += calculate_total_cost(
                past_session.get("tokens_by_model", {})
            )
        if cost_7d_current > 0:
            seven_day_cost = format_cost(cost_7d_current)

    return p.div(
        p.div(
            p.div(
                p.div(
                    wa.icon(name="clock", class_="text-sm text-cloud-dark mr-2"),
                    p.span(
                        f"5h Usage{' - ' + five_hour_countdown if five_hour_countdown else ''}{' - ' + five_hour_cost if five_hour_cost else ''}",
                        class_="text-xs font-semibold text-dark",
                    ),
                    class_="flex items-center",
                ),
                p.span(
                    f"{five_hour_util}%",
                    class_="text-xs font-bold text-dark ml-auto",
                ),
                class_="flex items-center mb-1",
            ),
            wa.progress_bar(
                value=five_hour_util,  # pyright: ignore
                style=f"--indicator-color: {'#d97757' if five_hour_util >= 90 else ('#d4a27f' if five_hour_util >= 70 else '#788c5d')}; --height: 8px;",
            ),
            class_="mb-1",
        ),
        p.div(
            p.div(
                p.div(
                    wa.icon(name="calendar", class_="text-sm text-cloud-dark mr-2"),
                    p.span(
                        f"7d Usage{' - ' + seven_day_countdown if seven_day_countdown else ''}{' - ' + seven_day_cost if seven_day_cost else ''}",
                        class_="text-xs font-semibold text-dark",
                    ),
                    class_="flex items-center",
                ),
                p.span(
                    f"{seven_day_util}%",
                    class_="text-xs font-bold text-dark ml-auto",
                ),
                class_="flex items-center mb-1",
            ),
            wa.progress_bar(
                value=seven_day_util,
                style=f"--indicator-color: {'#d97757' if seven_day_util >= 90 else ('#d4a27f' if seven_day_util >= 70 else '#788c5d')}; --height: 8px;",
            ),
        ),
        class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
    )


def create_usage_content(metrics_summary, web_usage_data=None, account_name=None):
    has_web_data = web_usage_data is not None
    global_data = metrics_summary.get("global", {})

    return p.div(
        p.div(
            p.div(
                (
                    create_web_session_stats(
                        web_usage_data, account_name, metrics_summary
                    )
                    if has_web_data
                    else p.div()
                ),
                create_global_tokens_by_model(
                    global_data.get("tokens_by_model", {}), metrics_summary
                ),
                class_="space-y-6",
            ),
            create_global_stats(global_data),
            class_="grid lg:grid-cols-2 gap-6 mb-8" if has_web_data else "mb-8",
        ),
        create_current_7d_period(metrics_summary.get("current_7d_period")),
        create_past_7d_periods(metrics_summary.get("past_7d_periods", [])),
    )


def create_global_tokens_by_model(tokens_by_model, metrics_summary=None):
    """Standalone card for global tokens by model"""
    if not tokens_by_model:
        return p.div()

    cost_by_model = {}
    if metrics_summary:
        current_7d = metrics_summary.get("current_7d_period")
        if current_7d:
            if current_7d.get("current_5h_session"):
                for model, data in (
                    current_7d["current_5h_session"].get("tokens_by_model", {}).items()
                ):
                    if model not in cost_by_model:
                        cost_by_model[model] = {"cost_input": 0, "cost_output": 0}
                    cost_by_model[model]["cost_input"] += data.get("cost_input", 0)
                    cost_by_model[model]["cost_output"] += data.get("cost_output", 0)

            for session in current_7d.get("past_5h_sessions", []):
                for model, data in session.get("tokens_by_model", {}).items():
                    if model not in cost_by_model:
                        cost_by_model[model] = {"cost_input": 0, "cost_output": 0}
                    cost_by_model[model]["cost_input"] += data.get("cost_input", 0)
                    cost_by_model[model]["cost_output"] += data.get("cost_output", 0)

        for period in metrics_summary.get("past_7d_periods", []):
            for session in period.get("past_5h_sessions", []):
                for model, data in session.get("tokens_by_model", {}).items():
                    if model not in cost_by_model:
                        cost_by_model[model] = {"cost_input": 0, "cost_output": 0}
                    cost_by_model[model]["cost_input"] += data.get("cost_input", 0)
                    cost_by_model[model]["cost_output"] += data.get("cost_output", 0)

    tokens_with_costs = {}
    for model, data in tokens_by_model.items():
        tokens_with_costs[model] = {
            "input": data.get("input", 0),
            "output": data.get("output", 0),
        }
        if model in cost_by_model:
            tokens_with_costs[model]["cost_input"] = cost_by_model[model]["cost_input"]
            tokens_with_costs[model]["cost_output"] = cost_by_model[model][
                "cost_output"
            ]

    return p.div(
        p.h2(
            "Tokens by Model",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p("All-time usage", class_="text-xs text-cloud-dark mb-3"),
        p.div(
            create_token_breakdown_by_model(tokens_with_costs, "", small=False),
            class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
        ),
    )


def create_global_stats(global_data):
    requests = global_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    tokens_by_model = global_data.get("tokens_by_model", {})
    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    return p.div(
        p.h2(
            "Global Usage", class_="text-xl font-bold text-dark m-0 mb-2 font-heading"
        ),
        p.p("All-time statistics", class_="text-xs text-cloud-dark mb-3"),
        p.div(
            p.div(
                create_stat_card("Total", total, "list", "primary"),
                create_stat_card(
                    "Success", requests.get("success", 0), "check", "success"
                ),
                create_stat_card(
                    "OOQ",
                    requests.get("ooq", 0),
                    "clock",
                    "warning",
                ),
                create_stat_card(
                    "Errors",
                    requests.get("error", 0),
                    "triangle-exclamation",
                    "danger",
                ),
                create_stat_card(
                    "Tokens In", format_number(total_input), "arrow-up", "success"
                ),
                create_stat_card(
                    "Tokens Out", format_number(total_output), "arrow-down", "primary"
                ),
                class_="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-2",
            ),
            create_token_breakdown_by_user(
                global_data.get("tokens_by_user", {}), "Tokens by User"
            ),
            create_requests_by_user(global_data.get("requests_by_user", {})),
            create_errors_by_type(global_data.get("errors_by_type", {})),
            class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
        ),
    )


def create_current_7d_period(period_data):
    if not period_data:
        return p.div()

    start = period_data.get("start", 0)
    end_inferred = period_data.get("end_inferred", 0)
    end_confirmed = period_data.get("end_confirmed")
    status = period_data.get("status", "unknown")
    time_remaining = period_data.get("time_remaining", 0)

    end_timestamp = end_confirmed or end_inferred

    requests = period_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    tokens_by_model = period_data.get("tokens_by_model", {})
    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    total_cost_7d = 0
    if period_data.get("current_5h_session"):
        total_cost_7d += calculate_total_cost(
            period_data["current_5h_session"].get("tokens_by_model", {})
        )
    for past_session in period_data.get("past_5h_sessions", []):
        total_cost_7d += calculate_total_cost(past_session.get("tokens_by_model", {}))

    return p.div(
        wa.details(
            p.div(
                p.span(
                    "Current 7d Period",
                    class_="text-xl font-bold text-dark font-heading mr-3",
                ),
                p.span(
                    datetime.fromtimestamp(start).strftime("%b %d"),
                    class_="text-sm text-dark",
                ),
                p.span(" → ", class_="text-xs text-cloud-dark mx-1"),
                p.span(
                    datetime.fromtimestamp(end_timestamp).strftime("%b %d"),
                    class_="text-sm text-dark",
                ),
                (
                    p.span(
                        "Weekly limit" if status == "ooq_7d" else status.upper(),
                        class_=f"text-xs px-1 py-0.5 rounded-full ml-2 {'bg-sky text-white' if status == 'active' else ('bg-clay text-white' if status == 'ooq_7d' else 'bg-cloud-medium text-dark')}",
                    )
                ),
                (
                    p.span(
                        f" - {format_time_remaining(period_data.get('time_elapsed_at_ooq', 0))}",
                        class_="text-xs text-clay ml-1",
                    )
                    if status == "ooq_7d" and period_data.get("time_elapsed_at_ooq")
                    else p.span()
                ),
                p.span(
                    f" • {total} req",
                    class_="text-xs text-cloud-dark ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-up", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_input), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-down", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_output), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                (
                    p.span(
                        f" • {format_cost(total_cost_7d)}",
                        class_="text-xs text-sky ml-2 font-semibold",
                    )
                    if total_cost_7d > 0
                    else p.span()
                ),
                class_="flex items-center flex-wrap",
                slot="summary",
            ),
            p.div(
                p.div(
                    create_stat_card("Total", total, "list", "primary"),
                    create_stat_card(
                        "Success", requests.get("success", 0), "check", "success"
                    ),
                    create_stat_card(
                        "OOQ",
                        requests.get("ooq", 0),
                        "clock",
                        "warning",
                    ),
                    create_stat_card(
                        "Error",
                        requests.get("error", 0),
                        "triangle-exclamation",
                        "danger",
                    ),
                    create_stat_card(
                        "Tokens In", format_number(total_input), "arrow-up", "success"
                    ),
                    create_stat_card(
                        "Tokens Out",
                        format_number(total_output),
                        "arrow-down",
                        "primary",
                    ),
                    class_="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-2",
                ),
                wa.details(
                    p.div("Show Full 7d Stats", slot="summary"),
                    p.div(
                        create_token_breakdown_by_model(
                            calculate_7d_tokens_with_costs(period_data),
                            "Tokens by Model",
                        ),
                        create_token_breakdown_by_user(
                            period_data.get("tokens_by_user", {}), "Tokens by User"
                        ),
                        class_="mb-1",
                    ),
                    open=False,
                ),
                create_current_5h_session(period_data.get("current_5h_session")),
                create_past_5h_sessions(period_data.get("past_5h_sessions", [])),
                class_="bg-white rounded-card shadow-warm-md p-3 border border-cloud-light mt-3",
            ),
            open=True,
        ),
        class_="mb-6",
    )


def create_current_5h_session(session_data):
    if not session_data:
        return p.div()

    session_id = session_data.get("session_id", "unknown")
    start = session_data.get("start", 0)
    end_inferred = session_data.get("end_inferred", 0)
    end_confirmed = session_data.get("end_confirmed")
    status = session_data.get("status", "unknown")
    time_remaining = session_data.get("time_remaining", 0)

    end_timestamp = end_confirmed or end_inferred

    requests = session_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    tokens_by_model = session_data.get("tokens_by_model", {})
    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    total_cost_5h = calculate_total_cost(tokens_by_model)

    status_color_map = {
        "active": "bg-sky text-white",
        "ooq_5h": "bg-clay text-white",
        "ooq_7d": "bg-clay text-white",
        "blocked_by_7d": "bg-clay text-white",
        "ready": "bg-olive text-white",
    }
    status_color = status_color_map.get(status, "bg-kraft text-white")

    return p.div(
        p.div(
            p.h3(
                f"Current 5h Session{' - ' + format_time_remaining(time_remaining) if time_remaining > 0 else ''}{' - ' + format_cost(total_cost_5h) if total_cost_5h > 0 else ''}",
                class_="text-lg font-bold text-dark m-0 font-heading",
            ),
            (
                p.p(
                    f"{datetime.fromtimestamp(end_timestamp).strftime('%b %d %H:%M')} end time",
                    class_="text-xs text-cloud-dark m-0",
                )
                if time_remaining > 0
                else p.div()
            ),
            class_="mb-2 mt-2",
        ),
        p.div(
            p.div(
                p.span(
                    datetime.fromtimestamp(start).strftime("%b %d %H:%M"),
                    class_="text-xs text-dark",
                ),
                p.span(" → ", class_="text-xs text-cloud-dark mx-1"),
                p.span(
                    datetime.fromtimestamp(end_timestamp).strftime("%b %d %H:%M"),
                    class_="text-xs text-dark",
                ),
                p.span(
                    f" ({' ' if end_confirmed else '~'})",
                    class_="text-xs text-cloud-dark ml-1",
                ),
                p.span(
                    (
                        "Limited"
                        if status == "ooq_5h"
                        else (
                            "Weekly limit"
                            if status == "ooq_7d"
                            else status.replace("_", " ").upper()
                        )
                    ),
                    class_=f"text-xs px-1 py-0.5 rounded-full ml-2 {status_color}",
                ),
                (
                    p.span(
                        f" - {format_time_remaining(session_data.get('time_elapsed_at_ooq', 0))}",
                        class_="text-xs text-clay ml-1",
                    )
                    if status in ["ooq_5h", "ooq_7d"]
                    and session_data.get("time_elapsed_at_ooq")
                    else p.span()
                ),
                class_="mb-3 flex items-center flex-wrap",
            ),
            p.div(
                create_small_stat("Total", total, "list"),
                create_small_stat("OK", requests.get("success", 0), "check"),
                create_small_stat("OOQ", requests.get("ooq", 0), "clock"),
                create_small_stat(
                    "Err", requests.get("error", 0), "triangle-exclamation"
                ),
                create_small_stat("In", format_number(total_input), "arrow-up"),
                create_small_stat("Out", format_number(total_output), "arrow-down"),
                class_="grid grid-cols-3 lg:grid-cols-6 gap-2 mb-3",
            ),
            wa.details(
                p.div("Show Details", slot="summary"),
                create_session_full_details(session_data),
                open=True,
            ),
            class_="bg-ivory-light rounded-card shadow-sm p-3 border border-cloud-light",
        ),
        class_="mb-3",
    )


def create_past_5h_sessions(sessions):
    if not sessions:
        return p.div()

    return p.div(
        p.h3(
            f"Past 5h Sessions ({len(sessions)})",
            class_="text-base font-bold text-dark m-0 mb-2 mt-2 font-heading",
        ),
        *[
            create_past_5h_session_card(session, i)
            for i, session in enumerate(sessions[:10])
        ],
        class_="mb-2 space-y-2",
    )


def create_past_5h_session_card(session_data, index):
    """Create a collapsible card for a past 5h session"""
    start = session_data.get("start", 0)
    end_inferred = session_data.get("end_inferred", 0)
    end_confirmed = session_data.get("end_confirmed")
    termination_reason = session_data.get("termination_reason")

    end_timestamp = end_confirmed or end_inferred
    duration = end_timestamp - start if end_timestamp else 0

    requests = session_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    tokens_by_model = session_data.get("tokens_by_model", {})
    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    total_cost = calculate_total_cost(tokens_by_model)

    return p.div(
        wa.details(
            p.div(
                p.span(
                    datetime.fromtimestamp(start).strftime("%b %d %H:%M"),
                    class_="text-xs text-dark mr-3",
                ),
                get_termination_badge(
                    termination_reason, session_data.get("time_elapsed_at_ooq")
                ),
                p.span(
                    f" • {total} req",
                    class_="text-xs text-cloud-dark ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-up", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_input), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-down", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_output), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                (
                    p.span(
                        f" • {format_cost(total_cost)}",
                        class_="text-xs text-sky ml-2 font-semibold",
                    )
                    if total_cost > 0
                    else p.span()
                ),
                class_="flex items-center",
                slot="summary",
            ),
            p.div(
                create_session_basic_summary(session_data),
                p.div(create_session_full_details(session_data), class_="mt-3"),
                class_="mt-2 p-3",
            ),
            open=False,
        ),
        class_="bg-white rounded-card shadow-sm p-2 border border-cloud-light",
    )


def create_past_5h_session_row(session_data, index):
    start = session_data.get("start", 0)
    end_inferred = session_data.get("end_inferred", 0)
    end_confirmed = session_data.get("end_confirmed")

    end_timestamp = end_confirmed or end_inferred
    duration = end_timestamp - start if end_timestamp else 0

    requests = session_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    return p.tr(
        p.td(
            datetime.fromtimestamp(start).strftime("%b %d %H:%M"),
            class_="text-xs text-dark py-2 px-3",
        ),
        p.td(format_duration(duration), class_="text-xs text-cloud-dark py-2 px-3"),
        p.td(str(total), class_="text-xs text-dark font-semibold text-right py-2 px-3"),
        p.td(
            str(requests.get("success", 0)),
            class_="text-xs text-olive font-semibold text-right py-2 px-3",
        ),
        p.td(
            str(requests.get("error", 0)),
            class_="text-xs text-clay font-semibold text-right py-2 px-3",
        ),
        p.td(
            str(requests.get("ooq", 0)),
            class_="text-xs text-kraft font-semibold text-right py-2 px-3",
        ),
        class_=f"{'bg-ivory-light' if index % 2 == 1 else 'bg-white'} border-b border-cloud-light",
    )


def create_past_7d_periods(periods):
    if not periods:
        return p.div()

    return p.div(
        p.h2(
            f"Past 7d Periods ({len(periods)})",
            class_="text-xl font-bold text-dark m-0 mb-3 font-heading",
        ),
        p.div(
            *[
                create_past_7d_period_card(period, i)
                for i, period in enumerate(periods[:5])
            ],
            class_="space-y-3",
        ),
        class_="mb-8",
    )


def create_past_7d_period_card(period_data, index):
    start = period_data.get("start", 0)
    end_confirmed = period_data.get("end_confirmed")
    end_inferred = period_data.get("end_inferred", 0)
    end_timestamp = end_confirmed or end_inferred
    termination_reason = period_data.get("termination_reason")

    requests = period_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    tokens_by_model = period_data.get("tokens_by_model", {})
    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    past_sessions = period_data.get("past_5h_sessions", [])

    total_cost_7d = sum(
        calculate_total_cost(session.get("tokens_by_model", {}))
        for session in past_sessions
    )

    return p.div(
        wa.details(
            p.div(
                p.span(
                    datetime.fromtimestamp(start).strftime("%b %d"),
                    class_="text-sm font-semibold text-dark",
                ),
                p.span(" → ", class_="text-xs text-cloud-dark mx-1"),
                p.span(
                    datetime.fromtimestamp(end_timestamp).strftime("%b %d"),
                    class_="text-sm text-dark",
                ),
                get_termination_badge(
                    termination_reason, period_data.get("time_elapsed_at_ooq")
                ),
                p.span(
                    f" • {total} req",
                    class_="text-xs text-cloud-dark ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-up", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_input), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                p.span(
                    wa.icon(name="arrow-down", class_="text-xs text-cloud-dark mx-1"),
                    p.span(
                        format_number(total_output), class_="text-xs text-cloud-dark"
                    ),
                    class_="inline-flex items-center ml-2",
                ),
                (
                    p.span(
                        f" • {format_cost(total_cost_7d)}",
                        class_="text-xs text-sky ml-2 font-semibold",
                    )
                    if total_cost_7d > 0
                    else p.span()
                ),
                class_="flex items-center",
                slot="summary",
            ),
            p.div(
                p.div(
                    create_small_stat("Total", total, "list"),
                    create_small_stat("OK", requests.get("success", 0), "check"),
                    create_small_stat("OOQ", requests.get("ooq", 0), "clock"),
                    create_small_stat(
                        "Err", requests.get("error", 0), "triangle-exclamation"
                    ),
                    class_="grid grid-cols-4 gap-2 mb-3",
                ),
                wa.details(
                    p.div("Show Full 7d Stats", slot="summary"),
                    p.div(
                        create_token_breakdown_by_model(
                            calculate_7d_tokens_with_costs(period_data),
                            "Tokens by Model",
                            small=True,
                        ),
                        create_token_breakdown_by_user(
                            period_data.get("tokens_by_user", {}),
                            "Tokens by User",
                            small=True,
                        ),
                    ),
                    open=False,
                ),
                (
                    p.div(
                        p.h4(
                            f"5h Sessions ({len(past_sessions)})",
                            class_="text-xs font-semibold text-dark mb-2 mt-3",
                        ),
                        *[
                            create_past_5h_session_card(session, i)
                            for i, session in enumerate(past_sessions)
                        ],
                        class_="space-y-2",
                    )
                    if past_sessions
                    else p.div()
                ),
                class_="mt-2",
            ),
            open=False,
        ),
        class_="bg-white rounded-card shadow-warm-md p-2 border border-cloud-light",
    )


def create_nested_5h_session_row(session_data, index):
    start = session_data.get("start", 0)
    end_inferred = session_data.get("end_inferred", 0)
    end_confirmed = session_data.get("end_confirmed")

    end_timestamp = end_confirmed or end_inferred
    duration = end_timestamp - start if end_timestamp else 0

    requests = session_data.get("requests", {})
    total = (
        requests.get("success", 0) + requests.get("error", 0) + requests.get("ooq", 0)
    )

    return p.tr(
        p.td(
            datetime.fromtimestamp(start).strftime("%m/%d %H:%M"),
            class_="text-xs text-dark py-1 px-2",
        ),
        p.td(format_duration(duration), class_="text-xs text-cloud-dark py-1 px-2"),
        p.td(str(total), class_="text-xs text-dark font-semibold text-right py-1 px-2"),
        p.td(
            str(requests.get("success", 0)),
            class_="text-xs text-olive text-right py-1 px-2",
        ),
        p.td(
            str(requests.get("error", 0)),
            class_="text-xs text-clay text-right py-1 px-2",
        ),
        p.td(
            str(requests.get("ooq", 0)),
            class_="text-xs text-kraft text-right py-1 px-2",
        ),
        class_=f"{'bg-white' if index % 2 == 1 else 'bg-ivory-light'} border-b border-cloud-light",
    )


def create_session_basic_summary(session_data):
    """Create basic session summary: tokens only"""
    tokens_by_model = session_data.get("tokens_by_model", {})

    total_input = sum(data.get("input", 0) for data in tokens_by_model.values())
    total_output = sum(data.get("output", 0) for data in tokens_by_model.values())

    return p.div(
        p.div(
            create_small_stat("In", format_number(total_input), "arrow-up"),
            create_small_stat("Out", format_number(total_output), "arrow-down"),
            create_small_stat(
                "Total", format_number(total_input + total_output), "layer-group"
            ),
            class_="grid grid-cols-3 gap-2",
        )
    )


def create_session_full_details(session_data):
    """Create full session details: per-model and per-user breakdowns"""
    tokens_by_model = session_data.get("tokens_by_model", {})
    tokens_by_user = session_data.get("tokens_by_user", {})

    return p.div(
        create_token_breakdown_by_model(tokens_by_model, "Tokens by Model", small=True),
        create_token_breakdown_by_user(tokens_by_user, "Tokens by User", small=True),
    )
