#!/usr/bin/env python3
"""Test calendar event creation with correct schema."""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from composio_mcp_client import calendar_create_event


async def main():
    print("Testing calendar event creation...")
    
    # Test with IST timezone (Asia/Kolkata)
    result = await calendar_create_event(
        summary="Test Event - Gemini Integration",
        start_datetime="2025-01-08T22:30:00",
        timezone="Asia/Kolkata",
        event_duration_hour=1,
        event_duration_minutes=0,
        description="Test event created via Composio MCP integration"
    )
    
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
