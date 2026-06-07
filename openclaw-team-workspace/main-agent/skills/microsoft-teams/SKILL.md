---
name: microsoft-teams
description: Microsoft Teams integration through Composio v3 for listing teams, channels, chats, users, messages, and meetings. Use when the agent needs to work with Microsoft Teams via Composio v3 SDK, especially to read teams data, send or reply to messages, create chats or meetings, or manage authentication.
---

# Microsoft Teams (Composio v3 SDK)

Use the **current Composio v3 SDK** patterns exclusively.

## Required Environment

| Variable                         | Description                        |
| -------------------------------- | ---------------------------------- |
| `COMPOSIO_API_KEY`               | Composio API key                   |
| `USER_ID`                        | Stable app-side user identifier    |
| `MICROSOFT_TEAMS_AUTH_CONFIG_ID` | Auth config ID starting with `ac_` |

- Python venv: `/opt/skills-venv/bin/python3`
- Python package: `composio`

IMPORTANT: Team features take time, before commiting to the task, first lets the user know that you are going to do their task, and that this might take some time.

## Get user's timezone

Microsoft teams tools via composio return datetime data in UTC, hence always convert responses to user's timezone.
to get user's tiemzone, run this command:

```python
import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".outlook-mcp"
CREDS_FILE = CONFIG_DIR / "credentials.json"
CONFIG_FILE = CONFIG_DIR / "config.json"

API = "https://graph.microsoft.com/v1.0/me"


def get_timezone() -> str:
    """
    Read timezone from ~/.outlook-mcp/config.json.

    Equivalent to:
      jq -r '.timezone // empty' "$CONFIG_FILE"

    Falls back to UTC if:
      - config.json does not exist
      - timezone is missing
      - timezone is null
      - timezone is an empty string
      - JSON is invalid
    """
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            config = json.load(f)

        timezone = config.get("timezone")

        if not timezone:
            return "UTC"

        return str(timezone)

    except FileNotFoundError:
        return "UTC"
    except json.JSONDecodeError:
        return "UTC"
    except OSError:
        return "UTC"


TIMEZONE = get_timezone()
os.environ["TZ"] = TIMEZONE
```

## Runtime Discovery (THIS IS VERY IMPORTANTS, FAILURE TO DO THIS CAN LEAD TO IMPROPER TOOL CALLS, CAUSING INACCURACIES AND LOW EFFICIENCY)

Always verify tool parameters via `composio.tools.get` before calling a tool for the first time in a session, as schemas may vary by auth config.

```python
import os
from composio import Composio

composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
tools = composio.tools.get(
    user_id=os.environ["USER_ID"],
    tools=["MICROSOFT_TEAMS_TEAMS_POST_CHAT_MESSAGE"]
)
print(tools[0].parameters)
```

Authentication Workflow
Check for active Teams connected account.
If none, generate a hosted auth link.
Send the link to the user and wait for confirmation.
Copy

```python
import os
from composio import Composio

composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
user_id = os.environ["USER_ID"]
auth_config_id = os.environ["MICROSOFT_TEAMS_AUTH_CONFIG_ID"]

# Check status
accounts = composio.connected_accounts.list(
    user_ids=[user_id],
    auth_config_ids=[auth_config_id],
    statuses=["ACTIVE"],
)

if not accounts.items:
    # Link new account
    connection_request = composio.connected_accounts.link(
        user_id=user_id,
        auth_config_id=auth_config_id,
    )
    print(f"AUTH_URL={connection_request.redirect_url}")
else:
    print(f"CONNECTED_ACCOUNT_ID={accounts.items[0].id}")
```

Messaging Workflow
Verify Connection: Ensure connected_account_id is active.
Find Target: Use MICROSOFT_TEAMS_CHATS_GET_ALL_CHATS to find a chat_id.
Get Confirmation: Always ask the user to confirm the recipient and message content.
Execute: Use composio.tools.execute.

Send Chat Message
Copy

```python
result = composio.tools.execute(
    "MICROSOFT_TEAMS_TEAMS_POST_CHAT_MESSAGE",
    user_id=os.environ["USER_ID"],
    connected_account_id="ca_...",
    arguments={
        "chat_id": "...",
        "content": "Hello World",
        "content_type": "text" # or 'html'
    },
    dangerously_skip_version_check=True,
)
```

Create Chat (Note Parameter Naming)
Copy

```python
result = composio.tools.execute(
    "MICROSOFT_TEAMS_TEAMS_CREATE_CHAT",
    user_id=os.environ["USER_ID"],
    connected_account_id="ca_...",
    arguments={
        "chatType": "oneOnOne", # or 'group'
        "members": [
            {
                "userOdataBind": "https://graph.microsoft.com/v1.0/users/me",
                "roles": ["owner"]
            },
            {
                "userOdataBind": "https://graph.microsoft.com/v1.0/users/target@example.com",
                "roles": ["owner"]
            }
        ]
    },
    dangerously_skip_version_check=True,
)
```

Finding Messages Workflow
For general requests about the most recent message, `lastUpdatedDateTime` is returning inaccurate data, hence the code below calls the microsoft API directly.
Use this over MICROSOFT_TEAMS_CHATS_GET_ALL_CHATS with `lastUpdatedDateTime`.

Most Resent Message

```python
import os
import json
import requests
from composio import Composio
from datetime import datetime, timedelta, timezone

TIMEZONE_NAME = "Asia/Calcutta"
TZ_INFO = timezone(timedelta(hours=5, minutes=30))

composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
user_id = os.environ["USER_ID"]
auth_config_id = os.environ["MICROSOFT_TEAMS_AUTH_CONFIG_ID"]

accounts = composio.connected_accounts.list(
    user_ids=[user_id],
    auth_config_ids=[auth_config_id],
    statuses=["ACTIVE"],
)

if not accounts.items:
    print(json.dumps({"error": "No active Teams connection found"}))
    raise SystemExit(1)

ca_id = accounts.items[0].id
account = composio.connected_accounts.get(ca_id)

state_val = account.state.val if account.state else {}
state_dict = state_val.model_dump() if hasattr(state_val, "model_dump") else state_val

access_token = (
    state_dict.get("access_token")
    or state_dict.get("accessToken")
    or state_dict.get("token")
)

if not access_token:
    print(json.dumps({
        "error": "No access token found",
        "available_keys": list(state_dict.keys()) if isinstance(state_dict, dict) else [],
    }))
    raise SystemExit(1)

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/chats",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    },
    params={
        "$expand": "lastMessagePreview",
        "$orderby": "lastMessagePreview/createdDateTime desc",
        "$top": "5",
    },
    timeout=30,
)

if not response.ok:
    print(json.dumps({
        "error": "Graph request failed",
        "status_code": response.status_code,
        "body": response.text,
    }))
    raise SystemExit(1)

data = response.json()
chats = data.get("value", [])

if not chats:
    print(json.dumps({"status": "no_chats_returned"}))
    raise SystemExit(0)

chat = chats[0]
preview = chat.get("lastMessagePreview")

if not preview or not preview.get("createdDateTime"):
    print(json.dumps({
        "status": "no_lastMessagePreview",
        "chat_keys": list(chat.keys()),
        "chat": chat,
    }))
    raise SystemExit(0)

utc_dt = datetime.fromisoformat(preview["createdDateTime"].replace("Z", "+00:00"))
local_dt = utc_dt.astimezone(TZ_INFO)

print(json.dumps({
    "status": "success",
    "from": preview.get("from", {}).get("user", {}).get("displayName"),
    "body": preview.get("body", {}).get("content"),
    "time": local_dt.strftime("%Y-%m-%d %I:%M %p"),
    "topic": chat.get("topic") or "Direct Chat",
    "chat_id": chat.get("id"),
}, ensure_ascii=False))
```

## Key Tool Slugs

| Slug                                         | Description                                |
| -------------------------------------------- | ------------------------------------------ |
| `MICROSOFT_TEAMS_GET_MY_PROFILE`             | Get current user profile (ID, email, etc.) |
| `MICROSOFT_TEAMS_CHATS_GET_ALL_CHATS`        | List recent chats                          |
| `MICROSOFT_TEAMS_CHATS_GET_ALL_MESSAGES`     | Fetch messages from a chat (`chat_id`)     |
| `MICROSOFT_TEAMS_TEAMS_POST_CHAT_MESSAGE`    | Send message to a chat                     |
| `MICROSOFT_TEAMS_TEAMS_CREATE_CHAT`          | Create a new chat                          |
| `MICROSOFT_TEAMS_TEAMS_POST_CHANNEL_MESSAGE` | Post message to a channel                  |
| `MICROSOFT_TEAMS_LIST_ASSOCIATED_TEAMS`      | List all teams user is associated with     |
| `MICROSOFT_TEAMS_GET_CHANNEL`                | Get details of a specific channel          |
| `MICROSOFT_TEAMS_TEAMS_LIST_CHANNELS`        | List all channels in a team                |
| `MICROSOFT_TEAMS_GET_PRESENCE`               | Get a user's presence status               |
| `MICROSOFT_TEAMS_SET_PRESENCE`               | Set current user's presence                |
| `MICROSOFT_TEAMS_CREATE_MEETING`             | Create an online meeting                   |

## Failure Handling

| Symptom               | Cause                         | Fix                                                                         |
| --------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| `InvalidParams`       | Mismatched argument names     | Run `composio.tools.get` to verify the exact schema (e.g. `userOdataBind`). |
| `401 Unauthorized`    | Expired or missing connection | Re-run the Authentication Workflow to generate a new link.                  |
| `403 Forbidden`       | Missing Graph permissions     | Check if the app has the required scopes (e.g. `Chat.ReadWrite`).           |
| Tool version mismatch | SDK versioning                | Pass `dangerously_skip_version_check=True` in `execute`.                    |
| `chat_id` not found   | Stale cache or wrong ID       | Re-list chats using `MICROSOFT_TEAMS_CHATS_GET_ALL_CHATS`.                  |

## Do Not Do These

- ❌ Do not use legacy `ComposioToolSet` or `Action` enums.
- ❌ Do not use snake_case for OData binding fields if the schema shows camelCase (e.g. use `userOdataBind`).
- ❌ Do not create a new chat if an existing `oneOnOne` chat can be found.
- ❌ Do not send messages or create meetings without explicit user confirmation.
- ❌ Do not assume all 169 tools are available; always check `toolkits=["microsoft_teams"]`.
- ❌ Do not treat datetime retrieved from teams tool responses as user's timezone (they always respond in UTC), check user's timezone then convert to their timezone.

## Safety & Confirmations

**Read-only actions (No confirmation):**

- Listing chats/messages/teams.
- Getting profiles.

**User-visible actions (Confirmation REQUIRED):**

- Posting messages (chat or channel).
- Creating chats or teams.
- Updating status/presence.

Ask: "Action: [Action] | To: [Recipient] | Message: [Content]. Confirm?"
