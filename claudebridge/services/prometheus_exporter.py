from typing import Any, Dict, Optional


def format_prometheus_metrics(
    summary: Dict[str, Any],
    web_usage_data: Optional[Dict[str, Any]] = None,
    account_name: Optional[str] = None,
) -> str:
    """
    Format metrics summary into Prometheus text format.

    Args:
        summary: Metrics summary from MetricsManager.get_metrics_summary()
        web_usage_data: Optional web session usage data
        account_name: Optional account name for labeling

    Returns:
        Prometheus-formatted metrics as string
    """
    lines = []

    lines.append("# HELP cc_requests_total Total number of requests by status")
    lines.append("# TYPE cc_requests_total counter")
    for status, count in summary["global"]["requests"].items():
        lines.append(f'cc_requests_total{{status="{status}"}} {count}')

    lines.append("")
    lines.append(
        "# HELP cc_tokens_total Total tokens processed globally by model and direction"
    )
    lines.append("# TYPE cc_tokens_total counter")
    for model, tokens in summary["global"]["tokens_by_model"].items():
        lines.append(
            f'cc_tokens_total{{model="{model}",direction="input"}} {tokens["input"]}'
        )
        lines.append(
            f'cc_tokens_total{{model="{model}",direction="output"}} {tokens["output"]}'
        )

    if summary["current_7d_period"]:
        period = summary["current_7d_period"]

        lines.append("")
        lines.append("# HELP cc_7d_status Current 7-day period status (active, ready)")
        lines.append("# TYPE cc_7d_status gauge")
        status_value = 1 if period["status"] == "active" else 0
        lines.append(f'cc_7d_status{{status="{period["status"]}"}} {status_value}')

        lines.append("")
        lines.append(
            "# HELP cc_7d_countdown_seconds Time remaining in current 7-day period"
        )
        lines.append("# TYPE cc_7d_countdown_seconds gauge")
        lines.append(f'cc_7d_countdown_seconds {period["time_remaining"]}')

        lines.append("")
        lines.append(
            "# HELP cc_7d_current_requests Current 7-day period requests by status"
        )
        lines.append("# TYPE cc_7d_current_requests counter")
        for status, count in period["requests"].items():
            lines.append(f'cc_7d_current_requests{{status="{status}"}} {count}')

        lines.append("")
        lines.append("# HELP cc_7d_current_tokens Current 7-day period tokens by model")
        lines.append("# TYPE cc_7d_current_tokens counter")
        for model, tokens in period["tokens_by_model"].items():
            lines.append(
                f'cc_7d_current_tokens{{model="{model}",direction="input"}} {tokens["input"]}'
            )
            lines.append(
                f'cc_7d_current_tokens{{model="{model}",direction="output"}} {tokens["output"]}'
            )

        if period["current_5h_session"]:
            session = period["current_5h_session"]

            lines.append("")
            lines.append(
                "# HELP cc_5h_status Current 5-hour session status (active, ready, blocked_by_7d)"
            )
            lines.append("# TYPE cc_5h_status gauge")
            status_map = {"active": 1, "ready": 0, "blocked_by_7d": 2}
            status_value = status_map.get(session["status"], 0)
            lines.append(f'cc_5h_status{{status="{session["status"]}"}} {status_value}')

            lines.append("")
            lines.append(
                "# HELP cc_5h_countdown_seconds Time remaining in current 5-hour session"
            )
            lines.append("# TYPE cc_5h_countdown_seconds gauge")
            lines.append(f'cc_5h_countdown_seconds {session["time_remaining"]}')

            lines.append("")
            lines.append(
                "# HELP cc_5h_current_requests Current 5-hour session requests by status"
            )
            lines.append("# TYPE cc_5h_current_requests counter")
            for status, count in session["requests"].items():
                lines.append(f'cc_5h_current_requests{{status="{status}"}} {count}')

            lines.append("")
            lines.append(
                "# HELP cc_5h_current_tokens Current 5-hour session tokens by model"
            )
            lines.append("# TYPE cc_5h_current_tokens counter")
            for model, tokens in session["tokens_by_model"].items():
                lines.append(
                    f'cc_5h_current_tokens{{model="{model}",direction="input"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_5h_current_tokens{{model="{model}",direction="output"}} {tokens["output"]}'
                )

        lines.append("")
        lines.append(
            "# HELP cc_5h_session_tokens All 5-hour sessions tokens with full breakdown and costs"
        )
        lines.append("# TYPE cc_5h_session_tokens counter")
        if period["current_5h_session"]:
            session = period["current_5h_session"]
            termination = session.get("termination_reason", "active")
            for model, tokens in session["tokens_by_model"].items():
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{session["session_id"]}",model="{model}",direction="input",status="current",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{session["session_id"]}",model="{model}",direction="output",status="current",termination="{termination}"}} {tokens["output"]}'
                )

                # Add cost metrics if available
                if "cost_input" in tokens and "cost_output" in tokens:
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{session["session_id"]}",model="{model}",direction="cost_input",status="current",termination="{termination}"}} {tokens["cost_input"]}'
                    )
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{session["session_id"]}",model="{model}",direction="cost_output",status="current",termination="{termination}"}} {tokens["cost_output"]}'
                    )
                    total_cost = tokens["cost_input"] + tokens["cost_output"]
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{session["session_id"]}",model="{model}",direction="cost_total",status="current",termination="{termination}"}} {total_cost}'
                    )

            for user, tokens in session.get("tokens_by_user", {}).items():
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{session["session_id"]}",user="{user}",direction="input",status="current",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{session["session_id"]}",user="{user}",direction="output",status="current",termination="{termination}"}} {tokens["output"]}'
                )

        for past_session in period["past_5h_sessions"]:
            termination = past_session.get("termination_reason", "unknown")
            for model, tokens in past_session["tokens_by_model"].items():
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",model="{model}",direction="input",status="past",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",model="{model}",direction="output",status="past",termination="{termination}"}} {tokens["output"]}'
                )

                # Add cost metrics if available
                if "cost_input" in tokens and "cost_output" in tokens:
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",model="{model}",direction="cost_input",status="past",termination="{termination}"}} {tokens["cost_input"]}'
                    )
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",model="{model}",direction="cost_output",status="past",termination="{termination}"}} {tokens["cost_output"]}'
                    )
                    total_cost = tokens["cost_input"] + tokens["cost_output"]
                    lines.append(
                        f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",model="{model}",direction="cost_total",status="past",termination="{termination}"}} {total_cost}'
                    )

            for user, tokens in past_session.get("tokens_by_user", {}).items():
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",user="{user}",direction="input",status="past",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_5h_session_tokens{{session_id="{past_session["session_id"]}",user="{user}",direction="output",status="past",termination="{termination}"}} {tokens["output"]}'
                )

    if summary["past_7d_periods"]:
        lines.append("")
        lines.append(
            "# HELP cc_7d_period_tokens All 7-day periods tokens with full breakdown"
        )
        lines.append("# TYPE cc_7d_period_tokens counter")

        for past_period in summary["past_7d_periods"]:
            period_id = past_period["period_id"]
            termination = past_period.get("termination_reason", "unknown")
            for model, tokens in past_period["tokens_by_model"].items():
                lines.append(
                    f'cc_7d_period_tokens{{period_id="{period_id}",model="{model}",direction="input",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_7d_period_tokens{{period_id="{period_id}",model="{model}",direction="output",termination="{termination}"}} {tokens["output"]}'
                )
            for user, tokens in past_period.get("tokens_by_user", {}).items():
                lines.append(
                    f'cc_7d_period_tokens{{period_id="{period_id}",user="{user}",direction="input",termination="{termination}"}} {tokens["input"]}'
                )
                lines.append(
                    f'cc_7d_period_tokens{{period_id="{period_id}",user="{user}",direction="output",termination="{termination}"}} {tokens["output"]}'
                )

    lines.append("")
    lines.append(
        "# HELP cc_websession_5h_percent Real 5-hour usage percentage from Claude.ai"
    )
    lines.append("# TYPE cc_websession_5h_percent gauge")
    account_label = f'account="{account_name}"' if account_name else ""

    if web_usage_data:
        is_stale = web_usage_data.get("is_stale", False)
        error = web_usage_data.get("error")

        if is_stale and error:
            lines.append(f"cc_websession_5h_percent{{{account_label}}} NaN")
        else:
            five_hour = web_usage_data.get("five_hour", {})
            if five_hour and "utilization" in five_hour:
                lines.append(
                    f'cc_websession_5h_percent{{{account_label}}} {five_hour.get("utilization", 0)}'
                )
            else:
                lines.append(f"cc_websession_5h_percent{{{account_label}}} NaN")
    else:
        lines.append(f"cc_websession_5h_percent{{{account_label}}} NaN")

    lines.append("")
    lines.append(
        "# HELP cc_websession_7d_percent Real 7-day usage percentage from Claude.ai"
    )
    lines.append("# TYPE cc_websession_7d_percent gauge")

    if web_usage_data:
        is_stale = web_usage_data.get("is_stale", False)
        error = web_usage_data.get("error")

        if is_stale and error:
            lines.append(f"cc_websession_7d_percent{{{account_label}}} NaN")
        else:
            seven_day = web_usage_data.get("seven_day", {})
            if seven_day and "utilization" in seven_day:
                lines.append(
                    f'cc_websession_7d_percent{{{account_label}}} {seven_day.get("utilization", 0)}'
                )
            else:
                lines.append(f"cc_websession_7d_percent{{{account_label}}} NaN")
    else:
        lines.append(f"cc_websession_7d_percent{{{account_label}}} NaN")

    lines.append("")
    lines.append(
        "# HELP cc_websession_last_updated_timestamp Timestamp of last successful web session poll"
    )
    lines.append("# TYPE cc_websession_last_updated_timestamp gauge")

    if web_usage_data:
        last_updated = web_usage_data.get("last_updated", 0)
        if last_updated:
            lines.append(
                f"cc_websession_last_updated_timestamp{{{account_label}}} {last_updated}"
            )
        else:
            lines.append(f"cc_websession_last_updated_timestamp{{{account_label}}} 0")
    else:
        lines.append(f"cc_websession_last_updated_timestamp{{{account_label}}} 0")

    lines.append("")
    lines.append(
        "# HELP cc_websession_error_status Whether web session polling is currently failing (0=ok, 1=error)"
    )
    lines.append("# TYPE cc_websession_error_status gauge")

    if web_usage_data:
        is_stale = web_usage_data.get("is_stale", False)
        error = web_usage_data.get("error")
        error_status = 1 if (is_stale and error) else 0
        lines.append(f"cc_websession_error_status{{{account_label}}} {error_status}")
    else:
        lines.append(f"cc_websession_error_status{{{account_label}}} 0")

    lines.append("")
    return "\n".join(lines)
