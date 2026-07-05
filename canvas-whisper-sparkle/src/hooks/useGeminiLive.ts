import { useState, useEffect, useRef, useCallback } from "react";
import { Howl } from "howler";
import type { AuraState } from "@/components/VoiceAura";

// Tool toggle state matching ToolsDrawer
export type ToolToggles = Record<string, boolean>;

// Connection state
export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

// Message types from Gemini
export type MessageType =
  | "text"
  | "audio"
  | "input_transcription"
  | "output_transcription"
  | "tool_call"
  | "tool_result"
  | "turn_complete"
  | "setup_complete"
  | "interrupted"
  | "error";

export interface GeminiMessage {
  type: MessageType;
  data: any;
  endOfTurn?: boolean;
}

// Hook options
export interface UseGeminiLiveOptions {
  serverUrl?: string;
  toolToggles: ToolToggles;
  systemInstructions?: string;
  onMessage?: (msg: GeminiMessage) => void;
  onError?: (error: Error) => void;
}

// Hook return type
export interface UseGeminiLiveReturn {
  connectionState: ConnectionState;
  agentState: AuraState;
  connect: () => Promise<void>;
  disconnect: () => void;
  sendAudio: (data: ArrayBuffer) => void;
  sendVideo: (data: ArrayBuffer) => void;
  sendToolResponse: (functionResponses: any[]) => void;
  error: string | null;
}

// WebSocket message types
interface WSMessage {
  type: MessageType;
  data?: any;
  endOfTurn?: boolean;
}

export function useGeminiLive(options: UseGeminiLiveOptions): UseGeminiLiveReturn {
  const { serverUrl = "", toolToggles, systemInstructions = "", onMessage, onError } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [agentState, setAgentState] = useState<AuraState>("connecting");
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const isPlayingRef = useRef(false);
  const isCapturingRef = useRef(true);
  const isInitializedRef = useRef(false);
  const retrievalMusicRef = useRef<Howl | null>(null);

  // Initialize retrieval music
  useEffect(() => {
    retrievalMusicRef.current = new Howl({
      src: ["/retrieval-music.mp3"],
      loop: true,
      volume: 0,
    });
    return () => {
      if (retrievalMusicRef.current) {
        retrievalMusicRef.current.unload();
      }
    };
  }, []);

  // Play retrieval music with fade in
  const playRetrievalMusic = useCallback(() => {
    if (retrievalMusicRef.current && !retrievalMusicRef.current.playing()) {
      retrievalMusicRef.current.play();
      retrievalMusicRef.current.fade(0, 0.3, 1000);
    }
  }, []);

  // Stop retrieval music with fade out
  const stopRetrievalMusic = useCallback(() => {
    if (retrievalMusicRef.current && retrievalMusicRef.current.playing()) {
      const music = retrievalMusicRef.current;
      music.fade(music.volume(), 0, 1000);
      setTimeout(() => {
        if (music.playing()) {
          music.stop();
        }
      }, 1000);
    }
  }, []);

  // Initialize audio playback worklet
  const initPlayback = async () => {
    if (isInitializedRef.current) return;

    try {
      // Create audio context at 24kHz to match Gemini
      playbackContextRef.current = new AudioContext({ sampleRate: 24000 });

      // Load the audio worklet
      await playbackContextRef.current.audioWorklet.addModule(
        "/audio-processors/playback.worklet.js",
      );

      // Create worklet node
      workletNodeRef.current = new AudioWorkletNode(playbackContextRef.current, "pcm-processor");

      // Connect to output
      workletNodeRef.current.connect(playbackContextRef.current.destination);

      isInitializedRef.current = true;
      console.log("🔊 Audio playback initialized");
    } catch (err) {
      console.error("Failed to initialize audio playback:", err);
    }
  };

  // Stop audio playback immediately
  const stopPlayback = useCallback(() => {
    console.log("🔇 Stopping playback");
    isPlayingRef.current = false;

    // Send interrupt message to worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.port.postMessage("interrupt");
    }
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback(
    (jsonData: string) => {
      try {
        const data = JSON.parse(jsonData);
        const messages = parseMessages(data);

        for (const msg of messages) {
          switch (msg.type) {
            case "setup_complete":
              console.log("✅ Setup complete");
              setAgentState("listening");
              isCapturingRef.current = true;
              break;
            case "turn_complete":
              console.log("✅ Turn complete");
              setAgentState("listening");
              isCapturingRef.current = true;
              stopRetrievalMusic();
              break;
            case "audio":
              setAgentState("speaking");
              isCapturingRef.current = false;
              stopRetrievalMusic();
              playAudio(msg.data);
              break;
            case "input_transcription":
              setAgentState("listening");
              break;
            case "output_transcription":
              setAgentState("speaking");
              stopRetrievalMusic();
              break;
            case "interrupted":
              console.log("🗣️ Interrupted! Stopping playback");
              stopPlayback();
              stopRetrievalMusic();
              setAgentState("listening");
              isCapturingRef.current = true;
              break;
            case "tool_call":
              setAgentState("thinking");
              isCapturingRef.current = false;
              playRetrievalMusic();
              handleToolCall(msg.data);
              break;
            case "error":
              setError(msg.data?.error || "Unknown error");
              stopRetrievalMusic();
              break;
          }

          onMessage?.(msg);
        }
      } catch (err) {
        console.error("Error parsing message:", err);
      }
    },
    [onMessage, stopPlayback, stopRetrievalMusic, playRetrievalMusic],
  );

  // Play audio response
  const playAudio = useCallback(async (base64Audio: string) => {
    // Initialize playback if needed
    if (!isInitializedRef.current) {
      await initPlayback();
    }

    if (!playbackContextRef.current || !workletNodeRef.current) {
      console.error("Playback not initialized");
      return;
    }

    // Resume context if suspended
    if (playbackContextRef.current.state === "suspended") {
      await playbackContextRef.current.resume();
    }

    try {
      // Decode base64 to ArrayBuffer
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert PCM16 to float32
      const pcm16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(pcm16.length);
      for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768.0;
      }

      // Send to worklet
      workletNodeRef.current.port.postMessage(float32);
      isPlayingRef.current = true;
    } catch (err) {
      console.error("Error playing audio:", err);
    }
  }, []);

  // Handle tool calls
  const handleToolCall = useCallback(
    async (toolCall: any) => {
      if (!toolCall?.functionCalls) return;

      const functionResponses: any[] = [];

      for (const fc of toolCall.functionCalls) {
        const { name, args, id } = fc;
        console.log(`🛠️ Tool call: ${name}`, args);

        try {
          const result = await executeTool(name, args, toolToggles, serverUrl, onMessage);
          functionResponses.push({
            id,
            name,
            response: result,
          });
          // Surface fetch-to-canvas results to the UI so it can render the upload item.
          if (name === "gdrive_fetch_to_canvas") {
            onMessage?.({ type: "tool_result", data: { name, args, result } });
          }
        } catch (err) {
          console.error(`Tool ${name} failed:`, err);
          functionResponses.push({
            id,
            name,
            response: { error: (err as Error).message },
          });
        }
      }

      // Send responses back
      if (functionResponses.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            toolResponse: {
              functionResponses,
            },
          }),
        );
      }
    },
    [toolToggles, serverUrl, onMessage],
  );

  // Connect to server
  const connect = useCallback(async () => {
    try {
      console.log("🔌 Starting connection...");
      setConnectionState("connecting");
      setError(null);

      // Get ephemeral token from our server
      console.log(`🔑 Fetching token from ${serverUrl}/api/token`);
      const tokenResponse = await fetch(`${serverUrl}/api/token`, { method: "POST" });
      if (!tokenResponse.ok) {
        throw new Error(`Failed to get token: ${tokenResponse.status}`);
      }
      const { token } = await tokenResponse.json();
      console.log("✅ Token received:", token?.substring(0, 20) + "...");

      // Connect directly to Google's WebSocket API
      const wsUrl = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContentConstrained?access_token=${token}`;
      console.log("🌐 Connecting to Google WebSocket...");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("✅ WebSocket connected!");
        setConnectionState("connected");
        setAgentState("listening");

        // Build tools list based on toggles
        const tools = getEnabledTools(toolToggles);
        console.log(`🛠️ Sending setup with ${tools.length} tool groups`);

        // Send setup message
        const setupMsg = {
          setup: {
            model: "models/gemini-3.1-flash-live-preview",
            generationConfig: {
              responseModalities: ["AUDIO"],
              speechConfig: {
                voiceConfig: {
                  prebuiltVoiceConfig: {
                    voiceName: "Puck",
                  },
                },
              },
            },
            systemInstruction: {
              parts: [{ text: systemInstructions + " When the session starts, greet the user briefly and ask how you can help them today." }],
            },
            tools: tools.length > 0 ? tools : undefined,
            realtimeInputConfig: {
              automaticActivityDetection: {
                disabled: false,
                silenceDurationMs: 2000,
                prefixPaddingMs: 500,
                endOfSpeechSensitivity: "END_SENSITIVITY_UNSPECIFIED",
                startOfSpeechSensitivity: "START_SENSITIVITY_UNSPECIFIED",
              },
              activityHandling: "ACTIVITY_HANDLING_UNSPECIFIED",
            },
          },
        };
        console.log("📤 Setup message:", JSON.stringify(setupMsg, null, 2));
        ws.send(JSON.stringify(setupMsg));

        // Send initial greeting prompt after setup
        setTimeout(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({
                clientContent: {
                  turns: [
                    {
                      parts: [{ text: "Hello! Please greet me and let me know you're ready to help." }],
                      role: "user",
                    },
                  ],
                  turnComplete: true,
                },
              }),
            );
          }
        }, 1000);
      };

      ws.onmessage = async (event) => {
        console.log("📩 WebSocket message received");
        // Gemini sends Blob data, need to convert to text first
        let jsonData: string;
        if (event.data instanceof Blob) {
          jsonData = await event.data.text();
        } else if (event.data instanceof ArrayBuffer) {
          jsonData = new TextDecoder().decode(event.data);
        } else {
          jsonData = event.data;
        }
        handleMessage(jsonData);
      };

      ws.onerror = (event) => {
        console.error("❌ WebSocket error:", event);
        setError("Connection error");
        setConnectionState("error");
        onError?.(new Error("WebSocket error"));
      };

      ws.onclose = (event) => {
        console.log("🔌 WebSocket closed:", event.code, event.reason);
        setConnectionState("disconnected");
        setAgentState("connecting");
      };

      // Start audio capture
      console.log("🎤 Starting audio capture...");
      await startAudioCapture();
      console.log("✅ Audio capture started");
    } catch (err) {
      console.error("❌ Connection failed:", err);
      setError(err.message);
      setConnectionState("error");
      onError?.(err as Error);
    }
  }, [serverUrl, systemInstructions, toolToggles, handleMessage, onError]);

  // Disconnect
  const disconnect = useCallback(() => {
    stopAudioCapture();
    stopPlayback();
    stopRetrievalMusic();

    // Clean up worklet
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    // Clean up playback context
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }

    isInitializedRef.current = false;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState("disconnected");
    setAgentState("connecting");
  }, [stopPlayback, stopRetrievalMusic]);

  // Send audio data
  const sendAudio = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const base64 = arrayBufferToBase64(data);
      wsRef.current.send(
        JSON.stringify({
          realtimeInput: {
            audio: {
              mimeType: "audio/pcm",
              data: base64,
            },
          },
        }),
      );
    }
  }, []);

  // Send video data
  const sendVideo = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const base64 = arrayBufferToBase64(data);
      console.log(`📹 Sending video frame (${data.byteLength} bytes, base64 length: ${base64.length})`);
      wsRef.current.send(
        JSON.stringify({
          realtimeInput: {
            video: {
              mimeType: "image/jpeg",
              data: base64,
            },
          },
        }),
      );
    } else {
      console.warn("WebSocket not open, cannot send video");
    }
  }, []);

  // Send tool response
  const sendToolResponse = useCallback((functionResponses: any[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          toolResponse: {
            functionResponses,
          },
        }),
      );
    }
  }, []);

  // Start audio capture
  const startAudioCapture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        // Only send audio when not playing (VAD handled by Gemini, but we pause capture during playback)
        if (isCapturingRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          const pcm16 = floatTo16BitPCM(inputData);
          sendAudio(pcm16.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      isCapturingRef.current = true;
      console.log("🎤 Audio capture started at 16kHz");
    } catch (err) {
      console.error("Failed to start audio capture:", err);
    }
  };

  // Stop audio capture
  const stopAudioCapture = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    agentState,
    connect,
    disconnect,
    sendAudio,
    sendVideo,
    sendToolResponse,
    error,
  };
}

// Helper functions
function parseMessages(data: any): GeminiMessage[] {
  const messages: GeminiMessage[] = [];

  if (data.setupComplete) {
    messages.push({ type: "setup_complete", data: "", endOfTurn: false });
    return messages;
  }

  if (data.toolCall) {
    messages.push({ type: "tool_call", data: data.toolCall, endOfTurn: false });
    return messages;
  }

  const serverContent = data?.serverContent;
  const parts = serverContent?.modelTurn?.parts;

  if (parts?.length) {
    for (const part of parts) {
      if (part.inlineData) {
        messages.push({ type: "audio", data: part.inlineData.data, endOfTurn: false });
      } else if (part.text) {
        messages.push({ type: "text", data: part.text, endOfTurn: false });
      }
    }
  }

  if (serverContent?.inputTranscription) {
    messages.push({
      type: "input_transcription",
      data: serverContent.inputTranscription,
      endOfTurn: false,
    });
  }

  if (serverContent?.outputTranscription) {
    messages.push({
      type: "output_transcription",
      data: serverContent.outputTranscription,
      endOfTurn: false,
    });
  }

  if (serverContent?.interrupted) {
    messages.push({ type: "interrupted", data: "", endOfTurn: false });
  }

  if (serverContent?.turnComplete) {
    messages.push({ type: "turn_complete", data: "", endOfTurn: true });
  }

  return messages;
}

async function executeTool(
  name: string,
  args: any,
  toggles: ToolToggles,
  serverUrl: string,
  onMessage?: (msg: GeminiMessage) => void,
): Promise<any> {
  // Map tool names to API endpoints
  const toolMap: Record<string, { endpoint: string; enabled: string }> = {
    cognee_remember: { endpoint: "/api/cognee/remember", enabled: "cognee-remember" },
    cognee_remember_batch: {
      endpoint: "/api/cognee/remember_batch",
      enabled: "cognee-batch-remember",
    },
    cognee_cognify: { endpoint: "/api/cognee/cognify", enabled: "cognee-cognify" },
    cognee_recall: { endpoint: "/api/cognee/recall", enabled: "cognee-recall" },
    cognee_forget: { endpoint: "/api/cognee/forget", enabled: "cognee-forget" },
    cognee_update: { endpoint: "/api/cognee/update", enabled: "cognee-update" },
    cognee_delete: { endpoint: "/api/cognee/delete", enabled: "cognee-delete" },
    notion_search: { endpoint: "/api/notion/search", enabled: "notion-search" },
    notion_create_page: { endpoint: "/api/notion/create_page", enabled: "notion-create-page" },
    notion_append_to_page: { endpoint: "/api/notion/append", enabled: "notion-append" },
    notion_get_page: { endpoint: "/api/notion/get_page", enabled: "notion-get-page" },
    slack_send_message: { endpoint: "/api/composio/call", enabled: "slack-send" },
    slack_list_channels: { endpoint: "/api/composio/call", enabled: "slack-list" },
    gmail_fetch_emails: { endpoint: "/api/composio/call", enabled: "gmail-fetch" },
    gmail_send_email: { endpoint: "/api/composio/call", enabled: "gmail-send" },
    calendar_get_events: { endpoint: "/api/composio/call", enabled: "calendar-get" },
    calendar_create_event: { endpoint: "/api/composio/call", enabled: "calendar-create" },
    calendar_delete_event: { endpoint: "/api/composio/call", enabled: "calendar-delete" },
    gdrive_find_file: { endpoint: "/api/composio/call", enabled: "gdrive-find" },
    gdrive_get_file_metadata: { endpoint: "/api/composio/call", enabled: "gdrive-get-meta" },
    gdrive_download_file: { endpoint: "/api/composio/call", enabled: "gdrive-download" },
    gdrive_create_file_from_text: { endpoint: "/api/composio/call", enabled: "gdrive-create-text" },
    gdrive_create_folder: { endpoint: "/api/composio/call", enabled: "gdrive-create-folder" },
    gdrive_fetch_to_canvas: { endpoint: "/api/composio/call", enabled: "gdrive-fetch-to-canvas" },
    canvas_list_files: { endpoint: "/api/canvas/files", enabled: "canvas-list-files" },
    canvas_group_files: { endpoint: "/api/canvas/group", enabled: "canvas-group-files" },
  };

  const tool = toolMap[name];
  if (!tool) {
    throw new Error(`Unknown tool: ${name}`);
  }

  if (!toggles[tool.enabled]) {
    throw new Error(`Tool ${name} is disabled`);
  }

  // Handle Composio tools specially
  if (
    name.startsWith("slack_") ||
    name.startsWith("gmail_") ||
    name.startsWith("calendar_") ||
    name.startsWith("gdrive_")
  ) {
    const composioArgs = {
      tool_slug: name.toUpperCase(),
      arguments: args,
      sync_response_to_workbench: false,
    };
    const response = await fetch(`${serverUrl}${tool.endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(composioArgs),
    });
    return response.json();
  }

  // Canvas tools
  if (name === "canvas_list_files") {
    const response = await fetch(`${serverUrl}${tool.endpoint}`, { method: "GET" });
    return response.json();
  }
  if (name === "canvas_group_files") {
    const response = await fetch(`${serverUrl}${tool.endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args),
    });
    const result = await response.json();
    onMessage?.({ type: "tool_result", data: { name, args, result } });
    return result;
  }

  // Regular tools
  const response = await fetch(`${serverUrl}${tool.endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  return response.json();
}

function getEnabledTools(toggles: ToolToggles): any[] {
  const functionDeclarations: any[] = [];

  // Cognee tools
  if (toggles["cognee-remember"]) {
    functionDeclarations.push({
      name: "cognee_remember",
      description:
        "Store a fact in persistent memory. Use when user states preferences, facts, or observations.",
      parameters: {
        type: "object",
        properties: {
          text: { type: "string", description: "The fact or observation to remember" },
        },
        required: ["text"],
      },
    });
  }

  if (toggles["cognee-recall"]) {
    functionDeclarations.push({
      name: "cognee_recall",
      description:
        "Search stored memories from previous sessions. Use for questions about past conversations.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "What to search for in memory" },
        },
        required: ["query"],
      },
    });
  }

  if (toggles["cognee-batch-remember"]) {
    functionDeclarations.push({
      name: "cognee_remember_batch",
      description: "Store multiple facts at once. More efficient than multiple remember calls.",
      parameters: {
        type: "object",
        properties: {
          texts: {
            type: "array",
            items: { type: "string" },
            description: "Array of facts to store",
          },
        },
        required: ["texts"],
      },
    });
  }

  if (toggles["cognee-cognify"]) {
    functionDeclarations.push({
      name: "cognee_cognify",
      description:
        "Trigger graph rebuild after storing memories. Call if you need immediate recall.",
      parameters: { type: "object", properties: {} },
    });
  }

  if (toggles["cognee-forget"]) {
    functionDeclarations.push({
      name: "cognee_forget",
      description: "Clear all stored memories. Use only when user explicitly requests.",
      parameters: { type: "object", properties: {} },
    });
  }

  if (toggles["cognee-update"]) {
    functionDeclarations.push({
      name: "cognee_update",
      description:
        "Update existing memories by finding and replacing content. Use when user wants to correct or modify stored facts. Bidirectional memory update.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query to find memories to update",
          },
          old_text: {
            type: "string",
            description: "The text to find and replace in matching memories",
          },
          new_text: {
            type: "string",
            description: "The new text to replace old_text with",
          },
        },
        required: ["query", "old_text", "new_text"],
      },
    });
  }

  if (toggles["cognee-delete"]) {
    functionDeclarations.push({
      name: "cognee_delete",
      description:
        "Delete specific memories by query. More granular than forget (which deletes all). Use when user wants to remove specific facts.",
      parameters: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query to find memories to delete",
          },
          exact_match: {
            type: "boolean",
            description: "If true, only delete memories that exactly match the query",
          },
        },
        required: ["query"],
      },
    });
  }

  // Notion tools
  if (toggles["notion-search"]) {
    functionDeclarations.push({
      name: "notion_search",
      description: "Search Notion workspace for pages and databases.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
        },
        required: ["query"],
      },
    });
  }

  if (toggles["notion-create-page"]) {
    functionDeclarations.push({
      name: "notion_create_page",
      description: "Create a new page in Notion.",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string", description: "Page title" },
          content: { type: "string", description: "Page content" },
          parent_id: { type: "string", description: "Optional parent page ID" },
        },
        required: ["title", "content"],
      },
    });
  }

  if (toggles["notion-append"]) {
    functionDeclarations.push({
      name: "notion_append_to_page",
      description: "Append content to an existing Notion page.",
      parameters: {
        type: "object",
        properties: {
          page_id: { type: "string", description: "Page ID to append to" },
          content: { type: "string", description: "Content to append" },
        },
        required: ["page_id", "content"],
      },
    });
  }

  if (toggles["notion-get-page"]) {
    functionDeclarations.push({
      name: "notion_get_page",
      description: "Get content from a Notion page.",
      parameters: {
        type: "object",
        properties: {
          page_id: { type: "string", description: "Page ID to retrieve" },
        },
        required: ["page_id"],
      },
    });
  }

  // Composio tools (Slack, Gmail, Calendar)
  if (toggles["slack-send"]) {
    functionDeclarations.push({
      name: "slack_send_message",
      description: "Send a message to a Slack channel.",
      parameters: {
        type: "object",
        properties: {
          channel: { type: "string", description: "Channel name or ID" },
          text: { type: "string", description: "Message text" },
        },
        required: ["channel", "text"],
      },
    });
  }

  if (toggles["slack-list"]) {
    functionDeclarations.push({
      name: "slack_list_channels",
      description: "List all Slack channels.",
      parameters: { type: "object", properties: {} },
    });
  }

  if (toggles["gmail-fetch"]) {
    functionDeclarations.push({
      name: "gmail_fetch_emails",
      description: "Fetch emails from Gmail.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
          max_results: { type: "integer", description: "Max emails to fetch" },
        },
      },
    });
  }

  if (toggles["gmail-send"]) {
    functionDeclarations.push({
      name: "gmail_send_email",
      description: "Send an email via Gmail.",
      parameters: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email" },
          subject: { type: "string", description: "Email subject" },
          body: { type: "string", description: "Email body" },
        },
        required: ["to", "subject", "body"],
      },
    });
  }

  if (toggles["calendar-get"]) {
    functionDeclarations.push({
      name: "calendar_get_events",
      description: "Get calendar events.",
      parameters: {
        type: "object",
        properties: {
          start_datetime: { type: "string", description: "Start datetime (ISO format)" },
          end_datetime: { type: "string", description: "End datetime (ISO format)" },
          timezone: { type: "string", description: "Timezone (e.g., Asia/Kolkata)" },
        },
      },
    });
  }

  if (toggles["calendar-create"]) {
    functionDeclarations.push({
      name: "calendar_create_event",
      description: "Create a calendar event.",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string", description: "Event title" },
          start_datetime: { type: "string", description: "Start datetime (ISO format)" },
          end_datetime: { type: "string", description: "End datetime (ISO format)" },
          timezone: { type: "string", description: "Timezone (e.g., Asia/Kolkata)" },
        },
        required: ["title", "start_datetime", "end_datetime"],
      },
    });
  }

  if (toggles["calendar-delete"]) {
    functionDeclarations.push({
      name: "calendar_delete_event",
      description: "Delete a calendar event.",
      parameters: {
        type: "object",
        properties: {
          event_id: { type: "string", description: "Event ID to delete" },
        },
        required: ["event_id"],
      },
    });
  }

  // Google Drive tools (Composio)
  if (toggles["gdrive-find"]) {
    functionDeclarations.push({
      name: "gdrive_find_file",
      description:
        "Search files in the connected Google Drive by name. Returns matching files with their id and name.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "File name search query" },
          max_results: { type: "integer", description: "Max files to return (default 10)" },
        },
        required: ["query"],
      },
    });
  }

  if (toggles["gdrive-get-meta"]) {
    functionDeclarations.push({
      name: "gdrive_get_file_metadata",
      description:
        "Get metadata for a Google Drive file by id, including webViewLink for opening in Drive.",
      parameters: {
        type: "object",
        properties: {
          file_id: { type: "string", description: "Google Drive file id" },
        },
        required: ["file_id"],
      },
    });
  }

  if (toggles["gdrive-download"]) {
    functionDeclarations.push({
      name: "gdrive_download_file",
      description: "Download a Drive file's content by id. Returns file content.",
      parameters: {
        type: "object",
        properties: {
          file_id: { type: "string", description: "Google Drive file id" },
          mime_type: { type: "string", description: "Optional target mime type for export" },
        },
        required: ["file_id"],
      },
    });
  }

  if (toggles["gdrive-create-text"]) {
    functionDeclarations.push({
      name: "gdrive_create_file_from_text",
      description: "Create a text file in Google Drive from raw text content.",
      parameters: {
        type: "object",
        properties: {
          name: { type: "string", description: "File name (e.g., notes.txt)" },
          content: { type: "string", description: "Text content of the file" },
          parent_id: { type: "string", description: "Optional parent folder id" },
        },
        required: ["name", "content"],
      },
    });
  }

  if (toggles["gdrive-create-folder"]) {
    functionDeclarations.push({
      name: "gdrive_create_folder",
      description: "Create a folder in Google Drive.",
      parameters: {
        type: "object",
        properties: {
          name: { type: "string", description: "Folder name" },
          parent_id: { type: "string", description: "Optional parent folder id" },
        },
        required: ["name"],
      },
    });
  }

  if (toggles["gdrive-fetch-to-canvas"]) {
    functionDeclarations.push({
      name: "gdrive_fetch_to_canvas",
      description:
        "IMPORTANT: After using gdrive_find_file to find files, ALWAYS call this tool with the file_id to display them on the canvas. This is the final step to show files to the user. Use the file_id returned by gdrive_find_file.",
      parameters: {
        type: "object",
        properties: {
          file_id: { type: "string", description: "Google Drive file id to fetch onto the canvas (get this from gdrive_find_file results)" },
        },
        required: ["file_id"],
      },
    });
  }

  if (toggles["canvas-list-files"]) {
    functionDeclarations.push({
      name: "canvas_list_files",
      description:
        "List all files currently visible on the user's canvas. Returns canvas_id (use this for grouping), name, and type. IMPORTANT: Use the 'canvas_id' field when grouping files, NOT 'drive_file_id'.",
      parameters: {
        type: "object",
        properties: {},
      },
    });
  }

  if (toggles["canvas-group-files"]) {
    functionDeclarations.push({
      name: "canvas_group_files",
      description:
        "Group specific files on the canvas into a named context. Use after listing files. The context is stored in persistent memory for later recall by coding agents. IMPORTANT: file_ids must be the 'canvas_id' values from canvas_list_files, NOT 'drive_file_id'.",
      parameters: {
        type: "object",
        properties: {
          file_ids: {
            type: "array",
            items: { type: "string" },
            description: "Array of canvas_id values (from canvas_list_files) to group together (minimum 2)",
          },
          context_name: {
            type: "string",
            description: "A short, descriptive name for this context group (2-5 words)",
          },
        },
        required: ["file_ids"],
      },
    });
  }

  // Return in Gemini's expected format
  return functionDeclarations.length > 0 ? [{ functionDeclarations }] : [];
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function floatTo16BitPCM(input: Float32Array): DataView {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return new DataView(output.buffer);
}
