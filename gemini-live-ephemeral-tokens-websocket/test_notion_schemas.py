#!/usr/bin/env python3
"""Test script to show detailed parameter schemas for key Notion MCP tools."""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from notion_mcp_client import notion_client


async def main():
    print("Connecting to Notion MCP server...")
    await notion_client.connect()

    key_tools = [
        "API-post-search",
        "API-post-page",
        "API-patch-block-children",
        "API-retrieve-a-page",
        "API-retrieve-page-markdown",
        "API-update-page-markdown"
    ]

    for tool_name in key_tools:
        tool = next((t for t in notion_client.tools if t.name == tool_name), None)
        if tool:
            print(f"\n{'='*60}")
            print(f"Tool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"\nInput Schema:")
            print(json.dumps(tool.inputSchema, indent=2))

    await notion_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
