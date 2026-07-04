#!/usr/bin/env python3
"""Server for Gemini Live API with Ephemeral Tokens
Provides an endpoint to generate ephemeral tokens and serves static files.
Uses Cognee HTTP API for memory management with persistent storage.
"""

import asyncio
import json
import mimetypes
import os
import datetime
import threading
import requests

from aiohttp import web
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env from the same directory as this script
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from notion_mcp_client import notion_client, init_notion, notion_search, notion_create_page, notion_append_to_page, notion_get_page
from composio_mcp_client import composio_client, init_composio

HTTP_PORT = 8000
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

COGNEE_BASE_URL = os.environ.get("COGNEE_BASE_URL", "http://localhost:8080")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_TENANT_ID = os.environ.get("COGNEE_TENANT_ID", "default")
COGNEE_USER_ID = os.environ.get("COGNEE_USER_ID", "default")

PERSISTENT_DATASET = "gemini_live_memory"

def get_cognee_headers():
    return {
        "Content-Type": "application/json",
        "X-Api-Key": COGNEE_API_KEY,
        "X-Tenant-Id": COGNEE_TENANT_ID,
        "X-User-Id": COGNEE_USER_ID
    }

def _background_store(texts):
    """Runs in a background thread: add_text + cognify to shared dataset."""
    try:
        headers = get_cognee_headers()
        add_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/add_text",
            json={"textData": texts, "datasetName": PERSISTENT_DATASET},
            headers=headers,
            timeout=30
        )
        if add_resp.status_code not in [200, 201]:
            print(f"[BG] add_text failed: {add_resp.status_code}")
            return

        requests.post(
            f"{COGNEE_BASE_URL}/api/v1/cognify",
            json={"datasets": [PERSISTENT_DATASET]},
            headers=headers,
            timeout=90
        )
        print(f"[BG] Stored {len(texts)} items, cognify done")
    except Exception as e:
        print(f"[BG] Store failed: {e}")

def store_in_background(texts):
    """Fire-and-forget: stores to shared dataset in background thread."""
    t = threading.Thread(target=_background_store, args=(texts,), daemon=True)
    t.start()

# Initialize the Gemini GenAI client
if not GEMINI_API_KEY:
    print("⚠️ Warning: GEMINI_API_KEY not found in environment. Please set it in .env or as an environment variable.")
    # Fallback to default client which might pick up GOOGLE_API_KEY
    client = genai.Client(http_options={"api_version": "v1alpha"})
else:
    client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1alpha"})


async def get_ephemeral_token(request):
    """Generates an ephemeral token for the Gemini Live API."""
    try:
        # Optional: Allow client to pass an API key
        # data = await request.json()
        # api_key = data.get("api_key")
        # if api_key:
        #     local_client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        # else:
        #     local_client = client

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        expire_time = now + datetime.timedelta(minutes=30)
        
        # Create an ephemeral token
        token = client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": expire_time.isoformat(),
                "new_session_expire_time": (now + datetime.timedelta(minutes=1)).isoformat(),
                "http_options": {"api_version": "v1alpha"},
            }
        )

        return web.json_response({
            "token": token.name,
            "expires_at": expire_time.isoformat()
        })
    except Exception as e:
        print(f"Error generating ephemeral token: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def cognee_remember(request):
    """Stores data in shared knowledge graph. Returns instantly, stores in background."""
    try:
        data = await request.json()
        text = data.get("text")

        if not text:
            return web.json_response({"error": "text is required"}, status=400)

        store_in_background([text])

        return web.json_response({
            "status": "queued",
            "dataset": PERSISTENT_DATASET
        })

    except Exception as e:
        print(f"Cognee remember error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def cognee_remember_batch(request):
    """Stores multiple texts at once. Returns instantly, stores in background."""
    try:
        data = await request.json()
        texts = data.get("texts", [])

        if not texts:
            return web.json_response({"error": "texts array is required"}, status=400)

        store_in_background(texts)

        return web.json_response({
            "status": "queued",
            "count": len(texts),
            "dataset": PERSISTENT_DATASET
        })

    except Exception as e:
        print(f"Cognee batch remember error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def cognee_recall(request):
    """Searches the shared knowledge graph across all sessions."""
    try:
        data = await request.json()
        query = data.get("query")

        if not query:
            return web.json_response({"error": "query is required"}, status=400)

        headers = get_cognee_headers()
        recall_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/recall",
            json={
                "query": query,
                "searchType": "CHUNKS", #CHUNKS
                "datasets": [PERSISTENT_DATASET]
            },
            headers=headers,
            timeout=30
        )

        if recall_resp.status_code == 404:
            return web.json_response({"result": None, "message": "No memories found"})

        if recall_resp.status_code != 200:
            return web.json_response({
                "error": f"Recall failed: {recall_resp.status_code}",
                "details": recall_resp.text
            }, status=500)

        result = recall_resp.json()
        return web.json_response({"result": result, "dataset": PERSISTENT_DATASET})

    except Exception as e:
        print(f"Cognee recall error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def cognee_forget(request):
    """Deletes the shared knowledge graph."""
    try:
        headers = get_cognee_headers()
        forget_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/forget",
            json={"dataset": PERSISTENT_DATASET},
            headers=headers,
            timeout=90
        )

        if forget_resp.status_code != 200:
            return web.json_response({
                "error": f"Forget failed: {forget_resp.status_code}",
                "details": forget_resp.text
            }, status=500)

        return web.json_response({"status": "forgotten", "dataset": PERSISTENT_DATASET})

    except Exception as e:
        print(f"Cognee forget error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def cognee_cognify(request):
    """Manually triggers cognify for the shared dataset."""
    try:
        headers = get_cognee_headers()
        cognify_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/cognify",
            json={"datasets": [PERSISTENT_DATASET]},
            headers=headers,
            timeout=90
        )

        if cognify_resp.status_code not in [200, 201, 202]:
            return web.json_response({
                "error": f"Cognify failed: {cognify_resp.status_code}"
            }, status=500)

        return web.json_response({"status": "cognified", "dataset": PERSISTENT_DATASET})

    except Exception as e:
        print(f"Cognee cognify error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def notion_search_endpoint(request):
    """Search Notion pages and databases."""
    try:
        data = await request.json()
        query = data.get("query", "")

        if not query:
            return web.json_response({"error": "query is required"}, status=400)

        result = await notion_search(query)
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Notion search error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def notion_create_page_endpoint(request):
    """Create a new page in Notion."""
    try:
        data = await request.json()
        title = data.get("title", "")
        content = data.get("content", "")
        parent_id = data.get("parent_id")

        if not title or not content:
            return web.json_response({"error": "title and content are required"}, status=400)

        result = await notion_create_page(title, content, parent_id)
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Notion create page error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def notion_append_endpoint(request):
    """Append content to an existing Notion page."""
    try:
        data = await request.json()
        page_id = data.get("page_id", "")
        content = data.get("content", "")

        if not page_id or not content:
            return web.json_response({"error": "page_id and content are required"}, status=400)

        result = await notion_append_to_page(page_id, content)
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Notion append error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def notion_get_page_endpoint(request):
    """Get content from a Notion page."""
    try:
        data = await request.json()
        page_id = data.get("page_id", "")

        if not page_id:
            return web.json_response({"error": "page_id is required"}, status=400)

        result = await notion_get_page(page_id)
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Notion get page error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def notion_list_tools_endpoint(request):
    """List available Notion MCP tools."""
    try:
        if not notion_client.session:
            return web.json_response({"error": "Notion MCP client not connected"}, status=500)

        tools = [{"name": t.name, "description": t.description} for t in notion_client.tools]
        return web.json_response({"tools": tools})

    except Exception as e:
        print(f"Notion list tools error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# Composio MCP endpoints
async def composio_call_endpoint(request):
    """Generic endpoint to call any Composio tool."""
    try:
        data = await request.json()
        tool_name = data.get("tool_name", "")
        arguments = data.get("arguments", {})

        if not tool_name:
            return web.json_response({"error": "tool_name is required"}, status=400)

        result = await composio_client.call_tool(tool_name, arguments)
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Composio call error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def composio_list_tools_endpoint(request):
    """List available Composio MCP tools."""
    try:
        if not composio_client.session:
            return web.json_response({"error": "Composio MCP client not connected"}, status=500)

        tools = [{"name": t.name, "description": t.description} for t in composio_client.tools]
        return web.json_response({"tools": tools})

    except Exception as e:
        print(f"Composio list tools error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def serve_static_file(request):
    """Serve static files from the frontend directory."""
    path = request.match_info.get("path", "index.html")

    # Security: prevent directory traversal
    path = path.lstrip("/")
    if ".." in path:
        return web.Response(text="Invalid path", status=400)

    # Default to index.html
    if not path or path == "/":
        path = "index.html"

    # Get the full file path - serve from frontend folder
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    file_path = os.path.join(frontend_dir, path)

    # Check if file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(text="File not found", status=404)

    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"

    # Read and serve the file
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return web.Response(body=content, content_type=content_type)
    except Exception as e:
        print(f"Error serving file {path}: {e}")
        return web.Response(text="Internal server error", status=500)


async def main():
    """Starts the HTTP server."""
    app = web.Application()
    
    # API endpoints
    app.router.add_post("/api/token", get_ephemeral_token)
    app.router.add_post("/api/cognee/remember", cognee_remember)
    app.router.add_post("/api/cognee/remember_batch", cognee_remember_batch)
    app.router.add_post("/api/cognee/cognify", cognee_cognify)
    app.router.add_post("/api/cognee/recall", cognee_recall)
    app.router.add_post("/api/cognee/forget", cognee_forget)

    # Notion MCP endpoints
    app.router.add_post("/api/notion/search", notion_search_endpoint)
    app.router.add_post("/api/notion/create_page", notion_create_page_endpoint)
    app.router.add_post("/api/notion/append", notion_append_endpoint)
    app.router.add_post("/api/notion/get_page", notion_get_page_endpoint)
    app.router.add_get("/api/notion/tools", notion_list_tools_endpoint)

    # Composio MCP endpoints (Slack, Gmail, Google Calendar)
    app.router.add_post("/api/composio/call", composio_call_endpoint)
    app.router.add_get("/api/composio/tools", composio_list_tools_endpoint)

    # Initialize Notion MCP client
    notion_ok = await init_notion()
    if notion_ok:
        print("  ✅ Notion MCP connected")
    else:
        print("  ⚠️  Notion MCP not available (set NOTION_ACCESS_TOKEN)")

    # Initialize Composio MCP client
    composio_ok = await init_composio()
    if composio_ok:
        print("  ✅ Composio MCP connected (Slack, Gmail, Calendar)")
    else:
        print("  ⚠️  Composio MCP not available (set COMPOSIO_API_KEY)")
    
    # Static files
    app.router.add_get("/", serve_static_file)
    app.router.add_get("/{path:.*}", serve_static_file)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║     Gemini Live API Server (Ephemeral Token Approach)     ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  📱 Web Interface: http://localhost:{HTTP_PORT:<5}                   ║
║  🔑 API Endpoint:  POST /api/token                         ║
║  🧠 Cognee Cloud:  {COGNEE_BASE_URL[:40]:<40} ║
║                                                            ║
║  Instructions:                                             ║
║  1. Ensure GOOGLE_API_KEY is set in your environment       ║
║  2. Open http://localhost:{HTTP_PORT} in your browser              ║
║  3. Click Connect to start!                                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    # Keep the server running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
