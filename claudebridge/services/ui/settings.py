import pyhtml as p
import pyhtml_cem.webawesome.components as wa
from pyhtml_htmx import hx


def create_settings_page(config_manager):
    config = config_manager.config  # ?

    return p.div(
        p.div(
            p.h1("Settings", class_="text-3xl font-bold text-dark m-0 font-heading"),
            p.p(
                "Configure ClaudeBridge system settings",
                class_="text-cloud-dark mt-2 mb-0",
            ),
            class_="mb-8",
        ),
        p.div(
            create_general_card(config_manager),
            p.div(
                create_claude_code_card(config_manager),
                create_prometheus_metrics_card(config_manager),
                class_="grid lg:grid-cols-2 gap-6",
            ),
            p.div(
                create_models_config_card(config_manager),
                create_api_tokens_card(config_manager),
                class_="grid lg:grid-cols-2 gap-6",
            ),
            class_="flex flex-col gap-6 max-w-6xl",
        ),
    )


def create_general_card(config_manager):
    from pyhtml_htmx import hx

    config = config_manager.config
    password_info = config_manager.get_ui_password()

    password_source = password_info["source"]
    password_enabled = password_info["password"] is not None
    can_edit = password_source in ["config", "none", "config_disabled"]

    source_display = {
        "env_disabled": "ENV",
        "env": "ENV",
        "config": "Config",
        "config_disabled": "Config",
        "none": "None",
    }.get(password_source, password_source or "unknown")

    return p.div(
        p.h2(
            "General Settings",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p(
            "System configuration and authentication",
            class_="text-xs text-cloud-dark mb-3",
        ),
        p.div(
            p.div(
                p.div(
                    p.div(
                        p.span(
                            "Config Version",
                            class_="text-xs text-cloud-dark mb-1 block",
                        ),
                        p.code(
                            config.get("version", "unknown"),
                            class_="text-sm text-dark bg-ivory-light px-2 py-1 rounded",
                        ),
                        class_="mb-3",
                    ),
                    p.div(
                        p.span(
                            "UI Password", class_="text-xs text-cloud-dark mb-1 block"
                        ),
                        p.div(
                            p.span(
                                "Enabled" if password_enabled else "Disabled",
                                class_=f"text-sm font-semibold {'text-olive' if password_enabled else 'text-cloud-dark'} mr-2",
                            ),
                            p.span(
                                f"({source_display})",
                                class_="text-xs text-cloud-medium",
                            ),
                            class_="mb-2",
                        ),
                        class_="mb-3",
                    ),
                    (
                        p.button(
                            "Change Password",
                            type="button",
                            class_="w-full px-4 py-2 bg-olive text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                            **{
                                "onclick": "document.getElementById('password-form').classList.toggle('hidden')"
                            },
                        )
                        if can_edit
                        else p.div()
                    ),
                    (
                        p.div(
                            p.p(
                                "Password set via ENV (read-only)",
                                class_="text-sm text-kraft mt-2",
                            )
                        )
                        if password_source == "env"
                        else p.div()
                    ),
                    (
                        p.form(
                            p.input(
                                type="text",
                                name="password",
                                placeholder="Leave blank for random",
                                class_="w-full px-4 py-2 border border-cloud-light rounded-xl mb-3",
                            ),
                            p.div(
                                p.button(
                                    "Cancel",
                                    type="button",
                                    class_="px-4 py-2 bg-cloud-medium text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                                    **{
                                        "onclick": "document.getElementById('password-form').classList.add('hidden')"
                                    },
                                ),
                                p.button(
                                    "Update",
                                    type="submit",
                                    class_="px-4 py-2 bg-olive text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                                ),
                                class_="flex gap-3 justify-end",
                            ),
                            id="password-form",
                            class_="hidden bg-ivory-light p-4 rounded-xl mt-3 border border-cloud-light",
                            **hx(  # pyright: ignore
                                post="/app/settings/password", swap="none"
                            ),
                            **{
                                "hx-on::after-request": """
                            if (event.detail.xhr.responseText && event.detail.xhr.responseText.startsWith('Password updated to:')) {
                                const password = event.detail.xhr.responseText.replace('Password updated to: ', '');
                                alert('New password: ' + password + '\\n\\nSave it! You will be logged out.');
                            } else {
                                alert('Password updated! Login again.');
                            }
                            window.location.href='/app/logout';
                        """
                            },
                        )
                        if can_edit
                        else p.div()
                    ),
                    class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
                )
            )
        ),
    )


def create_claude_code_card(config_manager):

    config = config_manager.config
    spoof_enabled = config.get("spoof_on_anthropic", False)

    return p.div(
        p.h2(
            "Claude Code Spoofing",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p(
            "",
            class_="text-xs text-cloud-dark mb-3",
        ),
        p.div(
            p.div(
                p.div(
                    p.span(
                        "Spoof Claude Code System Prompt",
                        class_="text-xs text-cloud-dark mb-2 block",
                    ),
                    p.div(
                        wa.switch(
                            checked=spoof_enabled,
                            **{  # pyright: ignore
                                "hx-post": "/app/settings/spoof-toggle",
                                "hx-trigger": "sl-change",
                                "hx-vals": 'js:{"enabled": event.target.checked}',
                                "hx-target": "#spoof-status-text",
                                "hx-swap": "outerHTML",
                            },
                        ),
                        p.span(
                            "Enabled" if spoof_enabled else "Disabled",
                            class_=f"text-sm font-semibold ml-3 {'text-olive' if spoof_enabled else 'text-cloud-dark'}",
                            id="spoof-status-text",
                        ),
                        class_="flex items-center",
                    ),
                    class_="mb-3",
                ),
                p.p(
                    "Enable if using the bridge with an Anthropic-style client that is not ClaudeCode",
                    class_="text-sm text-cloud-medium",
                ),
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        ),
    )


def create_prometheus_metrics_card(config_manager):

    config = config_manager.config
    metrics_enabled = config.get("metrics_endpoint_enabled", False)

    return p.div(
        p.h2(
            "Prometheus Metrics",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p(
            "Expose metrics endpoint for monitoring",
            class_="text-xs text-cloud-dark mb-3",
        ),
        p.div(
            p.div(
                p.div(
                    p.span(
                        "Expose /metrics Endpoint",
                        class_="text-xs text-cloud-dark mb-2 block",
                    ),
                    p.div(
                        wa.switch(
                            checked=metrics_enabled,
                            **{  # pyright: ignore
                                "hx-post": "/app/settings/metrics-toggle",
                                "hx-trigger": "sl-change",
                                "hx-vals": 'js:{"enabled": event.target.checked}',
                                "hx-target": "#metrics-status-text",
                                "hx-swap": "outerHTML",
                            },
                        ),
                        p.span(
                            "Enabled" if metrics_enabled else "Disabled",
                            class_=f"text-sm font-semibold ml-3 {'text-olive' if metrics_enabled else 'text-cloud-dark'}",
                            id="metrics-status-text",
                        ),
                        class_="flex items-center mb-2",
                    ),
                    (
                        p.code(
                            "http://localhost:8000/metrics",
                            class_="text-xs bg-ivory-light px-2 py-1 rounded border border-cloud-light inline-block",
                        )
                        if metrics_enabled
                        else p.div()
                    ),
                    class_="mb-3",
                ),
                p.p(
                    "Prometheus format with request counts, tokens, and quota status",
                    class_="text-sm text-cloud-medium",
                ),
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        ),
    )


def create_models_config_card(config_manager):
    config = config_manager.config
    custom_models = config.get("models", {}).get("custom", [])
    blocked_models = config.get("models", {}).get("blocked", [])

    return p.div(
        p.h2(
            "Model Configuration",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p("Custom and blocked models", class_="text-xs text-cloud-dark mb-3"),
        p.div(
            p.div(
                p.div(
                    p.span(
                        "Custom Models", class_="text-xs text-cloud-dark mb-1 block"
                    ),
                    p.span(
                        str(len(custom_models)),
                        class_="text-base font-semibold text-sky",
                    ),
                    class_="mb-3",
                ),
                p.div(
                    p.span(
                        "Blocked Models", class_="text-xs text-cloud-dark mb-1 block"
                    ),
                    p.span(
                        str(len(blocked_models)),
                        class_="text-base font-semibold text-clay",
                    ),
                    class_="mb-3",
                ),
                p.p("Manage in Models page", class_="text-sm text-cloud-medium"),
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        ),
    )


def create_api_tokens_card(config_manager):
    config = config_manager.config
    api_tokens_enabled = config.get("api_tokens", {}).get("enabled", False)
    tokens = config_manager.get_all_tokens()

    return p.div(
        p.h2(
            "Internal API Tokens",
            class_="text-xl font-bold text-dark m-0 mb-2 font-heading",
        ),
        p.p(
            "Authentication tokens for internal API access",
            class_="text-xs text-cloud-dark mb-3",
        ),
        p.div(
            p.div(
                p.div(
                    p.span("Token System", class_="text-xs text-cloud-dark mb-1 block"),
                    p.span(
                        "Enabled" if api_tokens_enabled else "Disabled",
                        class_=f"text-base font-semibold {'text-olive' if api_tokens_enabled else 'text-cloud-dark'}",
                    ),
                    class_="mb-3",
                ),
                p.div(
                    p.span(
                        "Active Tokens", class_="text-xs text-cloud-dark mb-1 block"
                    ),
                    p.span(str(len(tokens)), class_="text-base font-semibold text-sky"),
                    class_="mb-3",
                ),
                p.p("Manage in Users page", class_="text-sm text-cloud-medium"),
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        ),
    )
