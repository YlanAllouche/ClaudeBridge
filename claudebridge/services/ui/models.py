import datetime

import pyhtml as p
import pyhtml_cem.webawesome as wa
from pyhtml_htmx import hx


def create_models_page(models_data, config_manager):
    available_models = models_data.get("data", [])
    custom_models = config_manager.config.get("models", {}).get("custom", [])
    blocked_models = config_manager.config.get("models", {}).get("blocked", [])
    blocked_ids = set(blocked_models)
    all_models = []

    for model in available_models:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "blocked" if model["id"] in blocked_ids else "available",
                "type": "base",
            }
        )

    for model in custom_models:
        all_models.append(
            {
                "id": model["id"],
                "created": model.get("created", 0),
                "status": "custom",
                "type": "custom",
            }
        )

    header = p.div(
        p.div(
            p.h1("Models", class_="text-3xl font-bold text-dark m-0 font-heading"),
            p.p(
                "Browse available built-in and custom Claude models",
                class_="text-cloud-dark mt-2 mb-0",
            ),
            class_="flex-1",
        ),
        p.button(
            "Add Custom Model",
            type="button",
            id="add-model-btn",
            class_="px-6 py-3 bg-sky text-white rounded-xl font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
            **{
                "onclick": "document.getElementById('add-model-form').classList.toggle('hidden')"
            },
        ),
        class_="flex items-center justify-between mb-8",
    )

    add_model_form = p.div(
        p.div(
            p.h3(
                "Add Custom Model",
                class_="text-xl font-bold text-dark m-0 mb-4 font-heading",
            ),
            p.form(
                p.div(
                    p.label("Model ID:", class_="text-sm text-cloud-dark block mb-1"),
                    p.input(
                        type="text",
                        placeholder="e.g., claude-custom-model",
                        name="model_id",
                        required=True,
                        class_="w-full px-4 py-2 border border-cloud-light rounded-xl focus:outline-none focus:border-sky",
                    ),
                    class_="mb-3",
                ),
                p.div(
                    p.button(
                        "Cancel",
                        type="button",
                        class_="px-4 py-2 bg-cloud-medium text-white rounded-xl font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                        **{
                            "onclick": "document.getElementById('add-model-form').classList.add('hidden')"
                        },
                    ),
                    p.button(
                        "Add Model",
                        type="submit",
                        class_="px-4 py-2 bg-sky text-white rounded-xl font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                    ),
                    class_="flex gap-3 justify-end",
                ),
                **hx(
                    # pyright: ignore
                    post="/app/models/custom/add",
                    target="#models-table",
                    swap="outerHTML",
                    select="#models-table",
                ),
                **{
                    "hx-on::after-request": "if(event.detail.successful) { document.getElementById('add-model-form').classList.add('hidden'); this.closest('form').reset(); }"
                },
            ),
            class_="bg-white rounded-card shadow-warm-md p-4 border border-cloud-light",
        ),
        id="add-model-form",
        class_="mb-6 hidden",
    )

    models_table = create_models_table(all_models)

    return p.div(header, add_model_form, models_table)


def create_models_table(all_models):

    if not all_models:
        return p.div(
            p.p("No models available", class_="text-cloud-dark italic"),
            id="models-table",
        )

    return p.div(
        p.table(
            p.thead(
                p.tr(
                    p.th(
                        "",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3 w-8",
                    ),
                    p.th(
                        "Model ID",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Status",
                        class_="text-left text-xs font-semibold text-cloud-dark bg-white py-2 px-3",
                    ),
                    p.th(
                        "Created",
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
                    row
                    for i, model in enumerate(all_models)
                    for row in create_model_row(model, i)
                ]
            ),
            class_="w-full text-xs border-collapse border border-cloud-light rounded-lg overflow-hidden",
        ),
        id="models-table",
        class_="bg-white rounded-card shadow-warm-md border border-cloud-light overflow-hidden",
    )


def create_model_row(model, index, test_result=None):

    model_id = model["id"]
    model_id_safe = model_id.replace(".", "-").replace("_", "-")
    status = model["status"]
    created = model.get("created", 0)

    created_date = (
        datetime.datetime.fromtimestamp(created).strftime("%Y-%m-%d")
        if created
        else "N/A"
    )

    if test_result == "success":
        status_dot = p.div(
            "✓",
            class_="w-4 h-4 flex items-center justify-center text-olive font-bold text-sm",
            title="Test passed",
        )
    elif test_result == "error":
        status_dot = p.div(
            "✗",
            class_="w-4 h-4 flex items-center justify-center text-clay font-bold text-sm",
            title="Test failed",
        )
    elif status == "available":
        status_dot = p.div(class_="w-2 h-2 rounded-full bg-olive", title="Available")
        row_class = "bg-white"
    elif status == "blocked":
        status_dot = p.div(class_="w-2 h-2 rounded-full bg-clay", title="Blocked")
        row_class = "bg-coral bg-opacity-20"
    elif status == "custom":
        status_dot = p.div(class_="w-2 h-2 rounded-full bg-sky", title="Custom")
        row_class = "bg-white"
    else:
        status_dot = p.div(
            class_="w-2 h-2 rounded-full bg-cloud-medium", title="Unknown"
        )
        row_class = "bg-white"

    if status == "available":
        status_badge = p.span(
            "Available", class_="text-xs px-2 py-1 rounded-full bg-olive text-white"
        )
        row_class = "bg-white"
    elif status == "blocked":
        status_badge = p.span(
            "Blocked", class_="text-xs px-2 py-1 rounded-full bg-clay text-white"
        )
        row_class = "bg-coral bg-opacity-20"
    elif status == "custom":
        status_badge = p.span(
            "Custom", class_="text-xs px-2 py-1 rounded-full bg-sky text-white"
        )
        row_class = "bg-white"
    else:
        status_badge = p.span(
            "Unknown",
            class_="text-xs px-2 py-1 rounded-full bg-cloud-medium text-white",
        )
        row_class = "bg-white"

    if status == "available":
        action_buttons = p.div(
            p.button(
                "Test",
                type="button",
                class_="px-3 py-1 bg-sky text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/test",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target=f"#model-row-{model_id_safe}",
                    swap="outerHTML",
                ),
            ),
            p.button(
                "Set Cost",
                type="button",
                class_="px-3 py-1 bg-kraft text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **{
                    "onclick": f"document.getElementById('cost-form-{model_id_safe}').classList.toggle('hidden')"
                },
            ),
            p.button(
                "Block",
                type="button",
                class_="px-3 py-1 bg-clay text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/block",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target="#models-table",
                    swap="outerHTML",
                    select="#models-table",
                ),
            ),
            class_="flex gap-2 justify-end",
        )
    elif status == "blocked":
        action_buttons = p.div(
            p.button(
                "Test",
                type="button",
                class_="px-3 py-1 bg-sky text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/test",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target=f"#model-row-{model_id_safe}",
                    swap="outerHTML",
                ),
            ),
            p.button(
                "Set Cost",
                type="button",
                class_="px-3 py-1 bg-kraft text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **{
                    "onclick": f"document.getElementById('cost-form-{model_id_safe}').classList.toggle('hidden')"
                },
            ),
            p.button(
                "Unblock",
                type="button",
                class_="px-3 py-1 bg-olive text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/unblock",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target="#models-table",
                    swap="outerHTML",
                    select="#models-table",
                ),
            ),
            class_="flex gap-2 justify-end",
        )
    elif status == "custom":
        action_buttons = p.div(
            p.button(
                "Test",
                type="button",
                class_="px-3 py-1 bg-sky text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/test",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target=f"#model-row-{model_id_safe}",
                    swap="outerHTML",
                ),
            ),
            p.button(
                "Set Cost",
                type="button",
                class_="px-3 py-1 bg-kraft text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **{
                    "onclick": f"document.getElementById('cost-form-{model_id_safe}').classList.toggle('hidden')"
                },
            ),
            p.button(
                "Remove",
                type="button",
                class_="px-3 py-1 bg-clay text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                **hx(  # pyright: ignore
                    post=f"/app/models/custom/remove",
                    vals=f'{{"model_id": "{model_id}"}}',
                    target="#models-table",
                    swap="outerHTML",
                    select="#models-table",
                ),
            ),
            class_="flex gap-2 justify-end",
        )
    else:
        action_buttons = p.div()

    cost_form_row = p.tr(
        p.td(
            p.div(
                p.div(
                    p.h4("Set Model Cost", class_="text-sm font-bold text-dark mb-2"),
                    p.form(
                        p.div(
                            p.div(
                                p.label(
                                    "Input Cost ($ per million tokens):",
                                    class_="text-xs text-cloud-dark block mb-1",
                                ),
                                p.input(
                                    type="number",
                                    name="input_cost",
                                    step="0.01",
                                    min="0",
                                    required=True,
                                    class_="w-full px-3 py-2 border border-cloud-light rounded-lg focus:outline-none focus:border-sky text-xs",
                                ),
                                class_="mb-2",
                            ),
                            p.div(
                                p.label(
                                    "Output Cost ($ per million tokens):",
                                    class_="text-xs text-cloud-dark block mb-1",
                                ),
                                p.input(
                                    type="number",
                                    name="output_cost",
                                    step="0.01",
                                    min="0",
                                    required=True,
                                    class_="w-full px-3 py-2 border border-cloud-light rounded-lg focus:outline-none focus:border-sky text-xs",
                                ),
                                class_="mb-3",
                            ),
                        ),
                        p.input(type="hidden", name="model_id", value=model_id),
                        p.div(
                            p.button(
                                "Cancel",
                                type="button",
                                class_="px-3 py-1 bg-cloud-medium text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                                **{
                                    "onclick": f"document.getElementById('cost-form-{model_id_safe}').classList.add('hidden')"
                                },
                            ),
                            p.button(
                                "Save",
                                type="submit",
                                class_="px-3 py-1 bg-sky text-white rounded-lg text-xs font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
                            ),
                            class_="flex gap-2 justify-end",
                        ),
                        **hx(  # pyright: ignore
                            post="/app/models/cost/set",
                            target="#models-table",
                            swap="outerHTML",
                        ),
                        **{
                            "hx-on::after-request": f"if(event.detail.successful) {{ document.getElementById('cost-form-{model_id_safe}').classList.add('hidden'); }}"
                        },
                    ),
                    class_="bg-ivory-light p-3 rounded-lg",
                ),
                class_="px-3 py-2",
            ),
            colspan="5",
            class_="border-b border-cloud-light",
        ),
        id=f"cost-form-{model_id_safe}",
        class_="hidden",
    )

    return [
        p.tr(
            p.td(status_dot, class_="py-3 px-3 text-center"),
            p.td(model_id, class_="text-xs text-dark py-3 px-3 font-mono"),
            p.td(status_badge, class_="text-xs py-3 px-3"),
            p.td(created_date, class_="text-xs text-cloud-dark py-3 px-3"),
            p.td(action_buttons, class_="text-xs py-3 px-3"),
            id=f"model-row-{model_id_safe}",
            class_=f"{row_class} border-b border-cloud-light hover:bg-ivory-light transition-colors",
        ),
        cost_form_row,
    ]


def create_model_card(model, status, test_result=None):

    model_id = model.get("id", "unknown")
    model_id_safe = model_id.replace(".", "-").replace("_", "-")
    created = model.get("created", 0)

    # NOTE: Temporary test result indicator (not persisted to file or session)
    status_indicator = None
    if test_result == "success":
        status_indicator = p.div(
            title="Test successful",
            class_="w-3 h-3 rounded-full bg-olive",
            style="display: inline-block; margin-right: 8px;",
        )
    elif test_result == "error":
        status_indicator = p.div(
            title="Test failed",
            class_="w-3 h-3 rounded-full bg-clay",
            style="display: inline-block; margin-right: 8px;",
        )

    if status == "available":
        badge = wa.badge("Available", variant="success")
        card_class = "bg-white rounded-card shadow-warm-md border-l-4 border-olive"
        action_button = p.button(
            "Block",
            type="button",
            class_="px-4 py-2 bg-clay text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
            **hx(  # pyright: ignore
                post=f"/app/models/block",
                vals=f'{{"model_id": "{model_id}"}}',
                target=f"#model-card-{model_id_safe}",
                swap="outerHTML",
                select=f"#model-card-{model_id_safe}",
            ),
        )
    elif status == "blocked":
        badge = wa.badge("Blocked", variant="danger")
        card_class = "bg-coral rounded-card shadow-warm border-l-4 border-clay"
        action_button = p.button(
            "Unblock",
            type="button",
            class_="px-4 py-2 bg-olive text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
            **hx(  # pyright: ignore
                post=f"/app/models/unblock",
                vals=f'{{"model_id": "{model_id}"}}',
                target=f"#model-card-{model_id_safe}",
                swap="outerHTML",
                select=f"#model-card-{model_id_safe}",
            ),
        )
    elif status == "custom":
        badge = wa.badge("Custom", variant="success")
        card_class = "bg-white rounded-card shadow-warm-md border-l-4 border-sky"
        action_button = p.button(
            "Remove",
            type="button",
            class_="px-4 py-2 bg-clay text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer",
            **hx(  # pyright: ignore
                post=f"/app/models/custom/remove",
                vals=f'{{"model_id": "{model_id}"}}',
                target=f"#model-card-{model_id_safe}",
                swap="delete",
            ),
        )
    else:
        badge = wa.badge("Unknown", variant="neutral")
        card_class = "bg-white rounded-card shadow-warm-md"
        action_button = ""

    import datetime

    created_date = (
        datetime.datetime.fromtimestamp(created).strftime("%Y-%m-%d")
        if created
        else "N/A"
    )

    return wa.card(
        p.div(
            p.div(
                p.div(
                    status_indicator if status_indicator else "",
                    p.strong(model_id, class_="text-lg text-dark"),
                    class_="mb-2 flex items-center",
                ),
                p.div(badge, class_="mb-4"),
                p.div(
                    p.div(
                        p.span("Created: ", class_="text-cloud-dark text-sm"),
                        p.span(created_date, class_="text-cloud-medium text-sm"),
                        class_="mb-3",
                    ),
                    p.div(
                        p.button(
                            p.span("Test", class_="htmx-indicator-text"),
                            p.span(
                                wa.icon(name="arrow-repeat", class_="animate-spin"),
                                class_="htmx-indicator",
                            ),
                            type="button",
                            class_="px-4 py-2 bg-sky text-white rounded-xl text-sm font-semibold hover:bg-opacity-80 transition-all cursor-pointer mr-2",
                            **(  # pyright: ignore
                                hx(
                                    post="/app/users/rate-limits",
                                    target=f"#rate-limits-section-{token_id_safe}",
                                    swap="outerHTML",
                                )
                                | {
                                    "hx-on::after-request": f"document.getElementById('rate-limits-form-{token_id_safe}').classList.add('hidden');"
                                }
                            ),
                        ),
                        action_button,
                        class_="flex gap-2",
                    ),
                ),
            )
        ),
        id=f"model-card-{model_id_safe}",
        class_=card_class,
    )
