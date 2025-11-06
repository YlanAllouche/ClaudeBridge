from datetime import datetime

import pyhtml as p
import pyhtml_cem.webawesome.components as wa


def _calculate_7d_tokens_with_costs(period_data):
    """Calculate tokens with costs for a 7d period from all its 5h sessions"""
    tokens_by_model = {}
    for model, data in period_data.get("tokens_by_model", {}).items():
        tokens_by_model[model] = {
            "input": data.get("input", 0),
            "output": data.get("output", 0),
        }

    cost_by_model = {}

    if period_data.get("current_5h_session"):
        for model, data in (
            period_data["current_5h_session"].get("tokens_by_model", {}).items()
        ):
            if model not in cost_by_model:
                cost_by_model[model] = {"cost_input": 0, "cost_output": 0}
            cost_by_model[model]["cost_input"] += data.get("cost_input", 0)
            cost_by_model[model]["cost_output"] += data.get("cost_output", 0)

    for session in period_data.get("past_5h_sessions", []):
        for model, data in session.get("tokens_by_model", {}).items():
            if model not in cost_by_model:
                cost_by_model[model] = {"cost_input": 0, "cost_output": 0}
            cost_by_model[model]["cost_input"] += data.get("cost_input", 0)
            cost_by_model[model]["cost_output"] += data.get("cost_output", 0)

    for model in tokens_by_model:
        if model in cost_by_model:
            tokens_by_model[model]["cost_input"] = cost_by_model[model]["cost_input"]
            tokens_by_model[model]["cost_output"] = cost_by_model[model]["cost_output"]

    return tokens_by_model
