#!/usr/bin/env python3
"""Test script to verify Notion MCP integration works."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from notion_mcp_client import notion_client, notion_search, notion_create_page, notion_get_page


async def main():
    print("Connecting to Notion MCP server...")
    await notion_client.connect()
    print("✅ Connected!\n")

    print("1. Testing search...")
    try:
        search_result = await notion_search("test")
        print(f"   Search result: {search_result[:200]}...")
    except Exception as e:
        print(f"   ❌ Search failed: {e}")

    print("\n2. Testing create page...")
    try:
        create_result = await notion_create_page(
            title="Test Page from MCP",
            content="This is a test page created via the Notion MCP integration."
        )
        print(f"   Create result: {create_result[:200]}...")
        
        # Extract page ID from result (if available)
        if "id" in create_result.lower():
            print("   ✅ Page created successfully!")
    except Exception as e:
        print(f"   ❌ Create failed: {e}")

    print("\n3. Testing get page...")
    try:
        # This will fail if we don't have a valid page ID, but let's try
        get_result = await notion_get_page("00000000-0000-0000-0000-000000000000")
        print(f"   Get result: {get_result[:200]}...")
    except Exception as e:
        print(f"   Expected error (invalid page ID): {str(e)[:100]}...")

    await notion_client.disconnect()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
