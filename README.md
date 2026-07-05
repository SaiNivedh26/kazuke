# Kazake

**Turn live perception into persistent memory.**

A multimodal AI agent that watches, listens, and remembers meaningful moments from the real world — storing them as graph-backed memory with visual evidence.

---

## What it does

Kazake streams live camera and microphone input through Gemini Live, detects memory-worthy events (objects, ownership, relationships, locations), and persists them as structured knowledge in a Cognee knowledge graph — all in near real time.

Show it your water bottle and say *"This was gifted by my grandfather."* Kazake captures the object, the relationship, and a frame snapshot as evidence. Later, ask *"Where is the bottle gifted by my grandfather?"* and it recalls the memory with visual proof.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (React + tldraw)                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Camera   │  │ Mic (16kHz)  │  │ Screen Share (1fps)   │  │
│  └────┬─────┘  └──────┬───────┘  └───────────┬───────────┘  │
│       │               │                       │              │
│       └───────────────┼───────────────────────┘              │
│                       ▼                                      │
│            Gemini Live WebSocket                             │
│            (gemini-3.1-flash-live-preview)                   │
│                       │                                      │
│                       ▼                                      │
│              Tool Call Emission                              │
│         (capture_memory_event, etc.)                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (:8080)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Ephemeral    │  │ Frame Upload │  │ Tool Execution    │  │
│  │ Token Auth   │  │ to Storage   │  │ & Routing         │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Cognee Memory Layer                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Graph    │  │ Vector       │  │ Relational            │  │
│  │ Store    │  │ Index        │  │ Retrieval             │  │
│  └──────────┘  └──────────────┘  └───────────────────────┘  │
│                                                              │
│  Entities: Person, Object, Place, Event, Relationship        │
│  Relations: owned_by, gifted_by, located_in, seen_at         │
└─────────────────────────────────────────────────────────────┘
```

### Latency budget

| Stage | Target |
|---|---|
| Frame/audio → model understanding | 300–1500ms |
| Tool-call emission | 300–1200ms |
| Snapshot upload + metadata persist | 200–1000ms |
| Cognee memory write | 300–1500ms |
| Recall query | 300–1200ms |

End-to-end perceived delay: **~1–3 seconds**.

---

## Project structure

```
weekend-hack/
├── server.py                          # FastAPI backend — Cognee proxy, WebSocket, file upload
├── cognee_realtime_graph.py           # CLI for interactive knowledge graph building
├── static/index.html                  # GoJS graph visualization (served by FastAPI)
├── canvas-whisper-sparkle/            # React frontend (TanStack Start + Vite + tldraw)
│   ├── app/
│   │   ├── routes/
│   │   │   ├── canvas.tsx             # Canvas workspace with voice aura
│   │   │   └── _layout.tsx            # Root layout
│   │   ├── components/
│   │   │   ├── CanvasWorkspace.tsx     # tldraw canvas, file management, context groups
│   │   │   ├── VoiceAura.tsx          # Animated aura (connecting/listening/speaking/thinking)
│   │   │   ├── ToolsDrawer.tsx        # Toggle 25+ tools
│   │   │   └── KnowledgeGraphDialog.tsx # Graph visualization overlay
│   │   └── hooks/
│   │       └── useGeminiLive.ts       # WebSocket lifecycle, audio capture/playback, tool exec
│   └── package.json
├── gemini-live-ephemeral-tokens-websocket/  # Standalone Gemini Live client (vanilla JS)
│   ├── server.py                      # Token generation + MCP proxy
│   ├── frontend/                      # Vanilla JS frontend
│   └── mcp_server.py                 # Composio MCP integration
├── test_*.py                          # Test suite
├── AGENTS.md                          # Full build brief and design doc
└── .env                               # Environment config (not committed)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TanStack Router/Start, Vite 8, Tailwind CSS 4, tldraw |
| Audio | Web Audio API, AudioWorklet (16kHz capture, 24kHz playback) |
| Visualization | GoJS (graph), tldraw (canvas), Lottie (animations) |
| Backend | Python, FastAPI, Uvicorn |
| AI/ML | Gemini Live API (`gemini-3.1-flash-live-preview`) via WebSocket |
| Memory | Cognee (graph + vector + relational retrieval) |
| Auth | Ephemeral token exchange (backend generates short-lived Google tokens) |
| Integrations | Notion, Slack, Gmail, Google Calendar, Google Drive (via Composio) |

---

## Tool system

The agent has access to 25+ tools across these categories:

- **Cognee**: `remember`, `batch_remember`, `cognify`, `recall`, `forget`, `update`, `delete`
- **Notion**: `search`, `create_page`, `append_to_page`, `get_page`
- **Slack**: `send_message`, `list_channels`
- **Gmail**: `fetch_emails`, `send_email`
- **Calendar**: `get_events`, `create_event`, `delete_event`
- **Google Drive**: `find_file`, `get_metadata`, `download_file`, `create_text_file`, `create_folder`, `fetch_to_canvas`
- **Canvas**: `list_files`, `group_files`, `add_text_file`

---

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 20+
- Cognee instance (local or remote)
- Google Gemini API key

### Environment

```bash
cp .env.example .env
# Set these:
# BASE_URL, API_KEY, TENANT_ID, USER_ID  — Cognee config
# GEMINI_API_KEY                          — Google Gemini
```

### Backend

```bash
python -m venv hoo
source hoo/bin/activate
pip install fastapi uvicorn requests python-dotenv

python server.py
# FastAPI running at http://localhost:8080
```

### Frontend

```bash
cd canvas-whisper-sparkle
npm install
npm run dev
# TanStack Start app at http://localhost:3000
```

### Graph visualization (standalone)

```bash
python server.py
# Open http://localhost:8080 for GoJS graph view
```

### CLI knowledge graph builder

```bash
python cognee_realtime_graph.py
# Interactive CLI: add text, recall, forget, list data
```

---

## Memory model

Kazake stores structured episodic memories, not raw video. Each memory event contains:

```json
{
  "event_type": "object_observed",
  "object_label": "water bottle",
  "speaker_identity": "Sai",
  "relations": [
    {"type": "owned_by", "target": "Sai"},
    {"type": "gifted_by", "target": "Grandfather"},
    {"type": "located_in", "target": "kitchen shelf"}
  ],
  "frame_uri": "s3://bucket/frame_00123.jpg",
  "timestamp": "2026-07-04T10:35:12Z",
  "transcript_excerpt": "This water bottle was gifted by my grandfather.",
  "confidence": 0.87
}
```

### Design principles

- **Event-driven, not frame-rate**: Graph updates on semantic events, not every frame
- **Speech + vision**: Both modalities required before creating durable memory
- **Dedup on write**: Fast recall check before creating new entities
- **Confidence gating**: Minimum threshold before persisting
- **Observation → fact pipeline**: Low-latency observation first, async enrichment later
- **Evidence-backed**: Frame snapshots stored in object storage, URIs in graph

---

## Demo flow

1. Start a live session with camera and microphone
2. Show objects and narrate naturally — *"This is my desk"*, *"These keys are usually kept near the TV stand"*
3. Watch memory events appear in real time on the graph
4. End session, start a new one
5. Ask a recall question — *"Where is the bottle gifted by my grandfather?"*
6. Get an answer with image-backed evidence from the earlier observation

---

## License

Private — weekend hack project.
