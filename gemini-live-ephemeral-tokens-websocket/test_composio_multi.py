#!/usr/bin/env python3
"""Test COMPOSIO_MULTI_EXECUTE_TOOL for toolkit tools."""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from composio_mcp_client import composio_client


async def main():
    print("Connecting to Composio...")
    await composio_client.connect()
    print("✅ Connected!\n")

    print("Testing SLACK_LIST_ALL_CHANNELS via COMPOSIO_MULTI_EXECUTE_TOOL...")
    try:
        result = await composio_client.call_tool("SLACK_LIST_ALL_CHANNELS", {"limit": 5})
        print(f"Result: {result[:500]}...")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

    await composio_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
