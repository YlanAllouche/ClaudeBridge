import pyhtml as p


def create_chat_page(models, chat_token):
    # Find claude-sonnet-4-5 or fallback to first model
    default_model = "claude-4-5-haiku"
    if not any(m["id"] == default_model for m in models):
        default_model = (
            models[0]["id"] if models else "claude-4-5-haiku"
        )  # FIX: Why was sonnet 4-5 used to not work?

    model_options = [
        (
            p.option(model["id"], value=model["id"], selected=True)
            if model["id"] == default_model
            else p.option(model["id"], value=model["id"])
        )
        for model in models
    ]

    deep_chat = p.create_tag("deep-chat")
    deep_chat_element = deep_chat(
        id="chat-element",
        class_="w-full rounded-card overflow-hidden shadow-warm-md border border-cloud-light",
        style="width: 100%; height: calc(100vh - 280px); display: block; min-height: 500px;",
    )
    return p.div(
        p.div(
            p.div(
                p.h1(
                    "Chat Interface",
                    class_="text-3xl font-bold text-dark m-0 font-heading",
                ),
                p.p(
                    "Test Claude models with a live chat interface",
                    class_="text-cloud-dark mt-2 mb-0",
                ),
                class_="mb-6",
            ),
            p.div(
                p.label("Model", class_="block mb-2 font-semibold text-dark text-sm"),
                p.select(
                    *model_options,
                    id="model-select",
                    class_="w-full px-3 py-2 text-sm border-2 border-cloud-light rounded-xl bg-white cursor-pointer transition-all focus:border-dark focus:shadow-warm",
                ),
                class_="mb-6 max-w-md",
            ),
        ),
        deep_chat_element,
        # TODO: consider extracting into its own js file or replacing by some HTMX logic
        p.script(
            f"""
            (async function() {{
                await customElements.whenDefined('deep-chat');
                
                const chatElement = document.getElementById('chat-element');
                const modelSelect = document.getElementById('model-select');
                
                if (!chatElement) {{
                    console.error('Chat element not found');
                    return;
                }}
                
                chatElement.messageStyles = {{
                    default: {{
                        shared: {{
                            bubble: {{
                                borderRadius: '12px',
                                padding: '12px 16px',
                                fontSize: '15px',
                                lineHeight: '1.5'
                            }}
                        }},
                        user: {{
                            bubble: {{
                                maxWidth: '75%',
                                backgroundColor: '#0f0f0e',
                                color: '#ffffff'
                            }}
                        }},
                        ai: {{
                            bubble: {{
                                maxWidth: '100%',
                                backgroundColor: '#f0eee6',
                                color: '#0f0f0e',
                                border: '1px solid #d1cfc5'
                            }}
                        }}
                    }}
                }};
                
                chatElement.connect = {{
                    url: window.location.origin + '/v1/chat/completions',
                    stream: true
                }};
                
                chatElement.directConnection = {{
                    openAI: {{
                        key: '{chat_token}',
                        chat: true
                    }}
                }};
                
                chatElement.textInput = {{
                    placeholder: {{ text: "Ask Claude anything..." }},
                    styles: {{
                        container: {{
                            borderTop: '1px solid #d1cfc5',
                            backgroundColor: '#faf9f5'
                        }},
                        text: {{
                            padding: '12px',
                            fontSize: '15px'
                        }}
                    }}
                }};
                
                chatElement.requestInterceptor = function(requestDetails) {{
                    if (requestDetails.body && modelSelect) {{
                        let body = typeof requestDetails.body === 'string' 
                            ? JSON.parse(requestDetails.body) 
                            : requestDetails.body;
                        body.model = modelSelect.value;
                        requestDetails.body = body;
                    }}
                    return requestDetails;
                }};
                
                chatElement.addEventListener('response', function(event) {{
                    if (window.hljs) {{
                        setTimeout(() => chatElement.refreshMessages(), 100);
                    }}
                }});
            }})();
        """
        ),
    )
