import pyhtml as p
import pyhtml_cem.webawesome.components as wa

from .usage_formatters import format_number, format_time_remaining

sl_progress_bar = p.create_tag("sl-progress-bar")


def create_stat_card(label, value, icon_name, variant):
    color_classes = {
        "primary": "text-sky border-sky",
        "success": "text-olive border-olive",
        "warning": "text-kraft border-kraft",
        "danger": "text-clay border-clay",
        "neutral": "text-cloud-dark border-cloud-medium",
    }

    color_class = color_classes.get(variant, color_classes["neutral"])
    icon_color, border_color = color_class.split(" ")

    return p.div(
        p.div(
            wa.icon(name=icon_name, class_=f"text-lg {icon_color} mr-2"),
            p.div(str(value), class_="text-lg font-bold text-dark font-heading"),
            class_="flex items-center mb-0.5 p-3",
        ),
        p.div(label, class_="text-xs text-cloud-dark"),
        class_=f"bg-white rounded-card shadow-sm border-t-4 {border_color} p-3",
    )


def create_small_stat(label, value, icon_name=None):
    return p.div(
        p.div(
            (
                wa.icon(name=icon_name, class_="text-sm text-cloud-dark mr-1")
                if icon_name
                else p.span()
            ),
            p.span(str(value), class_="text-base font-bold text-dark font-heading"),
            class_="flex items-center justify-center",
        ),
        p.div(label, class_="text-xs text-cloud-dark"),
        class_="text-center",
    )


def create_token_breakdown_by_model(
    tokens_by_model, title="Token Usage by Model", small=False
):
    if not tokens_by_model:
        return p.div()

    sorted_items = sorted(tokens_by_model.items())

    has_costs = any(
        data.get("cost_input", 0) > 0 or data.get("cost_output", 0) > 0
        for model, data in sorted_items
    )

    title_element = (
        p.h4(
            title,
            class_=f"{'text-sm' if small else 'text-base'} font-semibold text-dark mb-2",
        )
        if title
        else p.div()
    )

    return p.div(
        title_element,
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "Model",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Input",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Output",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Total",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    (
                        p.th(
                            "$",
                            class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                        )
                        if has_costs
                        else p.th()
                    ),
                    class_="border-b-2 border-cloud-light",
                )
            ),
            p.tbody(
                *[
                    p.tr(
                        p.td(model, class_="text-xs text-dark py-2 px-3 font-mono"),
                        p.td(
                            format_number(data.get("input", 0)),
                            class_="text-xs text-olive font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            format_number(data.get("output", 0)),
                            class_="text-xs text-kraft font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            format_number(data.get("input", 0) + data.get("output", 0)),
                            class_="text-xs text-dark font-semibold text-right py-2 px-3",
                        ),
                        (
                            p.td(
                                f"{(data.get('cost_input', 0) + data.get('cost_output', 0)):.2f}",
                                class_="text-xs text-sky font-semibold text-right py-2 px-3",
                            )
                            if has_costs
                            else p.td()
                        ),
                        class_=f"{'bg-ivory-light' if i % 2 == 1 else 'bg-white'} border-b border-cloud-light",
                    )
                    for i, (model, data) in enumerate(sorted_items)
                ]
            ),
            class_="w-full text-xs border-collapse border border-cloud-light rounded-lg overflow-hidden",
        ),
        class_="mb-4" if title else "",
    )


def create_token_breakdown_by_user(
    tokens_by_user, title="Token Usage by User", small=False
):
    if not tokens_by_user:
        return p.div()

    sorted_items = sorted(tokens_by_user.items())

    return p.div(
        p.h4(
            title,
            class_=f"{'text-sm' if small else 'text-base'} font-semibold text-dark mb-2",
        ),
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "User",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Input",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Output",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Total",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    class_="border-b-2 border-cloud-light",
                )
            ),
            p.tbody(
                *[
                    p.tr(
                        p.td(user, class_="text-xs text-dark py-2 px-3 font-mono"),
                        p.td(
                            format_number(data.get("input", 0)),
                            class_="text-xs text-olive font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            format_number(data.get("output", 0)),
                            class_="text-xs text-kraft font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            format_number(data.get("input", 0) + data.get("output", 0)),
                            class_="text-xs text-dark font-semibold text-right py-2 px-3",
                        ),
                        class_=f"{'bg-ivory-light' if i % 2 == 1 else 'bg-white'} border-b border-cloud-light",
                    )
                    for i, (user, data) in enumerate(sorted_items)
                ]
            ),
            class_="w-full text-xs border-collapse border border-cloud-light rounded-lg overflow-hidden",
        ),
        class_="mb-4",
    )


def create_requests_by_user(requests_by_user):
    if not requests_by_user:
        return p.div()

    sorted_items = sorted(requests_by_user.items())

    return p.div(
        p.h4("Requests by User", class_="text-base font-semibold text-dark mb-2"),
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "User",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Success",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Error",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "OOQ",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Total",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    class_="border-b-2 border-cloud-light",
                )
            ),
            p.tbody(
                *[
                    p.tr(
                        p.td(user, class_="text-xs text-dark py-2 px-3 font-mono"),
                        p.td(
                            str(data.get("success", 0)),
                            class_="text-xs text-olive font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            str(data.get("error", 0)),
                            class_="text-xs text-clay font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            str(data.get("ooq", 0)),
                            class_="text-xs text-kraft font-semibold text-right py-2 px-3",
                        ),
                        p.td(
                            str(
                                data.get("success", 0)
                                + data.get("error", 0)
                                + data.get("ooq", 0)
                            ),
                            class_="text-xs text-dark font-semibold text-right py-2 px-3",
                        ),
                        class_=f"{'bg-ivory-light' if i % 2 == 1 else 'bg-white'} border-b border-cloud-light",
                    )
                    for i, (user, data) in enumerate(sorted_items)
                ]
            ),
            class_="w-full text-xs border-collapse border border-cloud-light rounded-lg overflow-hidden",
        ),
        class_="mb-4",
    )


def create_errors_by_type(errors_by_type):
    if not errors_by_type or sum(errors_by_type.values()) == 0:
        return p.div()

    sorted_items = sorted(errors_by_type.items(), key=lambda x: x[1], reverse=True)

    return p.div(
        p.h4("Errors by Type", class_="text-base font-semibold text-dark mb-2"),
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "Error Type",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Count",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    class_="border-b-2 border-cloud-light",
                )
            ),
            p.tbody(
                *[
                    p.tr(
                        p.td(error_type, class_="text-xs text-dark py-2 px-3"),
                        p.td(
                            str(count),
                            class_="text-xs text-clay font-semibold text-right py-2 px-3",
                        ),
                        class_=f"{'bg-ivory-light' if i % 2 == 1 else 'bg-white'} border-b border-cloud-light",
                    )
                    for i, (error_type, count) in enumerate(sorted_items)
                ]
            ),
            class_="w-full text-xs border-collapse border border-cloud-light rounded-lg overflow-hidden",
        ),
        class_="mb-4",
    )


def get_termination_badge(termination_reason, time_elapsed_at_ooq=None):
    if termination_reason == "natural":
        return p.span(
            "Natural", class_="text-xs px-1 py-0.5 rounded-full bg-olive text-white"
        )
    elif termination_reason == "ooq_5h":
        return p.span(
            p.span(
                "5h OOQ", class_="text-xs px-1 py-0.5 rounded-full bg-clay text-white"
            ),
            (
                p.span(
                    f" - {format_time_remaining(time_elapsed_at_ooq)}",
                    class_="text-xs text-clay ml-1",
                )
                if time_elapsed_at_ooq
                else p.span()
            ),
        )
    elif termination_reason == "ooq_7d":
        return p.span(
            p.span(
                "7d OOQ", class_="text-xs px-1 py-0.5 rounded-full bg-clay text-white"
            ),
            (
                p.span(
                    f" - {format_time_remaining(time_elapsed_at_ooq)}",
                    class_="text-xs text-clay ml-1",
                )
                if time_elapsed_at_ooq
                else p.span()
            ),
        )
    elif termination_reason == "rollover":
        return p.span(
            "Rollover", class_="text-xs px-1 py-0.5 rounded-full bg-kraft text-white"
        )
    elif termination_reason is None:
        return p.span(
            "Active", class_="text-xs px-1 py-0.5 rounded-full bg-sky text-white"
        )
    else:
        return p.span(
            str(termination_reason),
            class_="text-xs px-1 py-0.5 rounded-full bg-cloud-medium text-dark",
        )
