#!/usr/bin/env python3
"""Test script to list available Notion MCP tools."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from notion_mcp_client import notion_client


async def main():
    print("Connecting to Notion MCP server...")
    await notion_client.connect()

    print(f"\n✅ Connected! Available tools ({len(notion_client.tools)}):\n")
    for tool in notion_client.tools:
        print(f"  • {tool.name}")
        print(f"    {tool.description[:100]}..." if len(tool.description) > 100 else f"    {tool.description}")
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            props = tool.inputSchema.get('properties', {})
            if props:
                print(f"    Params: {', '.join(props.keys())}")
        print()

    await notion_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
