#!/usr/bin/env python3
"""Test script to verify Composio MCP integration works."""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from composio_mcp_client import composio_client


async def main():
    print("Connecting to Composio MCP server...")
    await composio_client.connect()
    print("✅ Connected!\n")

    print(f"Available meta-tools ({len(composio_client.tools)}):")
    for tool in composio_client.tools:
        print(f"  • {tool['name']}")

    print("\n1. Searching for Slack tools...")
    try:
        result = await composio_client.call_tool("COMPOSIO_SEARCH_TOOLS", {
            "query": "list slack channels"
        })
        print(f"   Result: {result[:500]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n2. Checking Slack connection...")
    try:
        result = await composio_client.call_tool("COMPOSIO_MANAGE_CONNECTIONS", {
            "toolkits": ["slack"]
        })
        print(f"   Result: {result[:500]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n3. Checking Gmail connection...")
    try:
        result = await composio_client.call_tool("COMPOSIO_MANAGE_CONNECTIONS", {
            "toolkits": ["gmail"]
        })
        print(f"   Result: {result[:500]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n4. Checking Google Calendar connection...")
    try:
        result = await composio_client.call_tool("COMPOSIO_MANAGE_CONNECTIONS", {
            "toolkits": ["googlecalendar"]
        })
        print(f"   Result: {result[:500]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    await composio_client.disconnect()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
