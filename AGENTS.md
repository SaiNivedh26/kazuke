# Live Perception to Cognee Memory: Feasibility Build Brief

## Objective

Build a hackathon MVP where a user streams live camera and microphone input, narrates objects and relationships in their house, and the system converts those moments into persistent structured memory in Cognee in near real time.[1][2]

The target experience is not raw video archiving and not plain transcript storage. The goal is event-driven multimodal memory: the system should recognize meaningful moments such as object identity, ownership, location, and relationship statements, then store them as graph-backed memories with image evidence for later recall.[3][2][4]

## Feasibility assessment

This is feasible as a hack MVP if “real time” is scoped correctly.[1][2] A realistic system can process a live stream continuously, detect memory-worthy events, and write structured memory within roughly interactive latency, but it should not try to convert every frame into graph updates.[1][5]

A practical definition of real time for this project is:

- Live perception loop from audio/video stream to model understanding in sub-second to low-single-digit seconds.[1][5]
- Structured memory write after a meaningful observation in about 1–3 seconds, depending on network and storage latency.[1][2]
- Immediate or near-immediate recall of already stored memories during the same or later session through Cognee memory tools.[2][4]

This means the graph updates on semantic events, not at video frame rate. The system should sample or gate frames, fuse them with speech, and create memories only when there is enough confidence that a durable fact or observation exists.[1][2]

## Why Cognee fits

Cognee is positioned as a persistent memory layer for agents, with MCP-based tools for reading and writing memory and a graph, vector, and relational retrieval model behind it.[3][6][2] That makes it suitable for storing structured long-term memory derived from a live multimodal agent rather than trying to serve as a raw media processing engine.[3][2]

The design principle should be: Gemini Live handles continuous perception and tool decisions, while Cognee stores durable memory objects, relationships, and evidence references.[1][2] In other words, the realtime model is the perceptual front end, and Cognee is the persistent memory back end.[6][2]

## System architecture

### 1. Live perception lane

A client application streams camera frames and microphone audio to Gemini Live using a live session transport such as WebSockets or the supported low-latency interaction path in the Live API.[1][5] The model continuously processes what is seen and heard, and keeps short-lived conversational state for the session.[1][7]

### 2. Memory decision lane

The model should be configured with tools so it does not directly “decide everything in text.” Instead, it emits structured calls only when it detects a memory-worthy event, such as a named object, an ownership statement, a sentimental relationship, or a location update.[1][5]

Example events:

- “This is my water bottle.”
- “This was gifted by my grandfather.”
- “These keys are usually kept near the TV stand.”
- “This is my work desk.”

These become candidate memory events rather than free-form transcript lines.[1][2]

### 3. Persistent memory lane

A backend service receives the tool call, persists an image snapshot or clip reference to object storage, normalizes the payload, checks existing memory for duplicates or conflicts, and then writes the structured memory into Cognee through MCP or SDK operations.[2][4][8]

The backend is also where memory policy lives: deduplication, confidence thresholds, entity matching, versioning, and whether a new observation should create, update, or reject a memory item.[2][4]

## Recommended memory model

Do not store full video as the primary knowledge unit. Store compact event packets backed by visual evidence.[3][2]

Suggested entity types:

- Person
- Object
- Place
- Event
- Relationship
- Observation
- Session

Suggested relation types:

- `owned_by`
- `gifted_by`
- `located_in`
- `usually_kept_at`
- `seen_at`
- `mentioned_by`
- `observed_in_session`

Suggested observation schema:

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

This turns perception into structured episodic memory with traceable evidence.[2][8]

## Tool design

The live model should have narrow tools instead of one generic “save memory” function. This makes behavior easier to control and debug.[1][2]

Suggested tool surface:

```ts
capture_memory_event({
  event_type,
  label,
  transcript_excerpt,
  frame_ref,
  entities,
  relations,
  location_hint,
  confidence
})

search_memory_candidates({
  entity_label,
  entity_type,
  visual_hint,
  relation_hint
})

update_memory_relation({
  source_id,
  relation,
  target_id,
  evidence_ref,
  confidence
})

mark_memory_uncertain({
  candidate_payload,
  reason
})
```

The backend can translate these tool calls into Cognee memory operations such as `remember`, `recall`, and `forget`, while also storing media references outside the graph itself.[2][4]

## Real-time strategy

Real-time graph construction is possible only if the system is event-driven.

Recommended rules:

- Sample one frame every 1–3 seconds, or trigger on scene/object change.[1][5]
- Use speech plus vision together before creating a durable memory, because vision alone is often ambiguous and speech alone lacks grounding.[1][5]
- Perform a fast recall check before writing a new entity, to avoid duplicates like creating three different “water bottle” nodes for the same item.[2][4]
- Write a low-latency observation first, then do slower enrichment or merging asynchronously in the background.[2][8]

This gives a responsive experience while protecting graph quality.[2][4]

## Hard problems and mitigations

### Identity resolution

The main challenge is deciding whether the currently seen object is new or already known.[2][8] This is especially hard for generic household objects like mugs, bottles, books, and keys.

Mitigation:

- Combine visual fingerprinting, transcript cues, and location context before creating a new node.
- Ask a brief clarification question when confidence is low, for example: “Is this the same bottle you showed earlier?”
- Support user labeling for important persistent objects.

### Incorrect permanence

A single statement in a live stream should not always become long-term truth.[2][4] For example, “my keys are here” may be temporary, while “this was gifted by my grandfather” is much more durable.

Mitigation:

- Classify memories into durable facts, temporary state, and episodic observations.
- Use TTL or lower retrieval priority for likely transient observations.
- Promote memories only after repeated confirmation or explicit user phrasing.

### Graph pollution

If every observation becomes memory, the graph becomes noisy and retrieval quality drops.[3][2]

Mitigation:

- Require a minimum confidence threshold.
- Gate writes through event categories.
- Batch and merge observations asynchronously.
- Prefer “observation events” first, then derived stable facts later.

### Media storage

Cognee should not be used as the raw binary store for full live video.[3][2] The graph should hold references to evidence, not the full video stream itself.

Mitigation:

- Store sampled frames or short clips in object storage.
- Save only URIs, thumbnails, timestamps, and metadata inside the memory payload.

## MVP scope

The best MVP is not “memory for everything in the house.” It should focus on high-value household memory with explicit user narration.[1][2]

Recommended MVP capabilities:

- Recognize a named object when the user points the camera at it and talks about it.[1][5]
- Attach a relation such as owner, gift source, sentimental tag, or room/location.[2][4]
- Save a frame snapshot as evidence.[1]
- Recall the object later with its relation and evidence, for example: “Where is the bottle gifted by my grandfather?”[2][4]
- Update a location observation when the object is seen again in another place.[2]

## Suggested demo flow

1. Start a live session with camera and microphone.[1][5]
2. Show a few meaningful objects and narrate them naturally, such as a desk, a bottle, a key tray, and a laptop.[1]
3. Let the model create memory events in near real time and display the evolving graph or timeline in the UI.[2][4]
4. End the session, start a new one, and ask a recall question using the stored memory.[2]
5. Show that the answer includes not just text but image-backed evidence from the earlier observation.[1][2]

This demonstrates multimodal perception, persistent memory, graph construction, and cross-session recall in one story.[1][2]

## Concrete build stack

- Client: Web or mobile app with camera and microphone streaming.
- Realtime model: Gemini Live for multimodal streaming and tool calls.[1][5]
- Orchestrator: Node.js or Python server handling session control and tool execution.
- Media storage: S3, Supabase Storage, or local object storage for frame snapshots.
- Memory layer: Cognee MCP server or direct Cognee SDK-backed service for `remember`, `recall`, and memory updates.[6][2][4]
- UI: live stream panel, extracted event log, graph/timeline view, and recall chat/search panel.

## Latency budget

A realistic latency budget for the MVP:

| Stage | Target latency | Notes |
|---|---:|---|
| Frame/audio ingestion to Live model understanding | 300 ms to 1500 ms | Depends on network and model turn size.[1][5] |
| Tool-call emission after a meaningful event | 300 ms to 1200 ms | Best when tool schema is narrow.[1] |
| Snapshot upload and metadata persistence | 200 ms to 1000 ms | Depends on storage choice. |
| Cognee memory write | 300 ms to 1500 ms | Depends on local vs remote deployment.[2][4] |
| Recall query from existing memory | 300 ms to 1200 ms | Varies with graph size and deployment.[2] |

The end-to-end perceived delay for “I showed an object and it became memory” should stay around 1–3 seconds for the experience to feel live.[1][2]

## What success looks like

The hack should not claim perfect scene understanding. Success is a system that can convert narrated live perception into durable, queryable, evidence-backed memory in near real time.[1][2]

A strong product sentence is:

> Turn live perception into persistent memory.

A more concrete version is:

> A multimodal agent that watches, listens, and remembers meaningful moments from the real world as graph-backed memory with visual evidence.[3][2]

## Recommendation

Proceed only if the build is scoped as event-driven multimodal memory, not full-frame continuous scene graphing.[1][2] The best architecture is Gemini Live for perception and tool selection, plus Cognee for persistent memory and cross-session recall.[6][1][2]

The MVP should prioritize reliability of memory events, evidence-backed storage, and strong recall over ambitious full-house visual indexing.[2][4]
