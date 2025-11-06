"""
Utility functions to infer estimated cost from model usage and pricing.
"""


def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    else:
        return str(num)


def format_cost(cost):
    if cost == 0:
        return "~$0.00"
    return f"~${cost:.2f}"


def calculate_total_cost(tokens_by_model):
    total = 0
    for model, data in tokens_by_model.items():
        cost_input = data.get("cost_input", 0)
        cost_output = data.get("cost_output", 0)
        total += cost_input + cost_output
    return total


def format_time_remaining(seconds):
    if seconds <= 0:
        return "expired"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def format_duration(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def calculate_7d_tokens_with_costs(period_data):
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
