import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class NotionMCPClient:
    def __init__(self):
        self.notion_token = os.environ.get("NOTION_ACCESS_TOKEN", "")
        self.session = None
        self._client_ctx = None
        self._session_ctx = None
        self.tools = []

    async def connect(self):
        if not self.notion_token:
            raise ValueError("NOTION_ACCESS_TOKEN not set in environment")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={
                "NOTION_TOKEN": self.notion_token,
                "PATH": os.environ.get("PATH", "")
            }
        )

        self._client_ctx = stdio_client(server_params)
        read_stream, write_stream = await self._client_ctx.__aenter__()

        self._session_ctx = ClientSession(read_stream, write_stream)
        self.session = await self._session_ctx.__aenter__()

        await self.session.initialize()

        result = await self.session.list_tools()
        self.tools = result.tools
        print(f"[Notion MCP] Connected. Available tools: {[t.name for t in self.tools]}")

    async def call_tool(self, tool_name: str, arguments: dict):
        if not self.session:
            raise RuntimeError("Notion MCP client not connected")

        result = await self.session.call_tool(tool_name, arguments)

        response_text = ""
        for content in result.content:
            if hasattr(content, 'text'):
                response_text += content.text
            else:
                response_text += str(content)

        return response_text

    async def disconnect(self):
        if self._session_ctx:
            try:
                await self._session_ctx.__aexit__(None, None, None)
            except Exception:
                pass
        if self._client_ctx:
            try:
                await self._client_ctx.__aexit__(None, None, None)
            except Exception:
                pass
        self.session = None
        print("[Notion MCP] Disconnected")


notion_client = NotionMCPClient()


async def init_notion():
    try:
        await notion_client.connect()
        return True
    except Exception as e:
        print(f"[Notion MCP] Failed to connect: {e}")
        return False


async def notion_search(query: str):
    result = await notion_client.call_tool("API-post-search", {"query": query})
    return result


async def notion_create_page(title: str, content: str, parent_id: str = None):
    if not parent_id:
        search_result = await notion_search("")
        import json
        results = json.loads(search_result).get("results", [])
        if results:
            parent_id = results[0]["id"]
        else:
            return "Error: No parent page found. Please provide a parent_id or create a page in Notion first."

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

    result = await notion_client.call_tool("API-post-page", {
        "parent": parent,
        "properties": properties,
        "children": children
    })
    return result


async def notion_append_to_page(page_id: str, content: str):
    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }
    ]

    result = await notion_client.call_tool("API-patch-block-children", {
        "block_id": page_id,
        "children": children
    })
    return result


async def notion_get_page(page_id: str):
    result = await notion_client.call_tool("API-retrieve-page-markdown", {"page_id": page_id})
    return result
