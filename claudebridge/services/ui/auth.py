import pyhtml as p
import pyhtml_cem.webawesome as wa


def create_login_fragment(error=None):
    """Login form for when auth is lost within the app"""
    error_alert = (
        wa.callout(
            wa.icon(slot="icon", name="exclamation-triangle"),
            p.strong("Error: "),
            error,
            variant="danger",
            open=True,
            class_="mb-6",
        )
        if error
        else ""
    )

    return p.div(
        p.div(
            p.h1(
                "Authentication Required",
                class_="text-2xl font-bold text-dark m-0 lcmb-2 font-heading",
            ),
            p.p("Please sign in to continue", class_="text-cloud-dark mb-6"),
            class_="mb-6",
        ),
        wa.card(
            p.form(
                error_alert,
                p.div(
                    p.label("Password", class_="block mb-2 font-semibold text-dark"),
                    p.input(
                        type="password",
                        name="password",
                        placeholder="Enter your password",
                        required=True,
                        autofocus=True,
                        class_="w-full px-4 py-3 text-base bg-ivory-light border-2 border-cloud-light rounded-xl outline-none transition-all duration-200 focus:border-dark focus:shadow-warm",
                    ),
                    class_="mb-6",
                ),
                p.button(
                    "Sign In",
                    type="submit",
                    class_="w-full px-6 py-3.5 text-base font-semibold text-white bg-dark border-0 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-warm-md active:translate-y-0",
                ),
                action="/app/login",
                method="post",
                class_="p-6",
            ),
            class_="bg-white rounded-card shadow-warm-md max-w-md",
        ),
    )


def create_login_page(error=None):
    head = p.head(
        p.meta(charset="UTF-8"),
        p.meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        p.title("Login - ClaudeBridge"),
        p.link(rel="icon", type="image/png", href="/icon.png"),
        p.link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.19.1/cdn/themes/light.css",
        ),
        p.script(
            type="module",
            src="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.19.1/cdn/shoelace-autoloader.js",
        ),
        p.script(src="https://unpkg.com/htmx.org@2.0.3"),
        p.link(
            rel="stylesheet",
            href="/static/styles.css",
        ),
    )

    error_alert = (
        wa.callout(
            wa.icon(slot="icon", name="exclamation-triangle"),
            p.strong("Error: "),
            error,
            variant="danger",
            open=True,
            class_="mb-6",
        )
        if error
        else ""
    )

    form_content = p.form(
        error_alert,
        p.div(
            p.label("Password", class_="block mb-2 font-semibold text-dark"),
            p.input(
                type="password",
                name="password",
                placeholder="Enter your password",
                required=True,
                autofocus=True,
                class_="w-full px-4 py-3 text-base bg-ivory-light border-2 border-cloud-light rounded-xl outline-none transition-all duration-200 focus:border-dark focus:shadow-warm",
            ),
            class_="mb-6",
        ),
        p.button(
            "Sign In",
            type="submit",
            class_="w-full px-6 py-3.5 text-base font-semibold text-white bg-dark border-0 rounded-xl cursor-pointer transition-all duration-200 hover:shadow-warm-md active:translate-y-0",
        ),
        action="/app/login",
        method="post",
        class_="px-8 pb-8",
    )

    body = p.body(
        p.div(
            p.div(
                p.div(
                    p.img(
                        src="/icon.png",
                        alt="ClaudeBridge Logo",
                        class_="w-24 h-24 mx-auto mb-6 rounded-2xl shadow-warm-lg",
                    ),
                    p.h1(
                        "ClaudeBridge",
                        class_="text-2xl font-bold text-dark m-0 mb-2 font-heading",
                    ),
                    p.p("API Bridge Dashboard", class_="text-sm text-cloud-medium m-0"),
                    class_="text-center pt-8 px-8 pb-4",
                ),
                form_content,
                class_="bg-white rounded-card shadow-warm-md",
            ),
            class_="w-full max-w-md p-8",
        ),
        class_="m-0 font-sans bg-ivory-light min-h-screen flex items-center justify-center",
    )

    return p.html(head, body)
