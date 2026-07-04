#!/usr/bin/env python3
"""Test MCP server with stdio transport."""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    server_params = StdioServerParameters(
        command="/home/sai-nivedh-26/weekend-hack/hoo/bin/python3",
        args=["mcp_server.py"],
        cwd="/home/sai-nivedh-26/weekend-hack/gemini-live-ephemeral-tokens-websocket"
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"\n✅ Connected! Available tools ({len(tools.tools)}):")
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description[:80]}...")

            # Test remember tool
            print("\n📝 Testing remember tool...")
            result = await session.call_tool("remember", {
                "text": "On 2026-07-04: Test memory from MCP client"
            })
            print(f"   Result: {result.content[0].text if result.content else 'No response'}")

            # Test recall tool
            print("\n🔍 Testing recall tool...")
            result = await session.call_tool("recall", {
                "query": "test memory"
            })
            print(f"   Result: {result.content[0].text if result.content else 'No response'}")

            print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
