# Kazake
<p align="center">
  <img
    src="https://github.com/user-attachments/assets/f6a1e75a-73f9-4d0f-9efd-d3b6aa3a39c9"
    alt="Kazake"
    width="560"
  />
</p>

![React](https://img.shields.io/badge/Made%20with-React%2019-61DAFB)
![TanStack Router](https://img.shields.io/badge/Made%20with-TanStack%20Router-FF4154)
![TanStack Start](https://img.shields.io/badge/Made%20with-TanStack%20Start-FF4154)
![Vite](https://img.shields.io/badge/Made%20with-Vite%208-646CFF)
![Tailwind CSS](https://img.shields.io/badge/Made%20with-Tailwind%20CSS%204-06B6D4)
![tldraw](https://img.shields.io/badge/Made%20with-tldraw-000000)
![Web Audio API](https://img.shields.io/badge/Made%20with-Web%20Audio%20API-F7DF1E)
![AudioWorklet](https://img.shields.io/badge/Made%20with-AudioWorklet-FF9800)
![GoJS](https://img.shields.io/badge/Made%20with-GoJS-007ACC)
![Lottie](https://img.shields.io/badge/Made%20with-Lottie-00DDB3)
![Python](https://img.shields.io/badge/Made%20with-Python%203.12-3776AB)
![FastAPI](https://img.shields.io/badge/Made%20with-FastAPI-009688)
![Uvicorn](https://img.shields.io/badge/Made%20with-Uvicorn-499848)
![Gemini Live API](https://img.shields.io/badge/Made%20with-Gemini%20Live%20API-4285F4)
![Cognee](https://img.shields.io/badge/Made%20with-Cognee-6E56CF)
![Ephemeral Token Exchange](https://img.shields.io/badge/Made%20with-Ephemeral%20Token%20Exchange-4285F4)
![Notion](https://img.shields.io/badge/Made%20with-Notion-000000)
![Slack](https://img.shields.io/badge/Made%20with-Slack-4A154B)
![Gmail](https://img.shields.io/badge/Made%20with-Gmail-EA4335)
![Google Calendar](https://img.shields.io/badge/Made%20with-Google%20Calendar-4285F4)
![Google Drive](https://img.shields.io/badge/Made%20with-Google%20Drive-34A853)
![Composio](https://img.shields.io/badge/Made%20with-Composio-7C3AED)


**Turn live perception into persistent memory.**

It is a context as a service(CAAS) platform. It captures context from voice, screen sharing, files, and connected tools like Notion, Gmail, Drive, and Slack, then keeps that context available for future use across agents and tools.

Since it has access to Cognee, it can maintain a graphical context between different sessions, not only materialistic data, but also the visual contextual ingestion, for adding daily life activity/events to the unified platform

By default comes with a canvas page to maintain and manage content to pass down to downstream agents as an MCP server. These are specially configured as bi-directional streaming mcp's, so coding agents can update and remove the context as per the user request.

Cognee is the memory layer behind Kazake. We use it to store, organize, and retrieve project context as structured memory, so the AI can remember important details, group related information, and use the same context again later. It formulates a huge, dense graph connection that can reason between different activities that happened across different days and can perform parallel reasoning with the configured tools, making it superior to any other tools out there.


### check the [demo](https://www.youtube.com/watch?v=BPySjaEyfmg)


---


## Architecture

<img width="1580" height="1275" alt="shapes at 26-07-06 12 34 01" src="https://github.com/user-attachments/assets/e9c7b77c-30d7-4d45-b9e2-dae3f94ae5b7" />



---

## Core features

<img width="720" height="404" alt="avyfdq" src="https://github.com/user-attachments/assets/2038e12e-ce3d-4635-ae3f-8d9c1b3e28a7" />
<img width="720" height="404" alt="avyfno" src="https://github.com/user-attachments/assets/c03a2ec3-8bb0-4230-8342-84e7bbe5636e" />
<img width="720" height="404" alt="avyft7" src="https://github.com/user-attachments/assets/fa841e81-0e95-4b98-94e9-cf2fbad10135" />
<img width="720" height="404" alt="avyfx0" src="https://github.com/user-attachments/assets/a7a6d58f-e403-4851-85af-4822c8109f70" />
<img width="720" height="404" alt="avyg85" src="https://github.com/user-attachments/assets/aa5532af-84f5-40c6-8434-ae669053b491" />
<img width="720" height="404" alt="avygc1" src="https://github.com/user-attachments/assets/c59b3aa9-d9c6-41d1-9f6f-31974d3efc80" />


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
- Composio Api key
- 

### Environment

```bash
cp .env.example .env
# Set these:
# BASE_URL, API_KEY, TENANT_ID, USER_ID  — Cognee config
# GEMINI_API_KEY                          — Google Gemini
# COMPOSIO_API_KEY
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
- **Speech + vision**: Both modalities are required before creating durable memory
- **Dedup on write**: Fast recall check before creating new entities
- **Confidence gating**: Minimum threshold before persisting
- **Observation → fact pipeline**: Low-latency observation first, async enrichment later
- **Evidence-backed**: Frame snapshots stored in object storage, URIs in graph

---

![Material wave loading](https://github.com/user-attachments/assets/a08255eb-9647-471d-9881-61871332249f)

## Developers

[Sai Nivedh](https://www.github.com/SaiNivedh26)
