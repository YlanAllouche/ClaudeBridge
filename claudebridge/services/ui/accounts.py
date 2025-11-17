import datetime

import pyhtml as p
import pyhtml_cem.webawesome as wa
from pyhtml_htmx import hx


def create_web_session_key_section(
    account_id,
    web_session_key,
    web_session_error,
    web_session_polling_error=None,
    web_session_polling_error_since=None,
):
    if web_session_key:
        masked_key = (
            web_session_key[:20] + "..."
            if len(web_session_key) > 20
            else web_session_key
        )

        error_elements = []

        if web_session_error:
            error_elements.append(
                wa.callout(
                    wa.icon(slot="icon", name="exclamation-triangle"),
                    web_session_error,
                    variant="danger",
                    open=True,
                    class_="mt-3",
                )
            )

        # Polling error
        if web_session_polling_error:
            error_since_text = ""
            if web_session_polling_error_since:
                import time

                error_duration = int(time.time()) - web_session_polling_error_since
                if error_duration < 60:
                    error_since_text = f" (for {error_duration}s)"
                elif error_duration < 3600:
                    minutes = error_duration // 60
                    error_since_text = f" (for {minutes}m)"
                else:
                    hours = error_duration // 3600
                    minutes = (error_duration % 3600) // 60
                    error_since_text = f" (for {hours}h {minutes}m)"

            error_elements.append(
                wa.callout(
                    wa.icon(slot="icon", name="exclamation-triangle"),
                    p.strong(
                        f"Polling failed: {web_session_polling_error}{error_since_text}"
                    ),
                    variant="warning",
                    open=True,
                    class_="mt-3",
                )
            )

        return p.div(
            p.div(
                p.div(
                    p.span("Session Key", class_="text-xs text-cloud-dark mb-1 block"),
                    p.code(masked_key, class_="text-sm font-mono text-dark block mb-1"),
                    class_="mb-1",
                ),
                p.form(
                    p.input(type="hidden", name="account_id", value=account_id),
                    p.input(
                        type="text",
                        name="session_key",
                        placeholder="New key...",
                        class_="w-full p-2 border border-cloud-light rounded-xl text-sm font-mono mb-1",
                    ),
                    p.div(
                        p.button(
                            "Update",
                            type="submit",
                            class_="bg-olive text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-opacity-90 transition-colors cursor-pointer",
                        ),
                        p.button(
                            "Remove",
                            type="button",
                            class_="bg-clay text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-opacity-90 transition-colors cursor-pointer",
                            **hx(
                                post="/app/account/remove-session-key",
                                vals=f'{{"account_id": "{account_id}"}}',
                                target="#account-card",
                                swap="outerHTML",
                            ),
                        ),
                        class_="flex gap-2",
                    ),
                    **hx(
                        post="/app/account/update-session-key",
                        target="#account-card",
                        swap="outerHTML",
                    ),
                ),
                *error_elements,
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        )
    else:
        return p.div(
            p.div(
                p.span("Session Key", class_="text-xs text-cloud-dark mb-1 block"),
                p.span(
                    "Not configured",
                    class_="text-base text-dark font-semibold mb-1 block",
                ),
                p.form(
                    p.input(type="hidden", name="account_id", value=account_id),
                    p.input(
                        type="text",
                        name="session_key",
                        placeholder="sk-ant-sid01-...",
                        class_="w-full p-2 border border-cloud-light rounded-xl text-sm font-mono mb-1",
                    ),
                    p.button(
                        "Save",
                        type="submit",
                        class_="w-full bg-olive text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-opacity-90 transition-colors cursor-pointer mb-1",
                    ),
                    **hx(
                        post="/app/account/update-session-key",
                        target="#account-card",
                        swap="outerHTML",
                    ),
                ),
                p.p(
                    "Get from claude.ai, in Devtools, network, refresh page, look for the '/usage' call and copy the session key from the header of the request",
                    class_="text-xs text-cloud-medium",
                ),
                class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
            )
        )


def create_accounts_page(
    accounts, config_manager, accounts_manager=None, web_session_poller=None
):
    has_account = len(accounts) > 0
    account = accounts[0] if has_account else None

    header = p.div(
        p.h1("Account", class_="text-3xl font-bold text-dark m-0 font-heading"),
        class_="mb-2",
    )

    if not has_account:
        return p.div(
            header,
            wa.callout(
                wa.icon(slot="icon", name="info-circle"),
                p.strong("No account connected"),
                p.br(),
                "Connect your Anthropic account to start using the bridge",
                variant="success",
                open=True,
                class_="mb-1",
            ),
            p.div(
                p.button(
                    "Connect Account",
                    type="button",
                    id="connect-account-btn",
                    class_="bg-leather text-white px-6 py-3 rounded-xl font-semibold hover:bg-clay transition-colors cursor-pointer",
                    **hx(
                        get="/app/account/add-form",
                        target="#add-account-form",
                        swap="innerHTML",
                    ),
                ),
                class_="mb-1",
            ),
            p.div(id="add-account-form", class_="mb-1"),
        )

    return p.div(
        header,
        p.div(id="add-account-form", class_="mb-1"),
        p.div(
            id="account-card-wrapper",
            **hx(
                get="/app/account/refresh-card", trigger="every 60s", swap="innerHTML"
            ),
        )(create_account_card(account, accounts_manager)),
    )


def create_account_card(account, accounts_manager=None, web_session_poller=None):
    account_id = account.get("account_id")
    account_name = account.get("account_name", "Unknown Account")
    connected = account.get("connected", False)
    expires_at = account.get("expires_at")
    created_at = account.get("created_at", "")

    email = account.get("email", "N/A")
    org_name = account.get("organization_name", "N/A")
    org_uuid = account.get("organization_uuid", "N/A")
    anthropic_uuid = account.get("anthropic_account_uuid", "N/A")
    web_session_key = account.get("web_session_key")
    web_session_error = account.get("web_session_key_error")

    web_session_polling_error = None
    web_session_polling_error_since = None
    if web_session_poller:
        web_session_polling_error = web_session_poller.get_error(account_id)
        web_session_polling_error_since = web_session_poller.get_error_since(account_id)

    if connected:
        status_badge = p.span(
            "Connected", class_="text-xs px-2 py-1 rounded-full bg-olive text-white"
        )
        status_alert = p.div()
    else:
        status_badge = p.span(
            "Disconnected",
            class_="text-xs px-2 py-1 rounded-full bg-cloud-medium text-white",
        )
        status_alert = wa.callout(
            wa.icon(slot="icon", name="exclamation-triangle"),
            p.strong("Connection Lost"),
            "Reconnect to continue using the bridge",
            variant="warning",
            open=True,
            class_="mb-1",
        )

    if expires_at:
        try:
            expiry_dt = datetime.datetime.fromtimestamp(
                expires_at, tz=datetime.timezone.utc
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            time_left = expiry_dt - now

            if time_left.total_seconds() > 0:
                days = time_left.days
                hours = time_left.seconds // 3600
                expiry_text = (
                    f"Expires in {days}d {hours}h"
                    if days > 0
                    else f"Expires in {hours}h"
                )
            else:
                expiry_text = "Expired"
        except:
            expiry_text = "Unknown"
    else:
        expiry_text = "N/A"

    return p.div(
        p.div(
            p.h2("Oauth", class_="text-xl font-bold text-dark m-0 mb-1 font-heading"),
            p.div(
                status_alert,
                p.div(
                    p.div(
                        p.span("Email", class_="text-xs text-cloud-dark mb-1 block"),
                        p.span(email, class_="text-base text-dark font-semibold"),
                        class_="mb-1",
                    ),
                    p.div(
                        p.span(
                            "Organization", class_="text-xs text-cloud-dark mb-1 block"
                        ),
                        p.span(org_name, class_="text-base text-dark font-semibold"),
                        class_="mb-1",
                    ),
                    p.div(
                        p.span(
                            "Token Expiry", class_="text-xs text-cloud-dark mb-1 block"
                        ),
                        p.span(expiry_text, class_="text-base text-dark font-semibold"),
                        class_="mb-1",
                    ),
                    p.div(
                        p.span("Status", class_="text-xs text-cloud-dark mb-1 block"),
                        status_badge,
                        class_="mb-1",
                    ),
                    p.div(
                        p.form(
                            p.input(type="hidden", name="account_id", value=account_id),
                            p.button(
                                "Reconnect",
                                type="submit",
                                class_="bg-white text-dark px-4 py-2 rounded-xl text-sm font-semibold border border-cloud-light hover:bg-ivory-light transition-colors cursor-pointer mr-2",
                            ),
                            **hx(
                                post="/app/account/reconnect",
                                target="#add-account-form",
                                swap="innerHTML",
                            ),
                            class_="inline",
                        ),
                        p.form(
                            p.input(type="hidden", name="account_id", value=account_id),
                            p.button(
                                "Logout",
                                type="submit",
                                class_="bg-clay text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-opacity-90 transition-colors cursor-pointer",
                                onclick="return confirm('Are you sure you want to logout?');",
                            ),
                            **hx(
                                post="/app/account/delete",
                                target="#account-card",
                                swap="outerHTML",
                            ),
                            class_="inline",
                        ),
                        class_="flex gap-2",
                    ),
                    class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
                ),
                class_="mb-1",
            ),
        ),
        p.div(
            p.h2(
                "Web Session Key",
                class_="text-xl font-bold text-dark m-0 mb-1 font-heading",
            ),
            p.p(
                "For real-time usage polling from claude.ai",
                class_="text-xs text-cloud-dark mb-1",
            ),
            create_web_session_key_section(
                account_id,
                web_session_key,
                web_session_error,
                web_session_polling_error,
                web_session_polling_error_since,
            ),
        ),
        id="account-card",
        class_="max-w-4xl",
    )


def create_add_account_form():
    return p.div(
        wa.card(
            p.div(
                p.h3(
                    "Connect Account",
                    class_="text-lg font-bold text-dark m-0 mb-1 font-heading",
                ),
                p.form(
                    p.div(
                        p.label(
                            "Account Name",
                            class_="block text-sm font-semibold text-dark mb-1",
                            **{"for": "account-name"},
                        ),
                        p.input(
                            type="text",
                            name="account_name",
                            id="account-name",
                            placeholder="e.g., Personal Account, Work Account",
                            required=True,
                            class_="w-full p-2 border border-cloud-light rounded-xl mb-1",
                        ),
                        class_="mb-1",
                    ),
                    p.input(type="hidden", name="mode", value="max"),
                    p.div(
                        p.button(
                            "Start OAuth Flow",
                            type="submit",
                            class_="bg-leather text-white px-4 py-2 rounded-xl font-semibold hover:bg-clay transition-colors cursor-pointer",
                        ),
                        p.button(
                            "Cancel",
                            type="button",
                            class_="bg-white text-dark px-4 py-2 rounded-xl font-semibold border border-cloud-light hover:bg-ivory-light transition-colors cursor-pointer ml-3",
                            **hx(
                                get="/app/account/cancel-form",
                                target="#add-account-form",
                                swap="innerHTML",
                            ),
                        ),
                        class_="flex gap-3",
                    ),
                    **hx(
                        post="/app/account/start-oauth",
                        target="#add-account-form",
                        swap="innerHTML",
                    ),
                ),
            ),
            class_="bg-ivory-medium",
        ),
        class_="max-w-2xl",
    )


def create_oauth_flow_card(session_id, auth_url, account_name):
    return p.div(
        p.script(
            f"""
            console.log('OAuth flow card loaded for session: {session_id}');
            console.log('Opening OAuth URL in new window...');
            const authWindow = window.open('{auth_url}', '_blank', 'width=600,height=800');
            setTimeout(() => {{
                if (typeof htmx !== 'undefined') {{
                    console.log('Processing HTMX on new content');
                    htmx.process(document.getElementById('oauth-form-{session_id}'));
                }}
            }}, 100);
        """
        ),
        wa.card(
            p.div(
                p.h3(
                    f"Connect: {account_name}",
                    class_="text-lg font-bold text-dark m-0 mb-1 font-heading",
                ),
                p.div(
                    p.strong("Step 1: ", class_="text-dark text-sm"),
                    p.span(
                        "A new window should open automatically.",
                        class_="text-cloud-dark text-sm",
                    ),
                    class_="mb-1 text-sm bg-ivory-light p-3 rounded-xl",
                ),
                p.div(
                    p.label(
                        "Authorization URL",
                        class_="block text-sm font-semibold text-dark mb-1",
                    ),
                    p.div(
                        p.input(
                            type="text",
                            value=auth_url,
                            readonly=True,
                            class_="flex-1 p-2 border border-cloud-light rounded-xl bg-ivory-light font-mono text-xs",
                            id=f"auth-url-{session_id}",
                        ),
                        wa.copy_button(value=auth_url, class_="ml-2"),
                        class_="flex items-center mb-1",
                    ),
                    p.a(
                        "Open in Browser",
                        href=auth_url,
                        target="_blank",
                        class_="inline-flex items-center bg-leather text-white px-4 py-2 rounded-xl font-semibold hover:bg-clay transition-colors cursor-pointer no-underline",
                    ),
                    class_="mb-1",
                ),
                p.div(
                    p.strong("Step 2: ", class_="text-dark text-sm"),
                    p.span(
                        "After authorizing, paste the code below.",
                        class_="text-cloud-dark text-sm",
                    ),
                    class_="mb-1 text-sm bg-ivory-light p-3 rounded-xl",
                ),
                p.form(
                    p.div(
                        p.label(
                            "Authorization Code",
                            class_="block text-sm font-semibold text-dark mb-1",
                            **{"for": "auth-code"},
                        ),
                        p.input(
                            type="text",
                            name="code",
                            id="auth-code",
                            placeholder="Paste the authorization code here",
                            required=True,
                            class_="w-full p-2 border border-cloud-light rounded-xl mb-1",
                        ),
                        p.input(type="hidden", name="session_id", value=session_id),
                        class_="mb-1",
                    ),
                    p.div(
                        p.button(
                            "Complete Connection",
                            type="submit",
                            class_="bg-olive text-white px-4 py-2 rounded-xl font-semibold hover:bg-opacity-90 transition-colors cursor-pointer",
                            onclick="console.log('Complete button clicked');",
                        ),
                        p.button(
                            "Cancel",
                            type="button",
                            class_="bg-white text-dark px-4 py-2 rounded-xl font-semibold border border-cloud-light hover:bg-ivory-light transition-colors cursor-pointer ml-3",
                            **hx(
                                get="/app/account/cancel-form",
                                target="#add-account-form",
                                swap="innerHTML",
                            ),
                        ),
                        class_="flex gap-3",
                    ),
                    id=f"oauth-form-{session_id}",
                    **hx(
                        post="/app/account/complete-oauth",
                        target="#add-account-form",
                        swap="innerHTML",
                    ),
                ),
                p.div(id=f"oauth-status-{session_id}", class_="mt-4"),
            ),
            class_="bg-ivory-medium",
        ),
        class_="max-w-3xl",
    )
