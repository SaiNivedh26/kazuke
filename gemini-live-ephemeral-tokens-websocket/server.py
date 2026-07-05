#!/usr/bin/env python3
"""Server for Gemini Live API with Ephemeral Tokens
Provides an endpoint to generate ephemeral tokens and serves static files.
Uses Cognee HTTP API for memory management with persistent storage.
"""

import asyncio
import base64
import json
import mimetypes
import os
import datetime
import threading
import time
import requests
import re
import unicodedata

from aiohttp import web
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env from the same directory as this script
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from notion_mcp_client import notion_client, init_notion, notion_search, notion_create_page, notion_append_to_page, notion_get_page
from composio_mcp_client import (
    composio_client, init_composio,
    slack_send_message, slack_list_channels,
    gmail_fetch_emails, gmail_send_email,
    calendar_get_events, calendar_create_event, calendar_delete_event,
    gdrive_find_file, gdrive_get_file_metadata, gdrive_download_file,
    gdrive_create_file, gdrive_create_file_from_text, gdrive_create_folder,
    gdrive_upload_binary, gdrive_get_about, gdrive_set_sharing_public,
)

HTTP_PORT = 8000
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

COGNEE_BASE_URL = os.environ.get("COGNEE_BASE_URL", "http://localhost:8080")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_TENANT_ID = os.environ.get("COGNEE_TENANT_ID", "default")
COGNEE_USER_ID = os.environ.get("COGNEE_USER_ID", "default")

PERSISTENT_DATASET = "gemini_live_memory"

def clean_extracted_text(text):
    """Clean extracted text by normalizing whitespace and removing control characters."""
    if not text:
        return text
    
    # Normalize unicode characters (convert fancy quotes, dashes, etc. to ASCII equivalents)
    text = unicodedata.normalize('NFKD', text)
    
    # Replace common unicode characters with ASCII equivalents
    text = text.replace('\u2014', '-')  # em dash
    text = text.replace('\u2013', '-')  # en dash
    text = text.replace('\u2018', "'")  # left single quote
    text = text.replace('\u2019', "'")  # right single quote
    text = text.replace('\u201c', '"')  # left double quote
    text = text.replace('\u201d', '"')  # right double quote
    text = text.replace('\u2026', '...')  # ellipsis
    text = text.replace('\u00a0', ' ')  # non-breaking space
    
    # Remove control characters except newlines and tabs
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t')
    
    # Normalize whitespace: replace multiple spaces with single space, but preserve newlines
    text = re.sub(r'[^\S\n]+', ' ', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove multiple consecutive newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


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
        from datetime import datetime
        
        headers = get_cognee_headers()
        
        # Add timestamp to each text
        timestamped_texts = []
        created_at = datetime.now().isoformat()
        for text in texts:
            timestamped_texts.append(f"{text} [Created: {created_at}]")
        
        print(f"[BG] Storing {len(timestamped_texts)} items at {created_at}")
        
        add_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/add_text",
            json={"textData": timestamped_texts, "datasetName": PERSISTENT_DATASET},
            headers=headers,
            timeout=30
        )
        if add_resp.status_code not in [200, 201]:
            print(f"[BG] add_text failed: {add_resp.status_code} - {add_resp.text[:200]}")
            return

        cognify_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/cognify",
            json={"datasets": [PERSISTENT_DATASET]},
            headers=headers,
            timeout=90
        )
        print(f"[BG] Stored {len(timestamped_texts)} items, cognify status: {cognify_resp.status_code}")
    except Exception as e:
        print(f"[BG] Store failed: {e}")

def store_in_background(texts):
    """Fire-and-forget: stores to shared dataset in background thread."""
    t = threading.Thread(target=_background_store, args=(texts,), daemon=True)
    t.start()


def resolve_dataset_id(dataset_name):
    """Resolve a dataset name to its UUID via the Cognee datasets listing."""
    try:
        headers = get_cognee_headers()
        resp = requests.get(
            f"{COGNEE_BASE_URL}/api/v1/datasets/",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return None
        for ds in resp.json():
            if ds.get("name") == dataset_name:
                return ds.get("id")
    except Exception as e:
        print(f"resolve_dataset_id error: {e}")
    return None


async def cognee_visualize(request):
    """Proxies the Cognee graph visualization HTML for the shared dataset."""
    try:
        dataset_id = request.query.get("dataset_id")
        if not dataset_id:
            dataset_id = resolve_dataset_id(PERSISTENT_DATASET)
        if not dataset_id:
            return web.json_response(
                {"error": "Could not resolve dataset_id for visualization"},
                status=404,
            )

        headers = get_cognee_headers()
        viz_resp = requests.get(
            f"{COGNEE_BASE_URL}/api/v1/visualize",
            params={"dataset_id": dataset_id},
            headers=headers,
            timeout=60,
        )

        if viz_resp.status_code != 200:
            return web.json_response(
                {
                    "error": f"Visualize failed: {viz_resp.status_code}",
                    "details": viz_resp.text,
                },
                status=502,
            )

        return web.Response(
            body=viz_resp.content,
            content_type="text/html",
            charset="utf-8",
        )
    except Exception as e:
        print(f"Cognee visualize error: {e}")
        return web.json_response({"error": str(e)}, status=500)

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


async def cognee_update(request):
    """Updates existing memories by finding and replacing content. Bidirectional MCP."""
    try:
        data = await request.json()
        query = data.get("query")
        old_text = data.get("old_text")
        new_text = data.get("new_text")

        print(f"[Cognee Update] Received update request: query={query}, old_text={old_text}, new_text={new_text}")

        if not query:
            return web.json_response({"error": "query is required to find memories"}, status=400)
        if not old_text or not new_text:
            return web.json_response({"error": "old_text and new_text are required"}, status=400)

        headers = get_cognee_headers()
        
        # First, recall existing memories matching the query
        print(f"[Cognee Update] Recalling memories with query: {query}")
        recall_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/recall",
            json={
                "query": query,
                "searchType": "CHUNKS",
                "datasets": [PERSISTENT_DATASET]
            },
            headers=headers,
            timeout=30
        )

        print(f"[Cognee Update] Recall response status: {recall_resp.status_code}")
        
        if recall_resp.status_code == 404:
            return web.json_response({
                "status": "no_memories_found",
                "message": f"No memories found matching query: {query}"
            })

        if recall_resp.status_code != 200:
            return web.json_response({
                "error": f"Failed to recall memories: {recall_resp.status_code}",
                "details": recall_resp.text
            }, status=500)

        recalled = recall_resp.json()
        print(f"[Cognee Update] Recall response type: {type(recalled)}")
        
        # Check if we found any memories - handle different response formats
        results = []
        if isinstance(recalled, list):
            results = recalled
        elif isinstance(recalled, dict):
            if "result" in recalled:
                results = recalled["result"]
            elif "results" in recalled:
                results = recalled["results"]
            elif "chunks" in recalled:
                results = recalled["chunks"]
            elif "data" in recalled:
                results = recalled["data"]
        
        if not results:
            return web.json_response({
                "status": "no_memories_found",
                "message": f"No memories found matching query: {query}"
            })
        
        print(f"[Cognee Update] Found {len(results)} memories to check")
        
        # For each matching memory, check if old_text exists and replace it
        updated_count = 0
        for memory in results:
            # Extract text from different possible locations
            memory_text = ""
            if isinstance(memory, dict):
                # Try multiple fields where text might be stored
                memory_text = memory.get("text", "")
                if not memory_text and "raw" in memory:
                    raw = memory["raw"]
                    if isinstance(raw, dict):
                        memory_text = raw.get("value", "") or raw.get("text", "")
                if not memory_text and "content" in memory:
                    memory_text = memory["content"]
            else:
                memory_text = str(memory)
            
            print(f"[Cognee Update] Checking memory text (first 200 chars): {memory_text[:200]}")
            
            # Case-insensitive search as fallback
            if old_text in memory_text:
                # Replace old_text with new_text
                updated_text = memory_text.replace(old_text, new_text)
                
                # Store the updated memory
                store_in_background([updated_text])
                updated_count += 1
                print(f"[Cognee Update] Updated memory: {memory_text[:100]}... -> {updated_text[:100]}...")
            elif old_text.lower() in memory_text.lower():
                # Case-insensitive replacement
                import re
                updated_text = re.sub(re.escape(old_text), new_text, memory_text, flags=re.IGNORECASE)
                store_in_background([updated_text])
                updated_count += 1
                print(f"[Cognee Update] Updated memory (case-insensitive): {memory_text[:100]}... -> {updated_text[:100]}...")
        
        return web.json_response({
            "status": "updated",
            "updated_count": updated_count,
            "query": query,
            "old_text": old_text,
            "new_text": new_text
        })

        # Handle different response formats
        results = []
        if isinstance(recalled, dict):
            if "result" in recalled:
                results = recalled["result"]
            elif "results" in recalled:
                results = recalled["results"]
            elif "chunks" in recalled:
                results = recalled["chunks"]
            elif "data" in recalled:
                results = recalled["data"]
        elif isinstance(recalled, list):
            results = recalled

        print(f"[Cognee Update] Found {len(results)} results")

        # For each matching memory, create an updated version
        updated_count = 0
        for result in results:
            # Handle different result formats
            chunk_text = ""
            if isinstance(result, dict):
                chunk_text = result.get("text", "") or result.get("content", "") or result.get("chunk", "")
            elif isinstance(result, str):
                chunk_text = result
            
            print(f"[Cognee Update] Processing chunk: {chunk_text[:100]}...")
            
            # Check if old_text is in this chunk
            if old_text in chunk_text:
                # Replace old_text with new_text
                updated_chunk = chunk_text.replace(old_text, new_text)
                
                # Store the updated chunk
                store_in_background([updated_chunk])
                updated_count += 1
                print(f"[Cognee Update] Updated chunk: {updated_chunk[:100]}...")
            else:
                print(f"[Cognee Update] old_text not found in chunk")

        return web.json_response({
            "status": "updated",
            "updated_count": updated_count,
            "query": query,
            "old_text": old_text,
            "new_text": new_text,
            "dataset": PERSISTENT_DATASET
        })

    except Exception as e:
        print(f"Cognee update error: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def cognee_delete(request):
    """Deletes specific memories by query. More granular than forget (which deletes all)."""
    try:
        data = await request.json()
        query = data.get("query")
        exact_match = data.get("exact_match", False)

        if not query:
            return web.json_response({"error": "query is required"}, status=400)

        headers = get_cognee_headers()
        
        # Recall memories matching the query
        recall_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/recall",
            json={
                "query": query,
                "searchType": "CHUNKS",
                "datasets": [PERSISTENT_DATASET]
            },
            headers=headers,
            timeout=30
        )

        if recall_resp.status_code != 200:
            return web.json_response({
                "error": f"Failed to recall memories: {recall_resp.status_code}",
                "details": recall_resp.text
            }, status=500)

        recalled = recall_resp.json()
        
        # Handle different response formats
        results = []
        if isinstance(recalled, dict):
            if "result" in recalled:
                results = recalled["result"]
            elif "results" in recalled:
                results = recalled["results"]
            elif "chunks" in recalled:
                results = recalled["chunks"]
            elif "data" in recalled:
                results = recalled["data"]
        elif isinstance(recalled, list):
            results = recalled
        
        if not results:
            return web.json_response({
                "status": "no_memories_found",
                "message": f"No memories found matching query: {query}"
            })

        # For each matching memory, we can't directly delete individual chunks in Cognee
        # Instead, we'll mark them as deleted by storing a deletion marker
        # This is a workaround until Cognee provides chunk-level delete API
        deleted_count = 0
        for result in results:
            chunk_text = result.get("text", "")
            
            # Check if we should delete this chunk
            should_delete = False
            if exact_match:
                should_delete = (chunk_text == query)
            else:
                should_delete = (query.lower() in chunk_text.lower())
            
            if should_delete:
                # Store a deletion marker (Cognee doesn't support direct chunk deletion)
                deletion_marker = f"[DELETED] {chunk_text[:50]}... (marked for deletion)"
                store_in_background([deletion_marker])
                deleted_count += 1
                print(f"[Cognee Delete] Marked for deletion: {chunk_text[:100]}...")

        return web.json_response({
            "status": "marked_for_deletion",
            "deleted_count": deleted_count,
            "query": query,
            "exact_match": exact_match,
            "dataset": PERSISTENT_DATASET,
            "note": "Individual chunk deletion not supported by Cognee API. Marked for deletion instead."
        })

    except Exception as e:
        print(f"Cognee delete error: {e}")
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
        # Accept both tool_name and tool_slug for compatibility
        tool_name = data.get("tool_name") or data.get("tool_slug", "")
        arguments = data.get("arguments", {})

        if not tool_name:
            return web.json_response({"error": "tool_name or tool_slug is required"}, status=400)

        # Convert to lowercase for internal mapping
        tool_name = tool_name.lower()
        
        # Route to appropriate helper function
        if tool_name == "slack_send_message":
            channel = arguments.get("channel", "")
            text = arguments.get("text", "") or arguments.get("markdown_text", "")
            result = await slack_send_message(channel, text)
        elif tool_name == "slack_list_channels":
            result = await slack_list_channels()
        elif tool_name == "gmail_fetch_emails":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)
            result = await gmail_fetch_emails(query, max_results)
        elif tool_name == "gmail_send_email":
            to = arguments.get("to", "")
            subject = arguments.get("subject", "")
            body = arguments.get("body", "")
            result = await gmail_send_email(to, subject, body)
        elif tool_name == "calendar_get_events":
            time_min = arguments.get("start_datetime")
            time_max = arguments.get("end_datetime")
            max_results = arguments.get("max_results", 10)
            result = await calendar_get_events(time_min, time_max, max_results)
        elif tool_name == "calendar_create_event":
            summary = arguments.get("title", "") or arguments.get("summary", "")
            start_datetime = arguments.get("start_datetime", "")
            timezone = arguments.get("timezone", "Asia/Kolkata")
            end_datetime = arguments.get("end_datetime")
            event_duration_hour = arguments.get("event_duration_hour", 1)
            event_duration_minutes = arguments.get("event_duration_minutes", 0)
            description = arguments.get("description")
            result = await calendar_create_event(summary, start_datetime, timezone, end_datetime, event_duration_hour, event_duration_minutes, description)
        elif tool_name == "calendar_delete_event":
            event_id = arguments.get("event_id", "")
            calendar_id = arguments.get("calendar_id", "primary")
            result = await calendar_delete_event(event_id, calendar_id)
        elif tool_name == "gdrive_find_file":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)
            result = await gdrive_find_file(query, max_results)
        elif tool_name == "gdrive_get_file_metadata":
            file_id = arguments.get("file_id", "")
            result = await gdrive_get_file_metadata(file_id)
        elif tool_name == "gdrive_download_file":
            file_id = arguments.get("file_id", "")
            mime_type = arguments.get("mime_type")
            result = await gdrive_download_file(file_id, mime_type)
        elif tool_name == "gdrive_create_file_from_text":
            file_name = arguments.get("file_name", "") or arguments.get("name", "")
            text_content = arguments.get("text_content", "") or arguments.get("content", "")
            mime_type = arguments.get("mime_type", "text/plain")
            parent_id = arguments.get("parent_id")
            result = await gdrive_create_file_from_text(file_name, text_content, mime_type, parent_id)
        elif tool_name == "gdrive_create_folder":
            name = arguments.get("name", "")
            parent_id = arguments.get("parent_id")
            result = await gdrive_create_folder(name, parent_id)
        elif tool_name == "gdrive_get_about":
            result = await gdrive_get_about()
        elif tool_name == "gdrive_fetch_to_canvas":
            file_id = arguments.get("file_id", "")
            if file_id:
                try:
                    await gdrive_set_sharing_public(file_id)
                except Exception as perm_err:
                    print(f"GDrive sharing permission error (non-fatal): {perm_err}")
            meta_json = await gdrive_get_file_metadata(file_id)
            print(f"[gdrive_fetch_to_canvas] Raw metadata response: {str(meta_json)[:500]}")
            try:
                meta_data = json.loads(meta_json) if isinstance(meta_json, str) else meta_json
                print(f"[gdrive_fetch_to_canvas] Parsed meta_data type: {type(meta_data).__name__}")
                
                # Handle nested Composio response structure
                if isinstance(meta_data, dict) and "results" in meta_data:
                    results_list = meta_data["results"]
                    if isinstance(results_list, list) and len(results_list) > 0:
                        resp = results_list[0].get("response", {})
                        if isinstance(resp, dict) and "data" in resp:
                            meta_data = resp["data"]
                            print(f"[gdrive_fetch_to_canvas] Extracted from results[0].response.data: {meta_data}")
                
                result = meta_data
                print(f"[gdrive_fetch_to_canvas] Final result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            except Exception as e:
                print(f"[gdrive_fetch_to_canvas] Error parsing metadata: {e}")
                result = meta_json
        else:
            # Direct call for unknown tools
            result = await composio_client.call_tool(tool_name, arguments)
        
        # Auto-store tool call results in Cognee for later recall
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            # Create a human-readable summary with full content based on tool type
            if tool_name == "slack_send_message":
                channel = arguments.get("channel", "")
                text = arguments.get("text", "") or arguments.get("markdown_text", "")
                # Extract message ID from result if available
                msg_ref = ""
                try:
                    result_data = json.loads(result) if isinstance(result, str) else result
                    if isinstance(result_data, dict) and "results" in result_data:
                        msg_data = result_data["results"][0].get("response", {}).get("data", {})
                        msg_ref = f"\nMessage ID: {msg_data.get('message', {}).get('ts', 'N/A')}"
                except:
                    pass
                memory_text = f"On {date_str} at {timestamp}: Sent Slack message to channel '{channel}'\n\nFull message content:\n{text}{msg_ref}"
            elif tool_name == "gmail_send_email":
                to = arguments.get("to", "")
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")
                memory_text = f"On {date_str} at {timestamp}: Sent email\n\nTo: {to}\nSubject: {subject}\n\nFull email body:\n{body}"
            elif tool_name == "calendar_create_event":
                summary = arguments.get("title", "") or arguments.get("summary", "")
                start = arguments.get("start_datetime", "")
                end = arguments.get("end_datetime", "")
                desc = arguments.get("description", "")
                memory_text = f"On {date_str} at {timestamp}: Created calendar event\n\nEvent: {summary}\nStart: {start}\nEnd: {end}\nDescription: {desc}"
            elif tool_name == "notion_create_page":
                title = arguments.get("title", "")
                content = arguments.get("content", "")
                parent_id = arguments.get("parent_id", "")
                memory_text = f"On {date_str} at {timestamp}: Created Notion page\n\nTitle: {title}\nParent ID: {parent_id}\n\nFull page content:\n{content}"
            else:
                # Generic format for other tools - include full result
                memory_text = f"On {date_str} at {timestamp}: Executed tool '{tool_name}'\n\nArguments:\n{json.dumps(arguments, indent=2)}\n\nFull Result:\n{json.dumps(result, indent=2)}"
            
            store_in_background([memory_text])
            print(f"[Auto-Store] Stored {tool_name} result in Cognee: {memory_text[:100]}...")
        except Exception as store_err:
            print(f"[Auto-Store] Failed to store {tool_name}: {store_err}")
        
        return web.json_response({"result": result})

    except Exception as e:
        print(f"Composio call error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def composio_list_tools_endpoint(request):
    """List available Composio MCP tools."""
    try:
        if not composio_client.session:
            return web.json_response({"error": "Composio MCP client not connected"}, status=500)

        tools = []
        for t in composio_client.tools:
            name = t.get("name") if isinstance(t, dict) else getattr(t, "name", "")
            desc = t.get("description") if isinstance(t, dict) else getattr(t, "description", "")
            schema = None
            raw = t.get("tool") if isinstance(t, dict) else None
            if isinstance(raw, dict):
                func = raw.get("function", raw)
                schema = func.get("parameters")
            tools.append({"name": name, "description": desc, "parameters": schema})
        return web.json_response({"tools": tools})

    except Exception as e:
        print(f"Composio list tools error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def gdrive_upload_endpoint(request):
    """Upload a file to Google Drive via Composio. Multipart form: field 'file'.
    Text-decodable files are uploaded with content via CREATE_FILE_FROM_TEXT.
    Binary files get a Drive entry with name + mimeType via CREATE_FILE."""
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            return web.json_response({"error": "multipart 'file' field is required"}, status=400)

        raw = await field.read(decode=False)
        filename = field.filename or "upload.bin"
        mime_type = field.headers.get("Content-Type", "application/octet-stream")

        # Try text upload first (works for text/*, json, xml, csv, etc.)
        text_content = None
        text_mime_prefixes = ("text/", "application/json", "application/xml", "application/javascript",
                              "application/x-yaml", "application/csv", "image/svg+xml")
        if mime_type.startswith(text_mime_prefixes):
            try:
                text_content = raw.decode("utf-8")
            except UnicodeDecodeError:
                text_content = None

        if text_content is not None:
            result_json = await gdrive_create_file_from_text(filename, text_content, mime_type)
        else:
            result_json = await gdrive_upload_binary(filename, raw, mime_type)

        try:
            data = json.loads(result_json) if isinstance(result_json, str) else result_json
        except Exception:
            data = result_json

        # Extract the inner data object from the multi-execute wrapper
        inner = data
        if isinstance(inner, dict) and "results" in inner:
            results_list = inner["results"]
            if isinstance(results_list, list) and len(results_list) > 0:
                resp = results_list[0].get("response", {})
                if isinstance(resp, dict) and "data" in resp:
                    inner = resp["data"]

        file_id = inner.get("id") if isinstance(inner, dict) else None
        if file_id:
            try:
                await gdrive_set_sharing_public(file_id)
            except Exception as perm_err:
                print(f"GDrive sharing permission error (non-fatal): {perm_err}")

        return web.json_response({"result": inner, "name": filename, "mimeType": mime_type})

    except Exception as e:
        print(f"GDrive upload error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def gdrive_fetch_endpoint(request):
    """Fetch a Drive file's metadata + webViewLink by file_id (POST {file_id})."""
    try:
        data = await request.json()
        file_id = data.get("file_id", "")
        if not file_id:
            return web.json_response({"error": "file_id is required"}, status=400)

        try:
            await gdrive_set_sharing_public(file_id)
        except Exception as perm_err:
            print(f"GDrive sharing permission error (non-fatal): {perm_err}")

        result_json = await gdrive_get_file_metadata(file_id)
        try:
            parsed = json.loads(result_json) if isinstance(result_json, str) else result_json
            if isinstance(parsed, dict) and "results" in parsed:
                results_list = parsed["results"]
                if isinstance(results_list, list) and len(results_list) > 0:
                    resp = results_list[0].get("response", {})
                    if isinstance(resp, dict) and "data" in resp:
                        parsed = resp["data"]
        except Exception:
            parsed = result_json

        return web.json_response({"result": parsed})
    except Exception as e:
        print(f"GDrive fetch error: {e}")
        return web.json_response({"error": str(e)}, status=500)


# In-memory context storage
_context_store = {}

# Server-side canvas state (synced from frontend)
_canvas_files = {}


def _analyze_files_with_gemini(files):
    """Call Gemini HTTP API to analyze files and generate a context name + description."""
    try:
        api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None

        file_descriptions = []
        for f in files:
            name = f.get("name", "unknown")
            mime = f.get("mimeType", "unknown")
            file_descriptions.append(f"- {name} (type: {mime})")

        prompt = f"""Analyze these files and create a short, meaningful context name (2-5 words) that describes what they have in common. Also provide a one-sentence description.

Files:
{chr(10).join(file_descriptions)}

Respond in this exact JSON format:
{{"context_name": "short name", "description": "one sentence description"}}"""

        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200}
            },
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            timeout=15,
        )

        if resp.status_code != 200:
            print(f"Gemini analysis failed: {resp.status_code}")
            return None

        result = resp.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        import re
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"Gemini analysis error: {e}")
    return None


def _extract_file_content(file_info):
    """Extract actual content from a file - text for text files, description for images."""
    try:
        file_id = file_info.get("drive_file_id") or file_info.get("fileId")
        file_name = file_info.get("name", "unknown")
        mime_type = file_info.get("mime_type") or file_info.get("mimeType", "unknown")
        
        if not file_id:
            return f"File: {file_name} (no Drive ID available)"
        
        # Handle Google Docs/Sheets/Slides by exporting them
        export_mime_type = None
        if mime_type == "application/vnd.google-apps.document":
            export_mime_type = "text/plain"
            print(f"[Content Extract] Exporting Google Doc '{file_name}' as text...")
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            export_mime_type = "text/csv"
            print(f"[Content Extract] Exporting Google Sheet '{file_name}' as CSV...")
        elif mime_type == "application/vnd.google-apps.presentation":
            export_mime_type = "text/plain"
            print(f"[Content Extract] Exporting Google Slides '{file_name}' as text...")
        
        # Download file from Google Drive
        composio_args = {
            "tool_slug": "gdrive_download_file",
            "arguments": {"file_id": file_id},
        }
        
        # Add mime_type for export if needed
        if export_mime_type:
            composio_args["arguments"]["mime_type"] = export_mime_type
        
        print(f"[Content Extract] Downloading {file_name} (id={file_id}) from Drive...")
        download_resp = requests.post(
            f"http://localhost:8000/api/composio/call",
            json=composio_args,
            timeout=30,
        )
        
        if download_resp.status_code != 200:
            print(f"[Content Extract] Download failed: {download_resp.status_code} - {download_resp.text[:200]}")
            return f"File: {file_name} (download failed)"
        
        download_data = download_resp.json()
        result = download_data.get("result", "")
        
        print(f"[Content Extract] Raw result type: {type(result).__name__}")
        print(f"[Content Extract] Raw result preview: {str(result)[:300]}")
        
        # Parse the result - it might be JSON string or dict
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                pass
        
        # Extract content from various possible response formats
        file_content = None
        actual_mime_type = mime_type
        
        if isinstance(result, dict):
            # Check for base64 content
            file_content = result.get("content") or result.get("data") or result.get("base64_content")
            # Check for results array (Composio format)
            if not file_content and "results" in result:
                results_list = result["results"]
                if results_list and isinstance(results_list, list):
                    first_result = results_list[0]
                    if isinstance(first_result, dict):
                        resp_data = first_result.get("response", {})
                        if isinstance(resp_data, dict):
                            # Navigate through data field
                            data_field = resp_data.get("data")
                            if data_field and isinstance(data_field, dict):
                                # Check for downloaded_file_content (Composio Drive download format)
                                downloaded_content = data_field.get("downloaded_file_content")
                                if downloaded_content and isinstance(downloaded_content, dict):
                                    # Get actual mime type from response
                                    actual_mime_type = downloaded_content.get("mimetype", mime_type)
                                    # Try to get content field first
                                    file_content = downloaded_content.get("content") or downloaded_content.get("data")
                                    # If not found, try to fetch from s3url
                                    if not file_content and downloaded_content.get("s3url"):
                                        print(f"[Content Extract] Fetching content from s3url...")
                                        try:
                                            s3_resp = requests.get(downloaded_content["s3url"], timeout=30)
                                            if s3_resp.status_code == 200:
                                                # Check if it's binary content
                                                content_type = s3_resp.headers.get('content-type', '')
                                                if 'text' in content_type or 'json' in content_type or export_mime_type:
                                                    file_content = s3_resp.text
                                                    print(f"[Content Extract] Successfully fetched {len(file_content)} chars from s3url (text)")
                                                else:
                                                    # Binary content - encode as base64
                                                    import base64
                                                    file_content = base64.b64encode(s3_resp.content).decode('utf-8')
                                                    print(f"[Content Extract] Successfully fetched {len(file_content)} chars from s3url (binary/base64)")
                                        except Exception as e:
                                            print(f"[Content Extract] Failed to fetch from s3url: {e}")
                            else:
                                # Fallback: check if downloaded_file_content is directly in response
                                downloaded_content = resp_data.get("downloaded_file_content")
                                if downloaded_content and isinstance(downloaded_content, dict):
                                    actual_mime_type = downloaded_content.get("mimetype", mime_type)
                                    file_content = downloaded_content.get("content") or downloaded_content.get("data")
        
        if not file_content:
            print(f"[Content Extract] No content found in response: {str(result)[:200]}")
            return f"File: {file_name} (no content in response)"
        
        # Use actual_mime_type for content type detection
        effective_mime_type = actual_mime_type
        
        # If we exported a Google Doc/Sheet/Slide, use the export mime type
        if export_mime_type:
            effective_mime_type = export_mime_type
            print(f"[Content Extract] Using export mime type: {effective_mime_type}")
        
        # Handle text files
        if effective_mime_type.startswith("text/") or file_name.endswith((".txt", ".md", ".json", ".csv")) or export_mime_type:
            # Decode base64 if needed
            if isinstance(file_content, str):
                # Check if it looks like base64
                try:
                    import base64
                    # Try to decode
                    decoded = base64.b64decode(file_content).decode('utf-8', errors='replace')
                    # If decoded successfully and looks like text, use it
                    if decoded.isprintable() or '\n' in decoded:
                        file_content = decoded
                except:
                    # Not base64, use as-is
                    pass
            elif isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8', errors='replace')
            else:
                file_content = str(file_content)
            
            print(f"[Content Extract] Text file content (first 100 chars): {file_content[:100]}...")
            cleaned_content = clean_extracted_text(file_content)
            return f"File '{file_name}' content:\n{cleaned_content}"
        
        # Handle images - send to Gemini for description
        elif effective_mime_type.startswith("image/"):
            print(f"[Content Extract] Analyzing image {file_name} with Gemini...")
            print(f"[Content Extract] Image content type: {type(file_content).__name__}, length: {len(str(file_content))}")
            
            api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                return f"Image file: {file_name} (no API key for analysis)"
            
            # Ensure content is base64 string
            img_b64 = file_content
            if isinstance(file_content, bytes):
                import base64
                img_b64 = base64.b64encode(file_content).decode('utf-8')
            elif isinstance(file_content, str):
                # Check if it's already base64 or needs encoding
                try:
                    import base64
                    # Try to decode to see if it's base64
                    decoded = base64.b64decode(file_content)
                    # If successful, re-encode to ensure clean format
                    img_b64 = base64.b64encode(decoded).decode('utf-8')
                except:
                    # Not base64, might be raw binary string - encode it
                    img_b64 = base64.b64encode(file_content.encode('latin-1')).decode('utf-8')
            else:
                img_b64 = str(file_content)
            
            print(f"[Content Extract] Sending image to Gemini (base64 length: {len(img_b64)})")
            
            # Call Gemini vision API
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                json={
                    "contents": [{
                        "parts": [
                            {"text": "Describe this image in detail. What objects, people, text, or scenes are visible?"},
                            {"inline_data": {"mime_type": effective_mime_type, "data": img_b64}}
                        ]
                    }],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300}
                },
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                timeout=15,
            )
            
            if resp.status_code == 200:
                result = resp.json()
                description = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                cleaned_description = clean_extracted_text(description)
                print(f"[Content Extract] Image description: {cleaned_description[:100]}...")
                return f"Image '{file_name}' description:\n{cleaned_description}"
            else:
                print(f"[Content Extract] Gemini vision failed: {resp.status_code} - {resp.text[:300]}")
                return f"Image file: {file_name} (analysis failed)"
        
        # Handle PDF files - extract text using PyPDF2
        elif effective_mime_type == "application/pdf" or file_name.endswith(".pdf"):
            print(f"[Content Extract] Extracting text from PDF '{file_name}'...")
            try:
                from PyPDF2 import PdfReader
                import io
                
                # Get binary content
                if isinstance(file_content, bytes):
                    pdf_bytes = file_content
                elif isinstance(file_content, str):
                    import base64
                    try:
                        pdf_bytes = base64.b64decode(file_content)
                    except:
                        pdf_bytes = file_content.encode('latin-1')
                else:
                    return f"File: {file_name} (cannot process PDF content)"
                
                # Extract text from PDF
                reader = PdfReader(io.BytesIO(pdf_bytes))
                text_parts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                
                extracted_text = "\n\n".join(text_parts)
                cleaned_text = clean_extracted_text(extracted_text)
                print(f"[Content Extract] PDF text extracted ({len(cleaned_text)} chars)")
                return f"File '{file_name}' content:\n{cleaned_text}"
            except Exception as e:
                print(f"[Content Extract] PDF extraction failed: {e}")
                return f"File: {file_name} (PDF extraction failed: {str(e)[:50]})"
        
        # Handle DOCX files - extract text using python-docx
        elif effective_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_name.endswith(".docx"):
            print(f"[Content Extract] Extracting text from DOCX '{file_name}'...")
            try:
                from docx import Document
                import io
                
                # Get binary content
                if isinstance(file_content, bytes):
                    docx_bytes = file_content
                elif isinstance(file_content, str):
                    import base64
                    try:
                        docx_bytes = base64.b64decode(file_content)
                    except:
                        docx_bytes = file_content.encode('latin-1')
                else:
                    return f"File: {file_name} (cannot process DOCX content)"
                
                # Extract text from DOCX
                doc = Document(io.BytesIO(docx_bytes))
                text_parts = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)
                
                extracted_text = "\n\n".join(text_parts)
                cleaned_text = clean_extracted_text(extracted_text)
                print(f"[Content Extract] DOCX text extracted ({len(cleaned_text)} chars)")
                return f"File '{file_name}' content:\n{cleaned_text}"
            except Exception as e:
                print(f"[Content Extract] DOCX extraction failed: {e}")
                return f"File: {file_name} (DOCX extraction failed: {str(e)[:50]})"
        
        else:
            return f"File: {file_name} (unsupported type: {effective_mime_type})"
            
    except Exception as e:
        print(f"[Content Extract] Error: {e}")
        return f"File: {file_info.get('name', 'unknown')} (extraction error: {str(e)[:50]})"


def _store_context_in_cognee(context_id, context_name, description, files):
    """Persist context to Cognee knowledge graph with actual file content."""
    try:
        from datetime import datetime
        
        created_at = datetime.now().isoformat()
        
        # Extract actual content from each file
        file_contents = []
        for f in files:
            content = _extract_file_content(f)
            file_contents.append(content)
        
        # Build comprehensive text with context + file contents
        all_content = "\n\n".join(file_contents)
        text = f"""Context group '{context_name}'
Description: {description}
Created: {created_at}
Context ID: {context_id}

File contents:
{all_content}
"""
        
        # Clean the final text before storing
        text = clean_extracted_text(text)
        
        headers = get_cognee_headers()
        
        print(f"[Cognee] Storing context '{context_name}' with {len(files)} files")
        print(f"[Cognee] Total text length: {len(text)} chars")
        print(f"[Cognee] Text preview: {text[:500]}...")
        
        add_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/add_text",
            json={"textData": [text], "datasetName": PERSISTENT_DATASET},
            headers=headers,
            timeout=30,
        )
        print(f"[Cognee] add_text response: {add_resp.status_code} - {add_resp.text[:200]}")
        
        if add_resp.status_code not in [200, 201]:
            print(f"[Cognee] add_text failed: {add_resp.status_code}")
            return
        
        cognify_resp = requests.post(
            f"{COGNEE_BASE_URL}/api/v1/cognify",
            json={"datasets": [PERSISTENT_DATASET]},
            headers=headers,
            timeout=90,
        )
        print(f"[Cognee] cognify response: {cognify_resp.status_code} - {cognify_resp.text[:200]}")
        
        if cognify_resp.status_code not in [200, 201]:
            print(f"[Cognee] cognify failed: {cognify_resp.status_code}")
            return
            
        print(f"[Cognee] Context '{context_name}' successfully stored with content")
    except Exception as e:
        print(f"[Cognee] Context store failed: {e}")


async def context_create_endpoint(request):
    """Create a context group from selected files. Analyzes with Gemini, persists to Cognee."""
    try:
        data = await request.json()
        files = data.get("files", [])

        if not files:
            return web.json_response({"error": "files array is required"}, status=400)

        analysis = _analyze_files_with_gemini(files)

        if analysis:
            context_name = analysis.get("context_name", f"Context {len(_context_store) + 1}")
            description = analysis.get("description", "")
        else:
            file_names = [f.get("name", "unknown") for f in files]
            context_name = " & ".join(file_names)
            if len(context_name) > 40:
                context_name = context_name[:37] + "..."
            description = f"Group of {len(files)} files"

        context_id = f"ctx-{len(_context_store) + 1}-{int(time.time())}"
        _context_store[context_id] = {
            "id": context_id,
            "name": context_name,
            "description": description,
            "files": files,
            "created_at": time.time(),
        }

        t = threading.Thread(
            target=_store_context_in_cognee,
            args=(context_id, context_name, description, files),
            daemon=True,
        )
        t.start()

        return web.json_response({
            "context_id": context_id,
            "context_name": context_name,
            "description": description,
            "file_count": len(files),
        })
    except Exception as e:
        print(f"Context create error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def context_rename_endpoint(request):
    """Rename an existing context group."""
    try:
        data = await request.json()
        context_id = data.get("context_id", "")
        new_name = data.get("name", "")

        if not context_id or not new_name:
            return web.json_response({"error": "context_id and name are required"}, status=400)

        if context_id not in _context_store:
            return web.json_response({"error": "context not found"}, status=404)

        old_name = _context_store[context_id]["name"]
        _context_store[context_id]["name"] = new_name

        return web.json_response({
            "context_id": context_id,
            "old_name": old_name,
            "new_name": new_name,
        })
    except Exception as e:
        print(f"Context rename error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def context_list_endpoint(request):
    """List all context groups."""
    try:
        contexts = list(_context_store.values())
        return web.json_response({"contexts": contexts})
    except Exception as e:
        print(f"Context list error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def canvas_sync_endpoint(request):
    """Sync canvas file state from frontend."""
    try:
        data = await request.json()
        files = data.get("files", [])
        global _canvas_files
        _canvas_files = {f["id"]: f for f in files}
        print(f"[Canvas Sync] Received {len(files)} files: {[f.get('fileName') for f in files]}")
        return web.json_response({"status": "synced", "count": len(_canvas_files)})
    except Exception as e:
        print(f"Canvas sync error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def canvas_add_text_file_endpoint(request):
    """Add a text file to the canvas with retrieved content."""
    try:
        data = await request.json()
        content = data.get("content", "")
        title = data.get("title", "Retrieved Content")
        
        if not content:
            return web.json_response({"error": "content is required"}, status=400)
        
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{title.replace(' ', '_')}_{timestamp}.txt"
        
        # Upload to Google Drive
        composio_args = {
            "tool_slug": "gdrive_create_file_from_text",
            "arguments": {
                "file_name": filename,
                "text_content": content,
                "mime_type": "text/plain"
            }
        }
        
        result = await composio_client.call_tool(**composio_args)
        
        # Extract file metadata
        file_data = json.loads(result) if isinstance(result, str) else result
        file_id = None
        file_url = None
        
        if isinstance(file_data, dict):
            if "results" in file_data:
                results = file_data["results"]
                if results and len(results) > 0:
                    resp_data = results[0].get("response", {}).get("data", {})
                    file_id = resp_data.get("id")
                    file_url = resp_data.get("webViewLink") or resp_data.get("display_url")
        
        # Return canvas item data
        canvas_item = {
            "id": f"canvas-{timestamp}",
            "type": "text-file",
            "fileName": filename,
            "fileId": file_id,
            "webViewLink": file_url,
            "content": content,
            "source": "retrieval"
        }
        
        return web.json_response({"canvas_item": canvas_item})
        
    except Exception as e:
        print(f"Canvas add text file error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def canvas_list_files_endpoint(request):
    """Agent tool: list all files currently on canvas."""
    try:
        files = list(_canvas_files.values())
        print(f"[Canvas List] Returning {len(files)} files")
        return web.json_response({
            "files": [
                {
                    "canvas_id": f.get("id"),
                    "name": f.get("fileName", "unknown"),
                    "drive_file_id": f.get("fileId"),
                    "mime_type": f.get("mimeType"),
                }
                for f in files
            ]
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def canvas_group_files_endpoint(request):
    """Agent tool: group specific files into a context by file IDs."""
    try:
        data = await request.json()
        print(f"[Canvas Group] Received request: {data}")
        file_ids = data.get("file_ids", [])
        context_name = data.get("context_name", "")
        
        print(f"[Canvas Group] Looking for file_ids: {file_ids}")
        print(f"[Canvas Group] Available files in _canvas_files: {list(_canvas_files.keys())}")

        if not file_ids or len(file_ids) < 2:
            return web.json_response({"error": "file_ids array with at least 2 items required"}, status=400)

        files = []
        for fid in file_ids:
            if fid in _canvas_files:
                f = _canvas_files[fid]
                files.append({
                    "id": f.get("id"),
                    "name": f.get("fileName", "unknown"),
                    "fileId": f.get("fileId"),
                    "drive_file_id": f.get("fileId"),
                    "mime_type": f.get("mimeType"),
                    "mimeType": f.get("mimeType"),
                })

        if len(files) < 2:
            return web.json_response({"error": "Not enough valid files found on canvas"}, status=400)

        if not context_name:
            analysis = _analyze_files_with_gemini(files)
            if analysis:
                context_name = analysis.get("context_name", f"Context {len(_context_store) + 1}")
                description = analysis.get("description", "")
            else:
                context_name = f"Context {len(_context_store) + 1}"
                description = f"Group of {len(files)} files"
        else:
            description = f"Group of {len(files)} files: {', '.join(f.get('name', '') for f in files)}"

        context_id = f"ctx-{len(_context_store) + 1}-{int(time.time())}"
        _context_store[context_id] = {
            "id": context_id,
            "name": context_name,
            "description": description,
            "files": files,
            "created_at": time.time(),
        }

        t = threading.Thread(
            target=_store_context_in_cognee,
            args=(context_id, context_name, description, files),
            daemon=True,
        )
        t.start()

        return web.json_response({
            "context_id": context_id,
            "context_name": context_name,
            "description": description,
            "file_count": len(files),
            "file_ids": file_ids,
        })
    except Exception as e:
        print(f"Canvas group files error: {e}")
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
    # CORS middleware
    @web.middleware
    async def cors_middleware(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

    app = web.Application(middlewares=[cors_middleware])

    # Handle OPTIONS preflight
    async def options_handler(request):
        return web.Response(status=200)

    app.router.add_route('OPTIONS', '/{path:.*}', options_handler)
    
    # API endpoints
    app.router.add_post("/api/token", get_ephemeral_token)
    app.router.add_post("/api/cognee/remember", cognee_remember)
    app.router.add_post("/api/cognee/remember_batch", cognee_remember_batch)
    app.router.add_post("/api/cognee/cognify", cognee_cognify)
    app.router.add_post("/api/cognee/recall", cognee_recall)
    app.router.add_post("/api/cognee/forget", cognee_forget)
    app.router.add_post("/api/cognee/update", cognee_update)
    app.router.add_post("/api/cognee/delete", cognee_delete)
    app.router.add_get("/api/cognee/visualize", cognee_visualize)

    # Notion MCP endpoints
    app.router.add_post("/api/notion/search", notion_search_endpoint)
    app.router.add_post("/api/notion/create_page", notion_create_page_endpoint)
    app.router.add_post("/api/notion/append", notion_append_endpoint)
    app.router.add_post("/api/notion/get_page", notion_get_page_endpoint)
    app.router.add_get("/api/notion/tools", notion_list_tools_endpoint)

    # Composio MCP endpoints (Slack, Gmail, Google Calendar, Google Drive)
    app.router.add_post("/api/composio/call", composio_call_endpoint)
    app.router.add_get("/api/composio/tools", composio_list_tools_endpoint)

    # Google Drive endpoints
    app.router.add_post("/api/gdrive/upload", gdrive_upload_endpoint)
    app.router.add_post("/api/gdrive/fetch", gdrive_fetch_endpoint)

    # Context group endpoints
    app.router.add_post("/api/context/create", context_create_endpoint)
    app.router.add_post("/api/context/rename", context_rename_endpoint)
    app.router.add_get("/api/context/list", context_list_endpoint)

    # Canvas agent tool endpoints
    app.router.add_post("/api/canvas/sync", canvas_sync_endpoint)
    app.router.add_post("/api/canvas/add-text-file", canvas_add_text_file_endpoint)
    app.router.add_get("/api/canvas/files", canvas_list_files_endpoint)
    app.router.add_post("/api/canvas/group", canvas_group_files_endpoint)

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
