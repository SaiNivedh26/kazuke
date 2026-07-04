#!/usr/bin/env python3
"""Remote MCP Server exposing Cognee Memory, Notion, and Composio (Slack/Gmail/Calendar) tools.

Run modes:
  stdio (default):  python mcp_server.py
  HTTP with auth:   python mcp_server.py --transport http --port 9000

Remote MCP URL: http://localhost:9000/mcp
Auth: Bearer token (get from /api/token endpoint)

Configure in opencode.json / claude_desktop_config.json:
{
  "mcpServers": {
    "weekend-hack-remote": {
      "url": "http://localhost:9000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
"""

import asyncio
import json
import os
import sys
import threading
import requests
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastmcp import FastMCP
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(env_path)

COGNEE_BASE_URL = os.environ.get("COGNEE_BASE_URL", "http://localhost:8080")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_TENANT_ID = os.environ.get("COGNEE_TENANT_ID", "default")
COGNEE_USER_ID = os.environ.get("COGNEE_USER_ID", "default")
PERSISTENT_DATASET = "gemini_live_memory"

# Auth configuration
MCP_AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")
if not MCP_AUTH_TOKEN:
    MCP_AUTH_TOKEN = secrets.token_urlsafe(32)
    print(f"[Auth] Generated MCP auth token: {MCP_AUTH_TOKEN}", file=sys.stderr)


def get_cognee_headers():
    return {
        "Content-Type": "application/json",
        "X-Api-Key": COGNEE_API_KEY,
        "X-Tenant-Id": COGNEE_TENANT_ID,
        "X-User-Id": COGNEE_USER_ID
    }


# --- Token Management ---
_active_tokens: dict[str, dict] = {}


def generate_ephemeral_token(ttl_minutes: int = 60) -> dict:
    """Generate an ephemeral bearer token for MCP access."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    _active_tokens[token] = {
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc)
    }
    return {
        "token": token,
        "expires_at": expires_at.isoformat(),
        "mcp_url": f"http://localhost:9000/mcp"
    }


def validate_token(token: str) -> bool:
    """Validate a bearer token."""
    if token == MCP_AUTH_TOKEN:
        return True
    if token in _active_tokens:
        now = datetime.now(timezone.utc)
        if now < _active_tokens[token]["expires_at"]:
            return True
        else:
            del _active_tokens[token]
    return False


def cleanup_expired_tokens():
    """Remove expired tokens."""
    now = datetime.now(timezone.utc)
    expired = [t for t, info in _active_tokens.items() if now >= info["expires_at"]]
    for t in expired:
        del _active_tokens[t]


def _cognee_store_sync(texts):
    try:
        headers = get_cognee_headers()
        add_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/add_text",
            json={"textData": texts, "datasetName": PERSISTENT_DATASET},
            headers=headers,
            timeout=30
        )
        if add_resp.status_code not in [200, 201]:
            return f"add_text failed: {add_resp.status_code} {add_resp.text}"
        requests.post(
            f"{COGNEE_BASE_URL}/api/v1/cognify",
            json={"datasets": [PERSISTENT_DATASET]},
            headers=headers,
            timeout=90
        )
        return f"Stored {len(texts)} items and cognified"
    except Exception as e:
        return f"Store failed: {e}"


def _cognee_recall_sync(query):
    try:
        headers = get_cognee_headers()
        resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/recall",
            json={
                "query": query,
                "searchType": "CHUNKS",
                "datasets": [PERSISTENT_DATASET]
            },
            headers=headers,
            timeout=30
        )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            return f"Recall failed: {resp.status_code} {resp.text}"
        return resp.json()
    except Exception as e:
        return f"Recall failed: {e}"


mcp = FastMCP(
    name="WeekendHack",
    instructions="""
This MCP server provides persistent memory (Cognee), Notion workspace access, and productivity tools (Slack, Gmail, Google Calendar).

MEMORY TOOLS (Cognee) - PRIMARY:
- remember: Store facts, observations, relationships. Fires instantly, processes in background.
- recall: Search the knowledge graph for stored information. Returns relevant chunks.
- forget: Clear ALL memories from the graph.

NOTION TOOLS - SECONDARY:
- notion_search: Find pages in Notion workspace.
- notion_create_page: Create a new page with title and content.
- notion_append_to_page: Add content to an existing page.
- notion_get_page: Read page content as markdown.

PRODUCTIVITY TOOLS (Composio) - Use only when explicitly asked:
- slack_send_message / slack_list_channels
- gmail_fetch_emails / gmail_send_email
- calendar_get_events / calendar_create_event / calendar_delete_event

WORKFLOWS:
- When saving info: store in Cognee memory AND optionally in Notion
- When recalling: check Cognee first, then Notion if needed
- For calendar: use Asia/Kolkata timezone by default
""",
    version="1.0.0"
)


@mcp.tool
def remember(text: str) -> str:
    """Store a fact or observation in persistent memory (Cognee knowledge graph).
    Returns instantly, processes in background. Include date context for temporal awareness.

    Example: "On 2026-07-04: User's water bottle was gifted by grandfather"
    """
    result = _cognee_store_sync([text])
    return json.dumps({"status": "stored", "dataset": PERSISTENT_DATASET, "detail": result})


@mcp.tool
def remember_batch(texts: list[str]) -> str:
    """Store multiple facts at once in persistent memory. More efficient than individual calls.

    Example: ["On 2026-07-04: User owns a blue water bottle", "On 2026-07-04: User works at Google"]
    """
    if not texts:
        return json.dumps({"error": "texts array is required and must not be empty"})
    result = _cognee_store_sync(texts)
    return json.dumps({"status": "stored", "count": len(texts), "dataset": PERSISTENT_DATASET, "detail": result})


@mcp.tool
def recall(query: str) -> str:
    """Search the persistent knowledge graph for stored memories.
    Returns relevant chunks of information matching the query.
    Use this for cross-session recall of previously stored facts.
    """
    result = _cognee_recall_sync(query)
    if result is None:
        return json.dumps({"result": None, "message": "No memories found for this query"})
    return json.dumps({"result": result, "dataset": PERSISTENT_DATASET})


@mcp.tool
def forget() -> str:
    """Delete ALL memories from the shared knowledge graph. Use only when explicitly requested."""
    try:
        headers = get_cognee_headers()
        resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/forget",
            json={"dataset": PERSISTENT_DATASET},
            headers=headers,
            timeout=90
        )
        if resp.status_code != 200:
            return json.dumps({"error": f"Forget failed: {resp.status_code}", "details": resp.text})
        return json.dumps({"status": "forgotten", "dataset": PERSISTENT_DATASET})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("memory://status")
def memory_status() -> str:
    """Check if the Cognee memory backend is reachable."""
    try:
        headers = get_cognee_headers()
        resp = requests.get(
            f"{COGNEE_BASE_URL}/api/v1/health",
            headers=headers,
            timeout=5
        )
        return json.dumps({"status": "ok" if resp.status_code == 200 else "degraded", "code": resp.status_code})
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})


@mcp.resource("memory://dataset/{dataset_name}")
def memory_dataset_info(dataset_name: str) -> str:
    """Get info about a specific memory dataset."""
    return json.dumps({
        "dataset": dataset_name,
        "persistent_dataset": PERSISTENT_DATASET,
        "cognee_url": COGNEE_BASE_URL
    })


# --- Notion Tools ---

_notion_client = None
_notion_initialized = False


def _get_notion_client():
    global _notion_client, _notion_initialized
    if _notion_initialized:
        return _notion_client
    _notion_initialized = True
    try:
        from notion_mcp_client import notion_client, init_notion
        loop = asyncio.new_event_loop()
        loop.run_until_complete(init_notion())
        _notion_client = notion_client
    except Exception as e:
        print(f"[MCP] Notion init failed: {e}", file=sys.stderr)
    return _notion_client


def _notion_call_sync(tool_name, arguments):
    client = _get_notion_client()
    if not client or not client.session:
        return json.dumps({"error": "Notion MCP client not connected"})
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(client.call_tool(tool_name, arguments))
        return result
    finally:
        loop.close()


@mcp.tool
def notion_search(query: str) -> str:
    """Search Notion workspace for pages matching the query. Returns page IDs, titles, and metadata."""
    result = _notion_call_sync("API-post-search", {"query": query})
    return result


@mcp.tool
def notion_create_page(title: str, content: str, parent_id: str = None) -> str:
    """Create a new page in Notion with the given title and content.
    Optionally specify parent_id to create under an existing page.
    Returns the new page object with its ID.
    """
    if not parent_id:
        search_result = _notion_call_sync("API-post-search", {"query": ""})
        try:
            results = json.loads(search_result).get("results", [])
            if results:
                parent_id = results[0]["id"]
            else:
                return json.dumps({"error": "No parent page found. Provide a parent_id."})
        except json.JSONDecodeError:
            return json.dumps({"error": f"Search failed: {search_result}"})

    parent = {"page_id": parent_id}
    properties = {
        "title": {
            "title": [{"text": {"content": title}}]
        }
    }
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }
    ]
    result = _notion_call_sync("API-post-page", {
        "parent": parent,
        "properties": properties,
        "children": children
    })
    return result


@mcp.tool
def notion_append_to_page(page_id: str, content: str) -> str:
    """Append content to an existing Notion page. Use the page ID from search results."""
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }
    ]
    result = _notion_call_sync("API-patch-block-children", {
        "block_id": page_id,
        "children": children
    })
    return result


@mcp.tool
def notion_get_page(page_id: str) -> str:
    """Retrieve the content of a Notion page as markdown."""
    result = _notion_call_sync("API-retrieve-page-markdown", {"page_id": page_id})
    return result


# --- Composio Tools ---

_composio_client = None
_composio_initialized = False


def _get_composio_client():
    global _composio_client, _composio_initialized
    if _composio_initialized:
        return _composio_client
    _composio_initialized = True
    try:
        from composio_mcp_client import composio_client, init_composio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(init_composio())
        _composio_client = composio_client
    except Exception as e:
        print(f"[MCP] Composio init failed: {e}", file=sys.stderr)
    return _composio_client


def _composio_call_sync(tool_name, arguments):
    client = _get_composio_client()
    if not client or not client.session:
        return json.dumps({"error": "Composio client not connected"})
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(client.call_tool(tool_name, arguments))
        return result
    finally:
        loop.close()


@mcp.tool
def slack_send_message(channel: str, message: str) -> str:
    """Send a message to a Slack channel."""
    return _composio_call_sync("SLACK_SEND_MESSAGE", {
        "channel": channel,
        "markdown_text": message
    })


@mcp.tool
def slack_list_channels() -> str:
    """List all channels in the connected Slack workspace."""
    return _composio_call_sync("SLACK_LIST_ALL_CHANNELS", {})


@mcp.tool
def gmail_fetch_emails(query: str = None, max_results: int = 10) -> str:
    """Fetch emails from Gmail. Optionally filter by query (e.g., 'from:alice', 'subject:meeting')."""
    arguments = {"max_results": max_results}
    if query:
        arguments["query"] = query
    return _composio_call_sync("GMAIL_FETCH_EMAILS", arguments)


@mcp.tool
def gmail_send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail."""
    return _composio_call_sync("GMAIL_SEND_EMAIL", {
        "to": to,
        "subject": subject,
        "body": body
    })


@mcp.tool
def calendar_get_events(time_min: str = None, time_max: str = None, max_results: int = 10) -> str:
    """Get upcoming events from Google Calendar. Use ISO 8601 datetime format (e.g., '2026-07-04T00:00:00')."""
    arguments = {"max_results": max_results}
    if time_min:
        arguments["time_min"] = time_min
    if time_max:
        arguments["time_max"] = time_max
    return _composio_call_sync("GOOGLECALENDAR_EVENTS_LIST", arguments)


@mcp.tool
def calendar_create_event(
    summary: str,
    start_datetime: str,
    timezone: str = "Asia/Kolkata",
    end_datetime: str = None,
    event_duration_hour: int = 1,
    event_duration_minutes: int = 0,
    description: str = None
) -> str:
    """Create a Google Calendar event.
    Use ISO 8601 datetime without timezone suffix (e.g., '2026-07-04T14:30:00').
    Timezone: 'Asia/Kolkata' for IST, 'America/New_York' for EST.
    Provide either end_datetime OR event_duration_hour/minutes.
    """
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
    return _composio_call_sync("GOOGLECALENDAR_CREATE_EVENT", arguments)


@mcp.tool
def calendar_delete_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete a Google Calendar event by its ID. Use calendar_get_events first to find event IDs."""
    return _composio_call_sync("GOOGLECALENDAR_DELETE_EVENT", {
        "event_id": event_id,
        "calendar_id": calendar_id
    })


if __name__ == "__main__":
    import argparse
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount
    from starlette.middleware import Middleware
    import uvicorn

    parser = argparse.ArgumentParser(description="WeekendHack MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"[MCP] Starting WeekendHack MCP server (transport={args.transport})", file=sys.stderr)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport in ("http", "sse"):
        # Get the MCP ASGI app - FastMCP uses Streamable HTTP for both
        mcp_app = mcp.http_app(path="/mcp")

        # Auth middleware class
        class AuthMiddleware:
            def __init__(self, app):
                self.app = app

            async def __call__(self, scope, receive, send):
                if scope["type"] != "http":
                    await self.app(scope, receive, send)
                    return

                path = scope.get("path", "")
                
                # Skip auth for token and health endpoints
                if path in ("/api/token", "/health"):
                    await self.app(scope, receive, send)
                    return

                # Check auth header
                headers = dict(scope.get("headers", []))
                auth_header = headers.get(b"authorization", b"").decode()
                
                if not auth_header.startswith("Bearer "):
                    response = JSONResponse({"error": "Missing or invalid Authorization header"}, status_code=401)
                    await response(scope, receive, send)
                    return

                token = auth_header[7:]
                if not validate_token(token):
                    response = JSONResponse({"error": "Invalid or expired token"}, status_code=401)
                    await response(scope, receive, send)
                    return

                await self.app(scope, receive, send)

        # Token endpoint
        async def token_endpoint(request: Request):
            cleanup_expired_tokens()
            try:
                body = await request.json()
                ttl = body.get("ttl_minutes", 60)
            except:
                ttl = 60
            
            result = generate_ephemeral_token(ttl)
            return JSONResponse(result)

        # Health endpoint (no auth)
        async def health_endpoint(request: Request):
            return JSONResponse({"status": "ok", "server": "WeekendHack MCP", "version": "1.0.0"})

        # Build the Starlette app with MCP lifespan
        routes = [
            Route("/api/token", token_endpoint, methods=["POST"]),
            Route("/health", health_endpoint, methods=["GET"]),
            Route("/mcp", endpoint=mcp_app, methods=["GET", "POST", "DELETE"]),
        ]

        app = Starlette(
            routes=routes,
            middleware=[Middleware(AuthMiddleware)],
            lifespan=mcp_app.lifespan
        )

        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║           WeekendHack Remote MCP Server                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  MCP URL:     http://{args.host}:{args.port}/mcp                    ║
║  Token API:   POST http://{args.host}:{args.port}/api/token         ║
║  Health:      GET  http://{args.host}:{args.port}/health            ║
║                                                                  ║
║  Static Token: {MCP_AUTH_TOKEN[:20]}...                           ║
║                                                                  ║
║  Get ephemeral token:                                            ║
║  curl -X POST http://localhost:{args.port}/api/token                 ║
║                                                                  ║
║  Use in coding agents:                                           ║
║  {{                                                                ║
║    "mcpServers": {{                                                ║
║      "weekend-hack": {{                                            ║
║        "url": "http://localhost:{args.port}/mcp",                    ║
║        "headers": {{"Authorization": "Bearer TOKEN"}}              ║
║      }}                                                            ║
║    }}                                                              ║
║  }}                                                                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""", file=sys.stderr)

        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
