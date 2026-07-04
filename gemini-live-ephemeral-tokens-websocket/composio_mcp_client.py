import asyncio
import os
import json
from composio import Composio


class ComposioClient:
    def __init__(self):
        self.api_key = os.environ.get("COMPOSIO_API_KEY", "")
        self.user_id = os.environ.get("COMPOSIO_USER_ID", "default-user")
        self.client = None
        self.session = None
        self.tools = []

    async def connect(self):
        if not self.api_key:
            raise ValueError("COMPOSIO_API_KEY not set in environment")

        self.client = Composio(api_key=self.api_key)
        self.session = self.client.create(user_id=self.user_id)
        
        all_tools = self.session.tools()
        self.tools = []
        for t in all_tools:
            func = t.get('function', t)
            name = func.get('name', 'unknown')
            desc = func.get('description', '')
            self.tools.append({"name": name, "description": desc, "tool": t})
        print(f"[Composio] Connected. Available tools ({len(self.tools)}):")
        for t in self.tools:
            print(f"  • {t['name']}")

    async def call_tool(self, tool_name: str, arguments: dict):
        if not self.session:
            raise RuntimeError("Composio client not connected")

        # Meta-tools are executed directly
        if tool_name.startswith("COMPOSIO_"):
            tool_entry = next((t for t in self.tools if t['name'] == tool_name), None)
            if not tool_entry:
                raise ValueError(f"Meta-tool {tool_name} not found")
            result = self.session.execute(tool_slug=tool_name, arguments=arguments)
            return json.dumps(result.data) if hasattr(result, 'data') else str(result)
        
        # Toolkit tools (SLACK_*, GMAIL_*, etc.) must go through COMPOSIO_MULTI_EXECUTE_TOOL
        else:
            multi_args = {
                "tools": [
                    {
                        "tool_slug": tool_name,
                        "arguments": arguments
                    }
                ],
                "sync_response_to_workbench": False
            }
            result = self.session.execute(tool_slug="COMPOSIO_MULTI_EXECUTE_TOOL", arguments=multi_args)
            return json.dumps(result.data) if hasattr(result, 'data') else str(result)

    async def disconnect(self):
        self.session = None
        print("[Composio] Disconnected")


composio_client = ComposioClient()


async def init_composio():
    try:
        await composio_client.connect()
        return True
    except Exception as e:
        print(f"[Composio] Failed to connect: {e}")
        return False


# Slack tools
async def slack_send_message(channel: str, message: str):
    result = await composio_client.call_tool("SLACK_SEND_MESSAGE", {
        "channel": channel,
        "markdown_text": message
    })
    return result


async def slack_list_channels():
    result = await composio_client.call_tool("SLACK_LIST_ALL_CHANNELS", {})
    return result


# Gmail tools
async def gmail_fetch_emails(query: str = None, max_results: int = 10):
    arguments = {"max_results": max_results}
    if query:
        arguments["query"] = query
    result = await composio_client.call_tool("GMAIL_FETCH_EMAILS", arguments)
    return result


async def gmail_send_email(to: str, subject: str, body: str):
    result = await composio_client.call_tool("GMAIL_SEND_EMAIL", {
        "to": to,
        "subject": subject,
        "body": body
    })
    return result


# Google Calendar tools
async def calendar_get_events(time_min: str = None, time_max: str = None, max_results: int = 10):
    arguments = {"max_results": max_results}
    if time_min:
        arguments["time_min"] = time_min
    if time_max:
        arguments["time_max"] = time_max
    result = await composio_client.call_tool("GOOGLECALENDAR_EVENTS_LIST", arguments)
    return result


async def calendar_create_event(summary: str, start_datetime: str, timezone: str = "UTC", end_datetime: str = None, event_duration_hour: int = 1, event_duration_minutes: int = 0, description: str = None):
    arguments = {
        "summary": summary,
        "start_datetime": start_datetime,
        "timezone": timezone
    }
    if end_datetime:
        arguments["end_datetime"] = end_datetime
    else:
        arguments["event_duration_hour"] = event_duration_hour
        arguments["event_duration_minutes"] = event_duration_minutes
    if description:
        arguments["description"] = description
    result = await composio_client.call_tool("GOOGLECALENDAR_CREATE_EVENT", arguments)
    return result
