#!/usr/bin/env python3
"""Inspect COMPOSIO_MULTI_EXECUTE_TOOL raw definition."""
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from composio import Composio


async def main():
    client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
    session = client.create(user_id="default-user")
    
    all_tools = session.tools()
    for t in all_tools:
        func = t.get('function', t)
        name = func.get('name', 'unknown')
        if name == "COMPOSIO_MULTI_EXECUTE_TOOL":
            print(f"Full definition for {name}:")
            print(json.dumps(t, indent=2))
            break
    
    # Also try searching for slack tools to see the recommended flow
    print("\n\nSearching for 'list slack channels'...")
    result = session.execute(tool_slug="COMPOSIO_SEARCH_TOOLS", arguments={"query": "list slack channels"})
    print(f"Search result:\n{json.dumps(result.data, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
