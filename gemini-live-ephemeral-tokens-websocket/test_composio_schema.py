#!/usr/bin/env python3
"""Check COMPOSIO_MULTI_EXECUTE_TOOL schema."""
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

    print("Getting schema for COMPOSIO_MULTI_EXECUTE_TOOL...")
    try:
        result = await composio_client.call_tool("COMPOSIO_GET_TOOL_SCHEMAS", {
            "tool_names": ["COMPOSIO_MULTI_EXECUTE_TOOL"]
        })
        print(f"Result:\n{json.dumps(json.loads(result), indent=2)}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

    await composio_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
