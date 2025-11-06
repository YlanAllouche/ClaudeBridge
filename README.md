
<h1 style="display: flex; align-items: center; gap: 10px;">
  <img src="./claudebridge/static/icon.png" alt="description" height="50">
  <span>ClaudeBridge</span>
</h1>

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)
![HTMX](https://img.shields.io/badge/HTMX-36C?logo=htmx&logoColor=fff)
![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-%2338B2AC.svg?logo=tailwind-css&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-D97757?logo=claude&logoColor=fff)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=Prometheus&logoColor=white)


Self-hosted gateway that mirrors Claude Pro’s connection handshake, exposes an OpenAI-compatible API, and includes built-in identity management, Prometheus telemetry, web UI, and subscription/usage monitoring dashboards.

## Overview

**ClaudeBridge enables you to:**

- Use your Claude Pro subscription anywhere either an OpenAI or Anthropic endpoint is accepted
- Login with Claude Pro/Max through a friendly web ui
- Record and gives complete observability over your subscription usage
- This include estimated $ value of the subscription
- Exposes models that do not seem otherwise available in ClaudeCode (namely `sonnet 3.7` and `opus 3`)
- Works across apps and machines
- Allows to share the subscription across several users or applications with internal tokens
- Shows real subscription usage in % for 5h and 7d window limits

---

<details> 

<summary>

### About the project

</summary>

Keep in mind this is immature code prone to bugs but the base function of enabling OpenAI-style client on ClaudeCode subsccription has been fairly stable.


There is a some amount of technical debt due to a late move to components and modular server paths resulting in potential code duplication between the ui and blueprints folders.

The code was also written with tailwind's CDN version which ended up breaking good chunks of the design when finally bundling the css.

The project was developed with the idea of writing a python backend with a well optimized, snappy and SPA-like frontend without writing a single line of Javascript or installing node.js/npm.
This of course becomes increasingly hard as we bundle the app.

This includes in-line Javascript if it's more than 1-2 lines but does not include readily available [WebComponent libraries](https://github.com/OvidijusParsiunas/deep-chat).

I would need to look more closely about everything ClaudeCode does but so far the proxy is not adding noticeable delays to the answer in fact, it sometime seems to stream faster.


</details>


## Installation

> 💡 Keep in mind that this repo does not bundle the frontend dependencies so you need to run the build script, use the container or use the wheel build from the release section

### Admin password protection

> 💡 If a password is not set in config or in the env variable or is not disabled one will be generated for you in stdout at first run

``` bash
docker run -e DISABLE_UI_PASSWORD=true claudebridge  # No password
docker run -e UI_PASSWORD=mysecret claudebridge      # Password
```


### Build and install wheel locally (downloads frontend deps + builds)

``` bash 
python -m claudebridge.scripts.build
```

- Install locally
``` bash
pip install dist/claudebridge-0.1.0-py3-none-any.whl
# Alternatively, pip install . should work once built as long as `download_deps` has run once
```

- Run

```
claudebridge
```

### Containers

- Build Locally:
```bash
docker build -t claudebridge .
```

- or pull from this repo's registry:
``` bash
docker pull ghcr.io/ylanallouche/claudebridge:latest
```

- Run
``` bash
docker run -p 8000:8000 \
  -v ~/.config/claudebridge:/root/.config/claudebridge \ 
  # or -v ./claudebridge-data:/root/.config/claudebridge to map in current directory
  -e DEBUG=info \
ghcr.io/ylanallouche/claudebridge:latest 
  # or just claudebridge to use locally built container

```

### Dev env

``` bash
python -m claudebridge.scripts.download_deps # run once to cache the various CDN stored js/css bundles
python -m claudebridge.dev # will start the app with Flask in dev mode with auto reloader and DEBUG on as well as the tailwindcss cli watching the python files.
```

## Server setup

> 💡 Note that: if you do not want to use the service anymore, you can remove the session in your Anthropic console 

First go to account and start the account connection steps:

<details>
<summary>

### Screenshot

</summary>

![connection](screenshots/connection.png)

</details>

In a browser you are logged into Anthropic:
- Go to [http://localhost:8000](http://localhost:8000) or whereever you are hosting the app
- Give your account a name - *it can be anything, it's for local purposes only*
- Open the link
- authorize, get the code
- paste into `ClaudeBridge`

Optionally, to also get the % of use of your subscription:
- go to the `claude.ai`
- `settings` > `usage`
- `inspect the page` > go to `network`
- refresh the page
- filter for the endpoint getting the data by typing `usage`
- look for the request the page uses to poll the subscription usage

<details>
<summary>
=> Get this value

</summary>

![session-key](screenshots/session-key.png)

</details>

- and paste into the second field of the same account page in ClaudeBridge.

<details>
<summary>
You should then get something like this

</summary>

![connection](screenshots/account.png)

</details>



### Client setup

- Go to users
- Add new user
- copy the auth token 

> 💡 the `copy to clipbard` may only work over https, it seems. You can always do ` cat ~/.config/claudebridge/config.json | grep "<your-user-name>" -B1 ` to get the token back.

##### ClaudeCode example

Using 

```bash
ANTHROPIC_BASE_URL="http://localhost:8000" ANTHROPIC_API_KEY="mykey" claude
```

##### Any OpenAI-style client - here CodeCompanion in lua for nvim

```lua
bureau = function()
	return require("codecompanion.adapters").extend("openai_compatible", {
		name = "bureau",
		env = {
			url = "http://bureau:8000",
			chat_url = "/v1/chat/completions",
			models_endpoint = "/v1/models",
			api_key = "Your internal token here", 
		},
		schema = {
			model = {
				default = "claude-haiku-4-5",
			},
		},
	})
end,
```

## Full documentation

<detail>

<summary>

### Network interactions

</summary>

```mermaid
sequenceDiagram
    participant Client
    participant ClaudeBridge
    participant MetricsManager as Metrics Manager<br/>/metrics
    participant ClaudeAPI as Claude Pro/Max<br/>
    participant UsageAPI as claude.ai/usage<br/>Web API
    
    Client->>ClaudeBridge: POST /v1/chat/completions
    ClaudeBridge->>MetricsManager: Capture Request Data
    
    ClaudeBridge->>ClaudeBridge: Validate Token, Rate Limit
    ClaudeBridge->>ClaudeAPI: Refresh Token (if needed)
    ClaudeAPI-->>ClaudeBridge: New Access Token
    
    ClaudeBridge->>ClaudeAPI: Stream Request + Token
    ClaudeAPI-->>ClaudeBridge: Stream Response + Usage Metadata
    ClaudeBridge->>MetricsManager: Capture Response Data
    
    ClaudeBridge-->>Client: Response + Subscription Headers
    
    par Web Session Polling
        ClaudeBridge->>UsageAPI: Poll Usage Endpoint (5min interval)
        UsageAPI-->>ClaudeBridge: Quota %, 5h/7d
        ClaudeBridge->>MetricsManager: Capture Quota Data
        ClaudeBridge->>ClaudeBridge: Update accounts.json
    end
    
    Client->>ClaudeBridge: GET /metrics
    ClaudeBridge->>MetricsManager: Fetch Prometheus Metrics
    MetricsManager-->>Client: Prometheus Format Response

```

</details>

<details> 

<summary>

### Session boundaries and account usage tracking

</summary>

The application has 2 sources of truths when it comes to figuring out the state of the account and session boundaries.

- `/usage` polling from `claude.ai` when available
- `rate-limiting` returned in the header on every request (this can only be confirmed when the user does make a request)


In order to do so:

- the bridge initially assumes both session are ready
- upon first request it will create the first session or close the previous one
- use the new timestamp to create a new session
- figure out if the new 5h session is part of the previous weekly limit or if a new 7d session also need to be rolled out
- then upon either:
  - hitting out-of-quota
  - or letting the timer run out (from the initial 5 hours or 7 days since the start of the session)
  - the session will end and the reason for termination will be inferred
- termination reasons can be
  - `natural`: the account did not go through the full usage window and the timer ran out
  - `ooq-5h`: the account got to the 5 hour limit
  - `ooq-7d`: the account did not get to its 5 hour limit but got to its 

- the session is only fully confirmed to be ended once the next `200` request goes through and will look like the "current" ones until then

I have only been using the Anthropic service for about a week so I'm not entirely sure I got the behavior right and it's difficult to mock.

It seems that the account can get a "grace period" when hitting 7d-OOQ but still pretty low in usage of the 5h session.

I have only seen it once but it also looks like the 7d session timer can also move around slightly so the server also has some basic guardrails for "rollover" termination reason.

Here is a full diagram of the logic:

```mermaid

flowchart TD
    Start([User Starts Session])
    
    subgraph "5h Session"
        A5["🟢 active"]
        O5H["🔴 ooq_5h<br/>(quota hit)"]
        O5D["🔴 ooq_7d<br/>(blocked)"]
        B5D["🟡 blocked_by_7d<br/>(7d expired)"]
        R5["🔵 ready"]
    end
    
    subgraph "7d Period"
        A7["🟢 active"]
        O7["🔴 ooq_7d<br/>(quota hit)"]
        R7["🔵 ready"]
    end
    
    Start --> A5
    Start --> A7
    
    A5 -->|5h quota exhausted| O5H
    A5 -->|7d blocked| O5D
    A5 -->|7d expires| B5D
    A5 -->|time expires| R5
    
    O5H --> R5
    O5D --> R5
    B5D --> R5
    
    A7 -->|7d quota hit| O7
    A7 -->|time expires| R7
    O7 --> R7
    
    O5D -.->|inherits from| O7
    
    
    style O5D fill:#c46686
    style O5H fill:#c46686
    style O7 fill:#c46686
    style A5 fill:#788c5d
    style A7 fill:#788c5d
    style R5 fill:#bcd1ca
    style R7 fill:#bcd1ca
    style B5D fill:#cc785c


```


</details>


<details> 

<summary>

### Models, chat and testing

</summary>

The models used by ClaudeCode seem to be hardcoded and not documented dynamicaly on a `/models` endpont.
This mean we also have to document them manually.
To do so, the app contains all the models I could find to work.

![models](screenshots/models.png)

In the future, if wanting to add a model you can simply enter a model in the `models` page of the app.
Then hit the "set cost" button to make sure that cost estimate is tracked for the new models.

For both built-in and custom models you can also hit the "test" button that will send a simple message to that model to check of it works which be shown to you in UI

You can find your local models overrides in `~/.config/claudebridge/config.json`

Alternatively you can use the `chat` page to test the model further.
Note that:

- the conversation are not recorded anywhere 
- both the "test" button and the built-in chat ui have thir usage tracked towards a default, built-in user called "frontend".

Lastly, you can block models from being used by your tokens and from being documented in the `/models` api endpoint.


![chat-ui](screenshots/chat-ui.png)


</details>


<details> 
<summary>

### API tokens and internal users

</summary>

> ⚠️ While the user tokens can be disabled entirely in `configs.json`, I would recommend setting one up beside security reasons: some clients don't seem to like it and it's untested (not sure how the inner metrics work without a user/token).

![user-tokens](screenshots/user-tokens.png)

You can easily:
- create new user (I recomment setting one up per app)
  - all you have to do is enter a username and press enter
- rotate keys
- set rate limit (not extensively tested)

</details>


<details> 
<summary>

### Observability - Web UI

</summary>

Claudebridge tracks every request made:
- which user makes it
- with how many tokens in/out
- on which sessions (5h/7d)
- using which models
- at what estimated cost (updating the price of a model does not change the estimate of the previous calls)

It also has knowledge of the current time limit if any as well as state of the account:

- display all the metris in an internal dashboard
- both 7d (weekly limit) and 5h (session) Out-of-Quota monitoring
- Time based or rate-limit headers bases session bound calculation
- set or update model prices as well to keep the cost estimate accurate

And use all of that to display a live dashboard in a serie of collapsible elements.

- Global usage summary:

![global-usage](screenshots/global-usage.png)

- current weekly limit during the current 5h session
![current-7d](screenshots/current-7d.png)

- past 5h sessions of the current weekly limit:

![past-5h](screenshots/past-5h.png)

- full summary of previous weekly limits:
![past-7d](screenshots/past-7d-period-and--details.png)


</details>

<details> 
<summary>

### Observability - Prometheus/Grafana

</summary>

ClaudeBridge also exposes a `/metrics` endpoint for prometheus (which can be turned off in settings).
This allows to take the data and build anything with it.

Here is a quick example:

![grafana](screenshots/grafana_example.png)


</details>

<details> 
<summary>

### Storage and config files

</summary>


ClaudeBridge doesn't use a database at the moment but a set of json object that it constently writes to.

All of them are located in `~/.config/claudebridge/`

- `config.json` - Stores user configuration
  - sets all the different options
  - admin UI password (stored plainly)
  - Internal  user/tokens
  - User rate limits
  - Blocked/custom models
  - model cost overrides
  - only one to reload if changed manually by the user
6. metrics.json - Metrics Checkpoint 
  - restores all the metrics for the dashboard and prometheus
7. rate_limits.json - Rate Limit State 
  - Sliding window data for rate limiting
  - Per-token request/token counts over time
  - allows for rate limiting to survive reboot


</details>

<details> 

<summary>


## Issues and next focus

<details> 

<summary>

### Known issues

</summary>

- [ ] Look into the low hanging fruits from Lightouse 
- [ ] Wrong default log level on module
- [ ] `/chat` does not fail gracefull with no account setup
- [ ] too many waitresses related log
- [ ] custom models with custom pricing can appear twice in the models list (only visual)
- [ ] no visual confirmation when testing a custom model in /models page
- [ ] some inconsistence in the labels on the pill in the UI especially for `termination_reason`
- [ ] unnecessary/duplicate informations in accounts.json
- [ ] smarter polling when not making requests (currently 5 minutes) although that might be what keeps the session up

</details>

<details> 
<summary>

### Future development

</summary>

#### Maintenance

- [ ] Test everything, commit mock scripts for server answers first
- [ ] Clean duplicate logic between ui and blueprints
- [ ] Move heavily towards component
- [ ] Look into WA's theme system to remove most tailwind in-line classes
- [ ] better grafana/prometheus documentation
- [ ] Fix design left somewhat broken my tailwind migration
- [ ] One-click link to setup the container on public cloud
- [ ] Find a way to treeshake WA
- [ ] Fix every lsp error
  - [ ] Will first require to do a better job witht the htmx module for pyhtml


#### Minor

- [ ] optional auth on prometheus /metrics endpoint
- [ ] while the % usage can be tracked over time in prometheus exporter in the case of a session ending naturally before reaching its window we could log how far in % the session was - currently only recording how long it took to reach it when reaching the end of the window which seems more interesting
- [ ] investigate optimal llm usage for sub as well if time of day can be a correlation


#### New features

- [/] Multi-account setup with auto queue user requests accross account based on subscription state - was unable to test: not shipped
- [ ] add timer/usage endpoint to integrate in taskbar/tmux etc
- [ ] consider firing an event on weekly/session reset
    - notify-send if not in docker
    - use `smtp` to send an email if setup in config 
- [ ] Add new rate limit rule: `%max` of session (users can't submit query if subscription window is too advanced), and `grace_countdown` how many minutes before the reset of the session does the "%max" stops applying?
- [ ] Option to switch logstyle from current dramatic formattic to `logfmt`
- [ ] Return the remaining time to reset the session directly in the 429 responses to display the timer as error message in clients
- [ ] ship as desktop app with a webview and inno/mac bundle
- [ ] Look into how this would work for people who use overrage when going over the subscription
- [ ] build alternate way to expose the Anthropic services by relying on the SDK json formatting and streaming capabilities
  - Before nearly giving up on the current connection, I had some good result with it
- [ ] integrate common llm-capabilities that may not be specifically handled or captured at the moment:
  - stop parameter 
  - temperature 
  - top_p 
  - max_tokens
  - Prompt caching
  - Citations
  - PDF support

</details>

## Dependencies

- [deep-chat](https://github.com/OvidijusParsiunas/deep-chat)
- [loguru](https://github.com/Delgan/loguru)
- flask/waitress
- [pyHtml](https://github.com/COMP1010UNSW/pyhtml-enhanced) - and my modules for [WA/CEM processing](https://github.com/YlanAllouche/pyhtml-cem) and [htmx](https://github.com/YlanAllouche/pyhtml-htmx)
- [htmx](https://github.com/bigskysoftware/htmx)
- tailwindcss - using the globally install cli, not the npm package
- [WebAwesome](https://github.com/shoelace-style/webawesome) / FontAwesome
- [highlight.js](https://github.com/highlightjs/highlight.js) to get syntax highlighting in code blocks in deep-chat llm reponses
