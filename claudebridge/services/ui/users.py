import datetime

import pyhtml as p
import pyhtml_cem.webawesome.components as wa
from pyhtml_htmx import hx


def create_users_page(tokens, user_stats=None):
    import pyhtml_cem.webawesome.components as wa

    header = p.div(
        p.h1("Users", class_="text-3xl font-bold text-dark m-0 font-heading"),
        p.p(
            f"Manage {len(tokens)} internal user{'s' if len(tokens) != 1 else ''}",
            class_="text-cloud-dark mt-2 mb-0",
        ),
        class_="mb-8",
    )

    add_user_form = p.div(
        p.h3(
            "Add New User", class_="text-xl font-bold text-dark m-0 mb-4 font-heading"
        ),
        p.form(
            p.div(
                p.input(
                    type="text",
                    placeholder="Enter user name",
                    id="new-user-name",
                    name="name",
                    class_="flex-1 px-4 py-2 border border-cloud-light rounded-xl focus:outline-none focus:border-sky",
                ),
                p.button(
                    "Add User",
                    type="submit",
                    class_="px-6 py-2 bg-sky text-white rounded-xl font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                ),
                class_="flex gap-3 items-center",
            ),
            **hx(  # pyright: ignore
                post="/app/users/add",
                target="#users-table",
                swap="outerHTML",
                select="#users-table",
            ),
            **{
                "hx-on::after-request": "document.getElementById('new-user-name').value='';"
            },
        ),
        class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light mb-6",
    )

    if not tokens:
        return p.div(
            header,
            add_user_form,
            wa.callout(
                wa.icon(slot="icon", name="info-circle"),
                p.strong("No users configured"),
                p.br(),
                "Enter a name above to create your first internal user with an API token",
                variant="success",
                open=True,
            ),
        )

    users_table = create_users_table(tokens, user_stats)

    return p.div(header, add_user_form, users_table)


def create_users_table(tokens, user_stats=None):
    if not tokens:
        return p.div(id="users-table")

    return p.div(
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3 w-8",
                    ),
                    p.th(
                        "User",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Token",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Last Used",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Rate Limits",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Actions",
                        class_="text-right text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    class_="border-b-2 border-cloud-light",
                )
            ),
            p.tbody(
                *[
                    item
                    for i, token in enumerate(tokens)
                    for item in create_user_rows(token, i, user_stats)
                ]
            ),
            class_="w-full text-xs border-collapse",
        ),
        id="users-table",
        class_="bg-white rounded-card shadow-warm-md border border-cloud-light overflow-hidden",
    )


def create_user_rows(token, index, user_stats=None):
    """Creates main row + expandable rate limit form row"""
    name = token.get("name", "unknown")
    token_value = token.get("token", "")
    token_id_safe = token_value[:10] if token_value else f"token-{index}"
    rate_limits = token.get("rate_limits", {})

    last_used_timestamp = None
    last_error_timestamp = None
    status_dot = p.div(
        class_="w-2 h-2 rounded-full bg-cloud-medium", title="Never used"
    )

    if user_stats and name in user_stats:
        last_used_timestamp = user_stats[name].get("last_success_at")
        last_error_timestamp = user_stats[name].get("last_failure_at")

        if last_error_timestamp and (
            not last_used_timestamp or last_error_timestamp > last_used_timestamp
        ):
            status_dot = p.div(
                class_="w-2 h-2 rounded-full bg-clay", title="Last request failed"
            )
        elif last_used_timestamp:
            status_dot = p.div(
                class_="w-2 h-2 rounded-full bg-olive", title="Last request successful"
            )

    truncated_token = (
        token_value[:8] + "..." + token_value[-8:]
        if len(token_value) > 20
        else token_value
    )

    last_used_str = (
        datetime.datetime.fromtimestamp(last_used_timestamp).strftime("%m/%d %H:%M")
        if last_used_timestamp
        else "Never"
    )

    has_limits = bool(rate_limits)
    rate_limits_summary = ""
    if has_limits:
        limits = []
        if "requests_per_minute" in rate_limits:
            limits.append(f"{rate_limits['requests_per_minute']}/min")
        if "requests_per_day" in rate_limits:
            limits.append(f"{rate_limits['requests_per_day']}/day")
        rate_limits_summary = ", ".join(limits[:2]) if limits else "Custom"
    else:
        rate_limits_summary = "None"

    main_row = p.tr(
        p.td(status_dot, class_="py-3 px-3 text-center"),
        p.td(name, class_="text-xs text-dark py-3 px-3 font-semibold"),
        p.td(
            p.div(
                (
                    p.button(
                        p.code(
                            truncated_token,
                            class_="text-xs font-mono text-cloud-dark mr-2",
                        ),
                        wa.icon(name="clipboard", class_="text-xs text-sky"),
                        type="button",
                        class_="flex items-center bg-ivory-light hover:bg-ivory-dark px-2 py-1 rounded transition-colors cursor-pointer border border-cloud-light",
                        onclick=f"navigator.clipboard.writeText('{token_value}').then(() => {{ this.querySelector('wa-icon').setAttribute('name', 'check-circle'); setTimeout(() => this.querySelector('wa-icon').setAttribute('name', 'clipboard'), 2000); }});",
                    )
                    if token_value
                    else p.code(
                        truncated_token, class_="text-xs font-mono text-cloud-dark"
                    )
                ),
                class_="flex items-center",
            ),
            class_="py-3 px-3",
        ),
        p.td(last_used_str, class_="text-xs text-cloud-dark py-3 px-3"),
        p.td(
            p.div(
                p.span(rate_limits_summary, class_="text-xs text-dark mr-2"),
                p.button(
                    wa.icon(name="pencil", class_="text-xs mr-1"),
                    "Edit",
                    type="button",
                    class_="px-2 py-1 bg-sky text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                    **{
                        "onclick": f"document.getElementById('rate-form-row-{token_id_safe}').classList.toggle('hidden')"
                    },
                ),
                class_="flex items-center",
            ),
            class_="py-3 px-3",
        ),
        p.td(
            p.div(
                p.button(
                    "Rotate",
                    type="button",
                    class_="px-3 py-1 bg-kraft text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer mr-1",
                    **hx(
                        post="/app/users/regenerate",
                        vals=f'{{"token": "{token_value}", "name": "{name}"}}',
                        target="#users-table",
                        swap="outerHTML",
                        select="#users-table",
                    ),
                    **{"hx-confirm": f"Regenerate token for {name}?"},
                ),
                p.button(
                    "Delete",
                    type="button",
                    class_="px-3 py-1 bg-clay text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                    **hx(
                        post="/app/users/delete",
                        vals=f'{{"token": "{token_value}"}}',
                        target="#users-table",
                        swap="outerHTML",
                        select="#users-table",
                    ),
                    **{"hx-confirm": f"Delete user {name}?"},
                ),
                class_="flex gap-1 justify-end",
            ),
            class_="py-3 px-3",
        ),
        class_="border-b border-cloud-light hover:bg-ivory-light transition-colors",
    )

    form_row = p.tr(
        p.td(
            create_rate_limits_form_inline(
                rate_limits, token_value, name, token_id_safe, has_limits
            ),
            colspan="6",
            class_="p-0",
        ),
        id=f"rate-form-row-{token_id_safe}",
        class_="hidden border-b-2 border-cloud-medium",
    )

    return [main_row, form_row]


def create_rate_limits_form_inline(
    rate_limits, token_value, name, token_id_safe, has_limits
):
    """Inline rate limit form for table row"""
    return p.form(
        p.div(
            p.h4("Rate Limits", class_="text-sm font-semibold text-dark mb-3"),
            p.div(
                p.div(
                    p.label(
                        "Requests/Min", class_="text-xs text-cloud-dark block mb-1"
                    ),
                    p.input(
                        type="number",
                        name="requests_per_minute",
                        placeholder="60",
                        value=(
                            str(rate_limits.get("requests_per_minute", ""))
                            if rate_limits.get("requests_per_minute")
                            else ""
                        ),
                        class_="w-full px-2 py-1 border border-cloud-light rounded text-xs",
                    ),
                ),
                p.div(
                    p.label(
                        "Requests/Hour", class_="text-xs text-cloud-dark block mb-1"
                    ),
                    p.input(
                        type="number",
                        name="requests_per_hour",
                        placeholder="1000",
                        value=(
                            str(rate_limits.get("requests_per_hour", ""))
                            if rate_limits.get("requests_per_hour")
                            else ""
                        ),
                        class_="w-full px-2 py-1 border border-cloud-light rounded text-xs",
                    ),
                ),
                p.div(
                    p.label(
                        "Requests/Day", class_="text-xs text-cloud-dark block mb-1"
                    ),
                    p.input(
                        type="number",
                        name="requests_per_day",
                        placeholder="10000",
                        value=(
                            str(rate_limits.get("requests_per_day", ""))
                            if rate_limits.get("requests_per_day")
                            else ""
                        ),
                        class_="w-full px-2 py-1 border border-cloud-light rounded text-xs",
                    ),
                ),
                p.div(
                    p.label("Tokens/Min", class_="text-xs text-cloud-dark block mb-1"),
                    p.input(
                        type="number",
                        name="tokens_per_minute",
                        placeholder="100000",
                        value=(
                            str(rate_limits.get("tokens_per_minute", ""))
                            if rate_limits.get("tokens_per_minute")
                            else ""
                        ),
                        class_="w-full px-2 py-1 border border-cloud-light rounded text-xs",
                    ),
                ),
                p.div(
                    p.label("Tokens/Day", class_="text-xs text-cloud-dark block mb-1"),
                    p.input(
                        type="number",
                        name="tokens_per_day",
                        placeholder="1000000",
                        value=(
                            str(rate_limits.get("tokens_per_day", ""))
                            if rate_limits.get("tokens_per_day")
                            else ""
                        ),
                        class_="w-full px-2 py-1 border border-cloud-light rounded text-xs",
                    ),
                ),
                class_="grid grid-cols-5 gap-2 mb-3",
            ),
            p.div(
                p.input(type="hidden", name="token", value=token_value),
                p.input(type="hidden", name="name", value=name),
                p.button(
                    "Cancel",
                    type="button",
                    class_="px-3 py-1 bg-cloud-medium text-white rounded-lg text-xs font-semibold hover:bg-opacity-80",
                    **{
                        "onclick": f"document.getElementById('rate-form-row-{token_id_safe}').classList.add('hidden')"
                    },
                ),
                p.button(
                    "Save",
                    type="submit",
                    class_="px-3 py-1 bg-olive text-white rounded-lg text-xs font-semibold hover:bg-opacity-80",
                ),
                (
                    p.button(
                        "Remove All",
                        type="button",
                        class_="px-3 py-1 bg-clay text-white rounded-lg text-xs font-semibold hover:bg-opacity-80",
                        **hx(
                            post="/app/users/rate-limits/remove",
                            vals=f'{{"token": "{token_value}"}}',
                            target="#users-table",
                            swap="outerHTML",
                            select="#users-table",
                        ),
                        **{"hx-confirm": "Remove all limits?"},
                    )
                    if has_limits
                    else ""
                ),
                class_="flex gap-2 justify-end",
            ),
            class_="bg-ivory-light p-4",
        ),
        **hx(  # pyright: ignore
            post="/app/users/rate-limits",
            target="#users-table",
            swap="outerHTML",
            select="#users-table",
        ),
        **{
            "hx-on::after-request": f"document.getElementById('rate-form-row-{token_id_safe}').classList.add('hidden');"
        },
    )


def create_token_card(token, index, user_stats=None):
    name = token.get("name", "unknown")
    token_value = token.get("token", "")
    token_id_safe = token_value[:10] if token_value else f"token-{index}"
    rate_limits = token.get("rate_limits", {})

    last_used_timestamp = None
    last_error_timestamp = None
    status_indicator = None

    if user_stats and name in user_stats:
        last_used_timestamp = user_stats[name].get("last_success_at")
        last_error_timestamp = user_stats[name].get("last_failure_at")

        if last_used_timestamp or last_error_timestamp:
            if last_error_timestamp and (
                not last_used_timestamp or last_error_timestamp > last_used_timestamp
            ):
                status_indicator = p.div(
                    title="Last request failed",
                    class_="w-3 h-3 rounded-full bg-clay",
                    style="display: inline-block; margin-right: 8px;",
                )
            elif last_used_timestamp:
                status_indicator = p.div(
                    title="Last request successful",
                    class_="w-3 h-3 rounded-full bg-olive",
                    style="display: inline-block; margin-right: 8px;",
                )

    masked_token = (
        token_value[:10] + "..." + token_value[-10:]
        if len(token_value) > 20
        else "••••••••••••••••"
    )

    has_limits = bool(rate_limits)

    return wa.card(
        p.div(
            p.div(
                p.div(
                    status_indicator if status_indicator else "",
                    p.h3(name, class_="text-xl font-semibold m-0 text-dark"),
                    wa.badge("Active", variant="success"),
                    class_="flex items-center gap-4 mb-6",
                ),
                slot="header",
            ),
            p.div(
                p.div(
                    p.div(
                        p.span("Token:", class_="text-cloud-dark font-semibold mr-4"),
                        p.code(
                            token_value if token_value else masked_token,
                            id=f"token-{index}",
                            class_="bg-ivory-medium px-4 py-2 rounded font-mono text-xs",
                        ),
                        class_="mb-2 flex items-center",
                    ),
                    p.div(
                        p.span(
                            "Last Used: ", class_="text-cloud-dark font-semibold mr-2"
                        ),
                        p.span(
                            (
                                lambda: (
                                    datetime.datetime.fromtimestamp(
                                        last_used_timestamp
                                    ).strftime("%Y-%m-%d %H:%M")
                                    if last_used_timestamp
                                    else "Never"
                                )
                            )(),
                            class_="text-cloud-medium text-sm",
                        ),
                        class_="mb-4",
                    ),
                    p.div(
                        (
                            wa.copy_button(
                                value=token_value,
                                copy_label="Copy Token",
                                success_label="Copied!",
                                size="small",
                            )
                            if token_value
                            else ""
                        ),
                        p.button(
                            "Regenerate",
                            type="button",
                            class_="px-4 py-2 bg-kraft text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                            **hx(
                                post="/app/users/regenerate",
                                vals=f'{{"token": "{token_value}", "name": "{name}"}}',
                                target=f"#user-card-{token_id_safe}",
                                swap="outerHTML",
                            ),
                            **{
                                "hx-confirm": f"Regenerate token for {name}? The old token will be revoked."
                            },
                        ),
                        p.button(
                            "Delete",
                            type="button",
                            class_="px-4 py-2 bg-clay text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                            **hx(
                                post="/app/users/delete",
                                vals=f'{{"token": "{token_value}"}}',
                                target=f"#user-card-{token_id_safe}",
                                swap="delete",
                            ),
                            **{
                                "hx-confirm": f"Delete user {name}? This cannot be undone."
                            },
                        ),
                        class_="flex gap-2 mb-6 flex-wrap",
                    ),
                ),
                create_rate_limits_section(
                    rate_limits, token_value, name, token_id_safe
                ),
            ),
        ),
        id=f"user-card-{token_id_safe}",
        class_="bg-white rounded-card shadow-warm-md",
    )


def create_rate_limits_section(rate_limits, token_value, name, token_id_safe):
    import pyhtml_cem.webawesome.components as wa

    has_limits = bool(rate_limits)

    limits_display = []
    if has_limits:
        if "requests_per_minute" in rate_limits:
            limits_display.append(
                ("Requests/Minute", rate_limits["requests_per_minute"])
            )
        if "requests_per_hour" in rate_limits:
            limits_display.append(("Requests/Hour", rate_limits["requests_per_hour"]))
        if "requests_per_day" in rate_limits:
            limits_display.append(("Requests/Day", rate_limits["requests_per_day"]))
        if "tokens_per_minute" in rate_limits:
            limits_display.append(
                ("Tokens/Minute", f"{rate_limits['tokens_per_minute']:,}")
            )
        if "tokens_per_day" in rate_limits:
            limits_display.append(("Tokens/Day", f"{rate_limits['tokens_per_day']:,}"))

    return p.div(
        wa.divider(),
        p.div(
            p.div(
                p.strong("Rate Limits", class_="text-dark text-base mb-3 block"),
                p.button(
                    "Edit" if has_limits else "Add Rate Limits",
                    type="button",
                    class_="px-3 py-1 bg-olive text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                    **{
                        "onclick": f"document.getElementById('rate-limits-form-{token_id_safe}').classList.toggle('hidden')"
                    },
                ),
                class_="flex items-center justify-between mb-3",
            ),
            (
                p.div(
                    *[
                        p.div(
                            p.span(f"{label}:", class_="text-cloud-dark text-sm mr-2"),
                            p.span(
                                str(value), class_="text-dark font-semibold text-sm"
                            ),
                            class_="py-1 flex justify-between",
                        )
                        for label, value in limits_display
                    ],
                    class_="mb-3",
                )
                if has_limits
                else ""
            ),
            p.form(
                p.div(
                    p.div(
                        p.label(
                            "Requests/Minute:",
                            class_="text-xs text-cloud-dark block mb-1",
                        ),
                        p.input(
                            type="number",
                            name="requests_per_minute",
                            placeholder="e.g., 60",
                            value=(
                                str(rate_limits.get("requests_per_minute", ""))
                                if rate_limits.get("requests_per_minute")
                                else ""
                            ),
                            class_="w-full px-3 py-1.5 border border-cloud-light rounded-lg text-sm focus:outline-none focus:border-olive",
                        ),
                        class_="mb-3",
                    ),
                    p.div(
                        p.label(
                            "Requests/Hour:",
                            class_="text-xs text-cloud-dark block mb-1",
                        ),
                        p.input(
                            type="number",
                            name="requests_per_hour",
                            placeholder="e.g., 1000",
                            value=(
                                str(rate_limits.get("requests_per_hour", ""))
                                if rate_limits.get("requests_per_hour")
                                else ""
                            ),
                            class_="w-full px-3 py-1.5 border border-cloud-light rounded-lg text-sm focus:outline-none focus:border-olive",
                        ),
                        class_="mb-3",
                    ),
                    p.div(
                        p.label(
                            "Requests/Day:", class_="text-xs text-cloud-dark block mb-1"
                        ),
                        p.input(
                            type="number",
                            name="requests_per_day",
                            placeholder="e.g., 10000",
                            value=(
                                str(rate_limits.get("requests_per_day", ""))
                                if rate_limits.get("requests_per_day")
                                else ""
                            ),
                            class_="w-full px-3 py-1.5 border border-cloud-light rounded-lg text-sm focus:outline-none focus:border-olive",
                        ),
                        class_="mb-3",
                    ),
                    p.div(
                        p.label(
                            "Tokens/Minute:",
                            class_="text-xs text-cloud-dark block mb-1",
                        ),
                        p.input(
                            type="number",
                            name="tokens_per_minute",
                            placeholder="e.g., 100000",
                            value=(
                                str(rate_limits.get("tokens_per_minute", ""))
                                if rate_limits.get("tokens_per_minute")
                                else ""
                            ),
                            class_="w-full px-3 py-1.5 border border-cloud-light rounded-lg text-sm focus:outline-none focus:border-olive",
                        ),
                        class_="mb-3",
                    ),
                    p.div(
                        p.label(
                            "Tokens/Day:", class_="text-xs text-cloud-dark block mb-1"
                        ),
                        p.input(
                            type="number",
                            name="tokens_per_day",
                            placeholder="e.g., 1000000",
                            value=(
                                str(rate_limits.get("tokens_per_day", ""))
                                if rate_limits.get("tokens_per_day")
                                else ""
                            ),
                            class_="w-full px-3 py-1.5 border border-cloud-light rounded-lg text-sm focus:outline-none focus:border-olive",
                        ),
                        class_="mb-3",
                    ),
                    class_="grid grid-cols-2 gap-3",
                ),
                p.div(
                    p.input(type="hidden", name="token", value=token_value),
                    p.input(type="hidden", name="name", value=name),
                    p.button(
                        "Cancel",
                        type="button",
                        class_="px-4 py-2 bg-cloud-medium text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                        **{
                            "onclick": f"document.getElementById('rate-limits-form-{token_id_safe}').classList.add('hidden')"
                        },
                    ),
                    p.button(
                        "Save Rate Limits",
                        type="submit",
                        class_="px-4 py-2 bg-olive text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                    ),
                    (
                        p.button(
                            "Remove All Limits",
                            type="button",
                            class_="px-4 py-2 bg-clay text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                            **hx(
                                post="/app/users/rate-limits/remove",
                                vals=f'{{"token": "{token_value}"}}',
                                target=f"#rate-limits-section-{token_id_safe}",
                                swap="outerHTML",
                            ),
                            **{"hx-confirm": "Remove all rate limits?"},
                        )
                        if has_limits
                        else ""
                    ),
                    class_="flex gap-2 justify-end",
                ),
                id=f"rate-limits-form-{token_id_safe}",
                class_="hidden bg-ivory-light p-4 rounded-xl",
                **{
                    **hx(
                        post="/app/users/rate-limits",
                        target=f"#rate-limits-section-{token_id_safe}",
                        swap="outerHTML",
                    ),
                    "hx-on::after-request": f"document.getElementById('rate-limits-form-{token_id_safe}').classList.add('hidden');",
                },
            ),
        ),
        id=f"rate-limits-section-{token_id_safe}",
        class_="mt-4",
    )
