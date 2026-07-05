# Bidirectional MCP Tools Documentation

## Overview
Added bidirectional memory management tools to the MCP server, allowing coding agents to update and delete specific memories without clearing the entire knowledge graph.

## New Tools

### 1. `update(query, old_text, new_text)`
Update existing memories by finding and replacing content.

**Parameters:**
- `query` (str): Search query to find memories to update
- `old_text` (str): The text to find and replace in matching memories
- `new_text` (str): The new text to replace old_text with

**Returns:**
```json
{
  "status": "updated",
  "updated_count": 2,
  "query": "water bottle",
  "old_text": "blue water bottle",
  "new_text": "red water bottle",
  "dataset": "gemini_live_memory"
}
```

**Example Usage:**
```python
# Update a fact about the water bottle color
update(
    query="water bottle",
    old_text="blue water bottle",
    new_text="red water bottle"
)
```

### 2. `delete(query, exact_match=False)`
Delete specific memories by query. More granular than `forget()` which deletes all.

**Parameters:**
- `query` (str): Search query to find memories to delete
- `exact_match` (bool): If True, only delete memories that exactly match the query

**Returns:**
```json
{
  "status": "marked_for_deletion",
  "deleted_count": 1,
  "query": "old incorrect fact",
  "exact_match": false,
  "dataset": "gemini_live_memory",
  "note": "Individual chunk deletion not supported by Cognee API. Marked for deletion instead."
}
```

**Example Usage:**
```python
# Delete all memories containing "old fact"
delete(query="old fact", exact_match=False)

# Delete only memories that exactly match the query
delete(query="exact memory text", exact_match=True)
```

## Implementation Details

### Backend (server.py)
- Added `/api/cognee/update` endpoint
- Added `/api/cognee/delete` endpoint
- Both endpoints use Cognee's recall API to find matching memories
- Update creates new memories with replaced text
- Delete marks memories with `[DELETED]` prefix (Cognee limitation)

### Frontend (useGeminiLive.ts)
- Added `cognee_update` tool mapping
- Added `cognee_delete` tool mapping
- Both tools enabled by default in tool toggles

### MCP Server (mcp_server.py)
- Added `@mcp.tool` decorated `update()` function
- Added `@mcp.tool` decorated `delete()` function
- Updated MCP instructions to document new tools

## Testing

### Test Update Tool
```bash
# Store a fact
curl -X POST http://localhost:8000/api/cognee/remember \
  -H "Content-Type: application/json" \
  -d '{"text": "User owns a blue water bottle"}'

# Wait for cognify, then update it
curl -X POST http://localhost:8000/api/cognee/update \
  -H "Content-Type: application/json" \
  -d '{
    "query": "water bottle",
    "old_text": "blue water bottle",
    "new_text": "red water bottle"
  }'

# Verify the update
curl -X POST http://localhost:8000/api/cognee/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "water bottle"}'
```

### Test Delete Tool
```bash
# Store a fact
curl -X POST http://localhost:8000/api/cognee/remember \
  -H "Content-Type: application/json" \
  -d '{"text": "This is an old fact to delete"}'

# Delete it
curl -X POST http://localhost:8000/api/cognee/delete \
  -H "Content-Type: application/json" \
  -d '{
    "query": "old fact to delete",
    "exact_match": false
  }'
```

## Limitations

1. **Cognee doesn't support direct chunk deletion**: The delete tool marks memories with `[DELETED]` prefix instead of actually removing them. This is a Cognee API limitation.

2. **Update creates new memories**: The update tool creates new memories with the updated text rather than modifying existing ones. Old memories still exist but new ones take precedence in recall.

3. **Background processing**: Both operations trigger background cognify, so changes may take a few seconds to appear in recall results.

## Use Cases

1. **Correcting facts**: User says "My water bottle is red, not blue" → use `update()` to fix the memory
2. **Removing outdated info**: User says "Forget about my old job" → use `delete()` to remove specific memories
3. **Updating preferences**: User changes their mind → use `update()` to reflect new preferences
4. **Cleaning up errors**: Agent stored wrong information → use `delete()` to remove incorrect memories

## Future Improvements

- Implement true chunk deletion when Cognee API supports it
- Add batch update/delete operations
- Add undo functionality for recent updates/deletes
- Add memory versioning to track changes over time
