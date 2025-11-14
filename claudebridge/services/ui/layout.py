import pyhtml as p
import pyhtml_cem.webawesome.components as wa
from pyhtml_htmx import hx


def create_head(title="ClaudeBridge"):
    return p.head(
        p.meta(charset="UTF-8"),
        p.meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        p.title(title),
        p.link(rel="icon", type="image/png", href="/icon.png"),
        p.script(
            type="module",
            src="/static/vendors/webawesome/webawesome.loader.js",
        ),
        p.link(
            rel="stylesheet",
            href="/static/vendors/webawesome/styles/webawesome.css",
        ),
        p.script(
            # TODO: Make sourcing the local version of the FontAwesome icon library work or use another one entirely
            """
            import { unregisterIconLibrary, registerIconLibrary, setBasePath } from '/static/vendors/webawesome/webawesome.loader.js';
            
            setBasePath('/static/vendors/webawesome');
            
            unregisterIconLibrary('default');
            
            registerIconLibrary('default', {
                resolver: (name, family = 'classic', variant = 'solid') => {
                    const styleMap = {
                        'classic': {
                            'solid': 'solid',
                            'regular': 'regular',
                            'light': 'regular',
                            'thin': 'regular'
                        },
                        'sharp': {
                            'solid': 'solid',
                            'regular': 'regular'
                        },
                        'duotone': {
                            'solid': 'solid'
                        }
                    };
                    
                    const folder = styleMap[family]?.[variant] || 'solid';
                    return `/static/vendors/fontawesome/svgs/${folder}/${name}.svg`;
                },
                mutator: svg => svg.setAttribute('fill', 'currentColor')
            });
            """,
            type="module",
        ),
        p.script(
            src="/static/vendors/htmx/htmx.min.js",
        ),
        p.script(
            type="module",
            src="/static/vendors/deep-chat/deepChat.bundle.js",
        ),
        p.link(
            rel="stylesheet",
            href="/static/vendors/highlight.js/styles/atom-one-light.min.css",
        ),
        p.script(
            src="/static/vendors/highlight.js/highlight.min.js",
        ),
        p.link(
            rel="stylesheet",
            href="/static/vendors/fonts/fonts.css",
        ),
        p.link(
            rel="stylesheet",
            href="/static/styles.css",
        ),
        # TODO: Try view transition again - maybe wait for better support in firefox
        # TODO: Move in-line css to global css style
        p.style(
            """
            .htmx-indicator {
                display: none;
            }
            
            .htmx-request .htmx-indicator {
                display: inline-block;
            }
            
            .htmx-request .htmx-indicator-text {
                display: none;
            }
            
            @keyframes spin {
                from {
                    transform: rotate(0deg);
                }
                to {
                    transform: rotate(360deg);
                }
            }
            
            .animate-spin {
                animation: spin 1s linear infinite;
            }
        """
        ),
        p.script(
            """
            document.addEventListener('htmx:afterSettle', function(evt) {
                if (evt.detail.target) {
                    htmx.process(evt.detail.target);
                }
                
                if (evt.detail.target.id === 'main-content') {
                    const path = window.location.pathname;
                    const page = path.split('/').pop() || 'models';
                    
                    const pageNames = {
                        'models': 'Models',
                        'account': 'Account',
                        'usage': 'Usage',
                        'users': 'Users',
                        'settings': 'Settings',
                        'chat': 'Chat'
                    };
                    document.title = (pageNames[page] ? pageNames[page] + ' - ' : '') + 'ClaudeBridge';
                    
                    document.querySelectorAll('.nav-link').forEach(link => {
                        link.classList.remove('bg-dark', 'text-white', 'font-semibold');
                        link.classList.add('text-cloud-dark');
                    });
                    const activeLink = document.querySelector(`[data-page="${page}"]`);
                    if (activeLink) {
                        activeLink.classList.add('bg-dark', 'text-white', 'font-semibold');
                        activeLink.classList.remove('text-cloud-dark');
                    }
                }
            });
        """
        ),
    )


def create_nav(current_page="models"):
    nav_items = [
        ("models", "robot", "Models"),
        ("account", "id-card", "Account"),
        ("usage", "chart-bar", "Usage"),
        ("users", "users", "Users"),
        ("settings", "gear", "Settings"),
        ("chat", "comment", "Chat"),
    ]

    return p.nav(
        p.div(
            p.div(
                p.img(
                    src="/icon.png", alt="ClaudeBridge", class_="w-10 h-10 rounded-xl"
                ),
                p.span("ClaudeBridge", class_="font-heading"),
                class_="text-xl font-bold text-dark mb-1 flex items-center gap-3",
            ),
            p.div("API Bridge Dashboard", class_="text-sm text-cloud-medium"),
            class_="px-6 pb-6",
        ),
        wa.divider(),
        *[
            p.a(
                wa.icon(name=icon, class_="mr-3 text-base"),
                label,
                class_=f"nav-link flex items-center px-6 py-3.5 mx-3 my-1 transition-all duration-200 cursor-pointer rounded-xl {'bg-dark text-white font-semibold' if page == current_page else 'text-cloud-dark hover:underline'}",
                data_page=page,
                **hx(
                    get=f"/app/{page}",
                    target="#main-content",
                    swap="innerHTML",
                    push_url=True,
                    trigger="mousedown",
                ),
            )
            for page, icon, label in nav_items
        ],
        wa.divider(),
        p.a(
            wa.icon(name="arrow-right-from-bracket", class_="mr-3 text-base"),
            "Logout",
            href="/app/logout",
            class_="flex items-center px-6 py-3.5 mx-3 my-1 transition-all duration-200 cursor-pointer rounded-xl text-clay hover:underline",
        ),
        class_="w-56 bg-ivory-light py-6 fixed h-screen overflow-y-auto",
    )


def create_layout(content, title="ClaudeBridge", current_page="models"):
    return p.html(
        create_head(title),
        p.body(
            p.div(
                create_nav(current_page),
                p.main(p.div(content, id="main-content"), class_="ml-56 flex-1 p-8"),
                class_="flex min-h-screen bg-ivory-light m-0 font-sans",
            ),
            class_="m-0",
        ),
    )


def create_page_fragment(content):
    return content
