#!/usr/bin/env python3
"""Test remote MCP server with HTTP transport and auth."""
import asyncio
import requests
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client


async def test_remote_mcp(transport="sse"):
    base_url = "http://localhost:9000"
    
    print("=== Step 1: Get ephemeral token ===")
    token_resp = requests.post(f"{base_url}/api/token", json={"ttl_minutes": 5})
    token_data = token_resp.json()
    token = token_data["token"]
    mcp_url = token_data["mcp_url"]
    print(f"Token: {token[:20]}...")
    print(f"MCP URL: {mcp_url}")
    print(f"Transport: {transport}")
    
    print("\n=== Step 2: Connect to remote MCP server ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    if transport == "sse":
        client_ctx = sse_client(url=mcp_url, headers=headers)
    else:
        client_ctx = streamablehttp_client(url=mcp_url, headers=headers)
    
    async with client_ctx as streams:
        if transport == "sse":
            read, write = streams
        else:
            read, write, _ = streams  # streamable HTTP returns 3 values
        
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("\n=== Step 3: List available tools ===")
            tools = await session.list_tools()
            print(f"Connected! {len(tools.tools)} tools available:")
            for tool in tools.tools[:5]:
                print(f"  • {tool.name}")
            if len(tools.tools) > 5:
                print(f"  ... and {len(tools.tools) - 5} more")
            
            print("\n=== Step 4: Test remember tool ===")
            result = await session.call_tool("remember", {
                "text": "On 2026-07-04: Testing remote MCP server with auth!"
            })
            print(f"Result: {result.content[0].text[:100]}...")
            
            print("\n=== Step 5: Test recall tool ===")
            result = await session.call_tool("recall", {
                "query": "remote MCP server"
            })
            print(f"Result: {result.content[0].text[:200]}...")
            
            print("\n✅ Remote MCP server test passed!")


if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "sse"
    asyncio.run(test_remote_mcp(transport))
