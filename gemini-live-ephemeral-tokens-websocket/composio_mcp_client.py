import asyncio
import os
import json
import base64
import re
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


async def calendar_delete_event(event_id: str, calendar_id: str = "primary"):
    result = await composio_client.call_tool("GOOGLECALENDAR_DELETE_EVENT", {
        "event_id": event_id,
        "calendar_id": calendar_id
    })
    return result


# Google Drive tools
async def gdrive_find_file(query: str, max_results: int = 10):
    result = await composio_client.call_tool("GOOGLEDRIVE_FIND_FILE", {
        "query": query,
        "max_results": max_results,
    })
    return result


async def gdrive_get_file_metadata(file_id: str):
    result = await composio_client.call_tool("GOOGLEDRIVE_GET_FILE_METADATA", {
        "file_id": file_id,
    })
    return result


async def gdrive_download_file(file_id: str, mime_type: str = None):
    arguments = {"file_id": file_id}
    if mime_type:
        arguments["mime_type"] = mime_type
    result = await composio_client.call_tool("GOOGLEDRIVE_DOWNLOAD_FILE", arguments)
    return result


async def gdrive_create_file(name: str, mime_type: str = "application/octet-stream", parent_id: str = None):
    """Creates a file entry in Google Drive (metadata-only; no content upload via SDK staging).
    Returns {id, name, display_url, mimeType}."""
    arguments = {
        "name": name,
        "mimeType": mime_type,
    }
    if parent_id:
        arguments["parents"] = [parent_id]
    result = await composio_client.call_tool("GOOGLEDRIVE_CREATE_FILE", arguments)
    return result


async def gdrive_create_file_from_text(file_name: str, text_content: str, mime_type: str = "text/plain", parent_id: str = None):
    """Creates a file in Google Drive with actual text content. Returns {id, name, display_url, mimeType}."""
    arguments = {
        "file_name": file_name,
        "text_content": text_content,
        "mime_type": mime_type,
    }
    if parent_id:
        arguments["parent_id"] = parent_id
    result = await composio_client.call_tool("GOOGLEDRIVE_CREATE_FILE_FROM_TEXT", arguments)
    return result


async def gdrive_upload_binary(name: str, raw_bytes: bytes, mime_type: str = "application/octet-stream", parent_id: str = None):
    """Uploads binary content to Google Drive via Composio S3 staging.
    Step 1: Stage to S3 via COMPOSIO_REMOTE_WORKBENCH. Step 2: GOOGLEDRIVE_UPLOAD_FILE."""
    b64 = base64.b64encode(raw_bytes).decode("ascii")

    stage_code = (
        f'import base64\n'
        f'raw = base64.b64decode("{b64}")\n'
        f'out_path = "/home/user/{name}"\n'
        f'with open(out_path, "wb") as f:\n'
        f'    f.write(raw)\n'
        f'result, err = upload_local_file(out_path)\n'
        f'output = {{"result": result, "error": err}}\n'
    )

    stage_result = await composio_client.call_tool("COMPOSIO_REMOTE_WORKBENCH", {
        "code_to_execute": stage_code,
        "thought": f"Stage binary {name} to S3",
        "current_step": "STAGING_FILE",
    })

    s3key = None
    try:
        parsed = json.loads(stage_result) if isinstance(stage_result, str) else stage_result
        stdout = parsed.get("stdout", "")
        match = re.search(r"\(s3key\):\s*(\S+)", stdout)
        if match:
            s3key = match.group(1)
    except Exception:
        pass

    if not s3key:
        raise RuntimeError(f"Failed to extract s3key from workbench staging result: {stage_result}")

    upload_args = {
        "file_to_upload": {
            "name": name,
            "mimetype": mime_type,
            "s3key": s3key,
        }
    }
    if parent_id:
        upload_args["folder_to_upload_to"] = parent_id

    result = await composio_client.call_tool("GOOGLEDRIVE_UPLOAD_FILE", upload_args)
    return result


async def gdrive_create_folder(name: str, parent_id: str = None):
    arguments = {"name": name}
    if parent_id:
        arguments["parent_id"] = parent_id
    result = await composio_client.call_tool("GOOGLEDRIVE_CREATE_FOLDER", arguments)
    return result


async def gdrive_set_sharing_public(file_id: str):
    """Sets a file to be publicly accessible (anyone with link can view)."""
    arguments = {
        "file_id": file_id,
        "type": "anyone",
        "role": "reader"
    }
    result = await composio_client.call_tool("GOOGLEDRIVE_CREATE_PERMISSION", arguments)
    return result


async def gdrive_get_about():
    result = await composio_client.call_tool("GOOGLEDRIVE_GET_ABOUT", {})
    return result
