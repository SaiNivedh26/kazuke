import { lazy, Suspense, useRef, useState, useCallback, useEffect, useMemo } from "react";
import {
  Link2,
  Mic,
  MicOff,
  BookOpen,
  ChevronDown,
  Check,
  X,
  Plus,
  Minus,
  Monitor,
  Camera,
  CameraOff,
  MousePointer2,
  Group,
  Pencil,
} from "lucide-react";
import { VoiceAura, type AuraState } from "./VoiceAura";
import { ToolsDrawer } from "./ToolsDrawer";
import { KnowledgeGraphDialog } from "./KnowledgeGraphDialog";
import { ContextGroupBadge, type ContextGroup } from "./ContextGroupBadge";
import { ContextGroupOverlay } from "./ContextGroupOverlay";
import { ContextAnalysisLoader } from "./ContextAnalysisLoader";
import { StatefulButton } from "./ui/stateful-button";
import { useGeminiLive, type ToolToggles, type GeminiMessage } from "@/hooks/useGeminiLive";
import addFilesSvg from "@/assets/add_files.svg";
import docReadySvg from "@/assets/doc_ready.svg";
import loadingLottieData from "@/assets/loading_lottie.json";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

const TldrawCanvas = lazy(() => import("./TldrawCanvas"));
const LottieLoader = lazy(() => import("./LottieLoader"));

type Upload = {
  id: string;
  x: number;
  y: number;
  status: "loading" | "ready";
  fileName?: string;
  webViewLink?: string;
  fileId?: string;
  mimeType?: string;
};

const AURA_CYCLE: AuraState[] = ["connecting", "listening", "speaking", "thinking"];
const STATE_LABELS: Record<AuraState, string> = {
  connecting: "Connecting…",
  listening: "Listening",
  speaking: "Speaking",
  thinking: "Thinking…",
};

export function CanvasWorkspace() {
  const [toolToggles, setToolToggles] = useState<ToolToggles>(() => {
    const initial: ToolToggles = {};
    // Default all tools to true
    const toolIds = [
      "cognee-remember",
      "cognee-batch-remember",
      "cognee-cognify",
      "cognee-recall",
      "cognee-forget",
      "cognee-update",
      "cognee-delete",
      "notion-search",
      "notion-create-page",
      "notion-append",
      "notion-get-page",
      "slack-send",
      "slack-list",
      "gmail-fetch",
      "gmail-send",
      "calendar-get",
      "calendar-create",
      "calendar-delete",
      "gdrive-find",
      "gdrive-get-meta",
      "gdrive-download",
      "gdrive-create-text",
      "gdrive-create-folder",
      "gdrive-fetch-to-canvas",
      "canvas-list-files",
      "canvas-group-files",
    ];
    for (const id of toolIds) {
      initial[id] = true;
    }
    return initial;
  });

  const [status, setStatus] = useState<"success" | "failure">("success");
  const [linkCount, setLinkCount] = useState(2);
  const [muted, setMuted] = useState(true);
  const [cameraOn, setCameraOn] = useState(false);
  const [screenSharing, setScreenSharing] = useState(false);
  const [kbActive, setKbActive] = useState(false);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [dragging, setDragging] = useState<string | null>(null);
  const [previewUpload, setPreviewUpload] = useState<Upload | null>(null);
  const [selectedFileIds, setSelectedFileIds] = useState<Set<string>>(new Set());
  const [selectMode, setSelectMode] = useState(false);
  const [contextGroups, setContextGroups] = useState<ContextGroup[]>([]);
  const [groupingState, setGroupingState] = useState<"idle" | "loading" | "success">("idle");
  const [pendingGroup, setPendingGroup] = useState<ContextGroup | null>(null);
  const [analysisBounds, setAnalysisBounds] = useState<{ x: number; y: number; width: number; height: number; count: number } | null>(null);
  const [renamingGroupId, setRenamingGroupId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const dragRef = useRef<{
    id: string;
    startX: number;
    startY: number;
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const screenIntervalRef = useRef<number | null>(null);
  const agentStateRef = useRef<AuraState>("connecting");
  const screenSharingPausedRef = useRef<boolean>(false);

  // Gemini Live hook
  const {
    connectionState,
    agentState: geminiAgentState,
    connect,
    disconnect,
    sendVideo,
    error,
  } = useGeminiLive({
    serverUrl: "http://localhost:8000",
    toolToggles,
    systemInstructions:
      "You are a helpful assistant with persistent memory via Cognee. You can see through the camera and screen sharing, and hear through the microphone. IMPORTANT: When viewing the screen, observe passively unless the user explicitly asks you to do something with what you see. Do NOT automatically search for files, take actions, or respond to text you see on screen unless the user specifically asks. Only act when the user speaks to you or gives a clear command. You have access to Google Drive tools: use gdrive_find_file to search for files, then use gdrive_fetch_to_canvas to bring them onto the canvas. When the user asks to see or open files, ALWAYS use gdrive_fetch_to_canvas after finding them. You can also see what files are on the user's canvas using canvas_list_files, and group files into named contexts using canvas_group_files. CRITICAL: Never guess or make up file names. Only search for files that are explicitly named by the user. If uncertain about a file name, ask the user to clarify. When grouping canvas files, always call canvas_list_files first.\n\nCRITICAL RETRIEVAL RULE: When the user asks about PAST actions (messages sent, emails sent, events created, files accessed, etc.), ALWAYS use cognee_recall to search for this information in persistent memory. NEVER use slack_list_channels, gmail_fetch_emails, calendar_get_events, or similar tools to retrieve historical information. All tool calls are automatically stored in Cognee with timestamps and full content. For RETRIEVAL tasks, ONLY use cognee_recall. Only use the actual tools (slack_send_message, gmail_send_email, calendar_create_event, etc.) when the user explicitly asks you to SEND or CREATE something NEW. For RECALLING or LOOKING UP past information, always use cognee_recall.",
    onMessage: (msg: GeminiMessage) => {
      console.log("Gemini message:", msg.type);
      
      // Pause screen sharing when tool calls happen
      if (msg.type === "tool_call") {
        screenSharingPausedRef.current = true;
        console.log("📹 Pausing screen sharing due to tool call");
      }
      
      // Resume screen sharing after turn is complete
      if (msg.type === "turn_complete") {
        screenSharingPausedRef.current = false;
        console.log("📹 Resuming screen sharing after turn complete");
      }
      
      if (msg.type === "tool_result" && msg.data?.name === "gdrive_fetch_to_canvas") {
        const result = msg.data?.result;
        console.log("[gdrive_fetch_to_canvas] Full result:", JSON.stringify(result, null, 2));
        
        const meta = result?.result && typeof result.result === "object" ? result.result : result;
        console.log("[gdrive_fetch_to_canvas] Extracted meta:", JSON.stringify(meta, null, 2));
        
        const fileName = meta?.name ?? "Fetched file";
        const webViewLink = meta?.webViewLink ?? meta?.display_url;
        const fileId = meta?.id;
        const mimeType = meta?.mimeType;
        
        console.log("[gdrive_fetch_to_canvas] Extracted fields:", { fileName, webViewLink, fileId, mimeType });
        
        const rect = canvasRef.current?.getBoundingClientRect();
        const w = rect?.width ?? window.innerWidth;
        const h = rect?.height ?? window.innerHeight;
        const id = `fetch-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        const x = 200 + Math.random() * Math.max(200, w - 500);
        const y = 160 + Math.random() * Math.max(200, h - 400);
        setUploads((u) => [
          ...u,
          { id, x, y, status: "loading", fileName, webViewLink, fileId, mimeType },
        ]);
        setTimeout(() => {
          setUploads((u) => u.map((up) => (up.id === id ? { ...up, status: "ready" } : up)));
        }, 1800);
      }
      if (msg.type === "tool_result" && msg.data?.name === "canvas_group_files") {
        const result = msg.data?.result;
        if (result && !result.error) {
          const newGroup: ContextGroup = {
            id: result.context_id,
            name: result.context_name,
            fileIds: result.file_ids || [],
            color: GROUP_COLORS[contextGroups.length % GROUP_COLORS.length],
            createdAt: Date.now(),
          };
          setContextGroups((prev) => [...prev, newGroup]);
        }
      }
    },
    onError: (err: Error) => {
      console.error("Gemini error:", err);
      setStatus("failure");
    },
  });

  // Keep agentStateRef in sync with the hook's agent state
  useEffect(() => {
    agentStateRef.current = geminiAgentState;
  }, [geminiAgentState]);

  // Update status based on connection state
  useEffect(() => {
    if (connectionState === "connected") {
      setStatus("success");
    } else if (connectionState === "error") {
      setStatus("failure");
    }
  }, [connectionState]);

  // Sync canvas files to server for agent tool access
  useEffect(() => {
    const readyFiles = uploads
      .filter((u) => u.status === "ready")
      .map((u) => ({
        id: u.id,
        fileName: u.fileName,
        fileId: u.fileId,
        mimeType: u.mimeType,
      }));
    fetch("http://localhost:8000/api/canvas/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ files: readyFiles }),
    }).catch(() => {});
  }, [uploads]);

  // Use Gemini's agent state when connected, otherwise use local state
  const agentState = connectionState === "connected" ? geminiAgentState : "connecting";

  // Handle toggle updates from ToolsDrawer
  const handleToggleChange = useCallback((id: string, checked: boolean) => {
    setToolToggles((prev) => ({ ...prev, [id]: checked }));
  }, []);

  // Screen sharing functions
  const startScreenSharing = useCallback(() => {
    if (typeof navigator === "undefined" || !("mediaDevices" in navigator)) {
      console.error("Screen sharing not supported");
      return;
    }

    navigator.mediaDevices
      .getDisplayMedia({ video: true })
      .then((stream) => {
        screenStreamRef.current = stream;
        setScreenSharing(true);

        // Create a video element to capture frames
        const video = document.createElement("video");
        video.srcObject = stream;
        video.play();

        // Wait for video to be ready before capturing
        video.onloadedmetadata = () => {
          console.log("Screen sharing video loaded");

          // Capture frames at 1 frame every 3 seconds, but only when agent is listening and not paused
          screenIntervalRef.current = window.setInterval(() => {
            // Only send frames when agent is in listening state and screen sharing is not paused
            if (video.readyState === video.HAVE_ENOUGH_DATA && agentStateRef.current === "listening" && !screenSharingPausedRef.current) {
              const canvas = document.createElement("canvas");
              canvas.width = 1280;
              canvas.height = 720;
              const ctx = canvas.getContext("2d");
              if (ctx) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                canvas.toBlob((blob) => {
                  if (blob) {
                    blob.arrayBuffer().then((buffer) => {
                      console.log("Sending screen frame to Gemini");
                      sendVideo(buffer);
                    });
                  }
                }, "image/jpeg", 0.7);
              }
            }
          }, 3000);
        };

        // Handle stream ending (user clicks "Stop sharing")
        stream.getVideoTracks()[0].onended = () => {
          stopScreenSharing();
        };
      })
      .catch((err) => {
        console.error("Screen sharing error:", err);
      });
  }, [sendVideo]);

  const stopScreenSharing = useCallback(() => {
    if (screenIntervalRef.current) {
      clearInterval(screenIntervalRef.current);
      screenIntervalRef.current = null;
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
    }
    setScreenSharing(false);
  }, []);

  // Cleanup screen sharing on unmount
  useEffect(() => {
    return () => {
      if (screenIntervalRef.current) {
        clearInterval(screenIntervalRef.current);
      }
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    const w = rect?.width ?? window.innerWidth;
    const h = rect?.height ?? window.innerHeight;

    Array.from(files).forEach((file, i) => {
      const id = `${Date.now()}-${i}-${Math.random().toString(36).slice(2, 7)}`;
      const x = 200 + Math.random() * Math.max(200, w - 500);
      const y = 160 + Math.random() * Math.max(200, h - 400);
      setUploads((u) => [...u, { id, x, y, status: "loading" }]);

      // Upload to Google Drive via the backend, then resolve the item with metadata.
      const formData = new FormData();
      formData.append("file", file);
      fetch("http://localhost:8000/api/gdrive/upload", { method: "POST", body: formData })
        .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
        .then((data) => {
          const meta = data?.result && typeof data.result === "object" ? data.result : data;
          setUploads((u) =>
            u.map((up) =>
              up.id === id
                ? {
                    ...up,
                    status: "ready",
                    fileName: meta?.name ?? file.name,
                    webViewLink: meta?.webViewLink ?? meta?.display_url,
                    fileId: meta?.id,
                    mimeType: meta?.mimeType ?? file.type,
                  }
                : up,
            ),
          );
        })
        .catch((err) => {
          console.error("Drive upload failed:", err);
          setUploads((u) =>
            u.map((up) =>
              up.id === id
                ? { ...up, status: "ready", fileName: file.name, mimeType: file.type }
                : up,
            ),
          );
        });
    });
  };

  const removeUpload = (id: string) => {
    setUploads((u) => u.filter((up) => up.id !== id));
    setSelectedFileIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const toggleFileSelection = (id: string, multiSelect: boolean) => {
    setSelectedFileIds((prev) => {
      const next = new Set(prev);
      if (multiSelect) {
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
      } else {
        if (next.has(id) && next.size === 1) {
          next.clear();
        } else {
          next.clear();
          next.add(id);
        }
      }
      return next;
    });
  };

  const GROUP_COLORS = ["#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#3B82F6", "#EF4444"];

  const calculateGroupBounds = (fileIds: string[]) => {
    const groupFiles = uploads.filter((u) => fileIds.includes(u.id));
    if (groupFiles.length === 0) return null;
    const minX = Math.min(...groupFiles.map((f) => f.x));
    const minY = Math.min(...groupFiles.map((f) => f.y));
    const maxX = Math.max(...groupFiles.map((f) => f.x + 96));
    const maxY = Math.max(...groupFiles.map((f) => f.y + 96));
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  };

  const handleGroupFiles = async () => {
    if (selectedFileIds.size < 2) return;
    const fileIds = Array.from(selectedFileIds);
    
    const groupFiles = uploads.filter((u) => fileIds.includes(u.id));
    const minX = Math.min(...groupFiles.map((f) => f.x));
    const minY = Math.min(...groupFiles.map((f) => f.y));
    const maxX = Math.max(...groupFiles.map((f) => f.x + 96));
    const maxY = Math.max(...groupFiles.map((f) => f.y + 96));
    
    setAnalysisBounds({ x: minX, y: minY, width: maxX - minX, height: maxY - minY, count: fileIds.length });
    setGroupingState("loading");
    
    try {
      const fileData = groupFiles.map((f) => ({
        id: f.id,
        name: f.fileName,
        fileId: f.fileId,
        mimeType: f.mimeType,
      }));

      const response = await fetch("http://localhost:8000/api/context/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ files: fileData }),
      });

      if (!response.ok) throw new Error("Failed to create context");
      
      const data = await response.json();
      const contextName = data.context_name || `Context ${contextGroups.length + 1}`;
      
      const newGroup: ContextGroup = {
        id: data.context_id || `group-${Date.now()}`,
        name: contextName,
        fileIds,
        color: GROUP_COLORS[contextGroups.length % GROUP_COLORS.length],
        createdAt: Date.now(),
      };

      setPendingGroup(newGroup);
      setAnalysisBounds(null);
      setGroupingState("success");
      
      setTimeout(() => {
        setContextGroups((prev) => [...prev, newGroup]);
        setSelectedFileIds(new Set());
        setSelectMode(false);
        setGroupingState("idle");
        setPendingGroup(null);
      }, 1500);
    } catch (err) {
      console.error("Group creation failed:", err);
      setAnalysisBounds(null);
      setGroupingState("idle");
    }
  };

  const handleRenameContext = async (groupId: string) => {
    if (!renameValue.trim()) {
      setRenamingGroupId(null);
      return;
    }
    try {
      await fetch("http://localhost:8000/api/context/rename", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context_id: groupId, name: renameValue.trim() }),
      });
      setContextGroups((prev) =>
        prev.map((g) => (g.id === groupId ? { ...g, name: renameValue.trim() } : g)),
      );
    } catch (err) {
      console.error("Rename failed:", err);
    }
    setRenamingGroupId(null);
    setRenameValue("");
  };

  const handleAgentGroupFiles = useCallback(async (fileIds: string[], contextName?: string) => {
    try {
      const response = await fetch("http://localhost:8000/api/canvas/group", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, context_name: contextName }),
      });
      if (!response.ok) throw new Error("Agent group failed");
      const data = await response.json();
      
      const newGroup: ContextGroup = {
        id: data.context_id,
        name: data.context_name,
        fileIds,
        color: GROUP_COLORS[contextGroups.length % GROUP_COLORS.length],
        createdAt: Date.now(),
      };
      setContextGroups((prev) => [...prev, newGroup]);
      return data;
    } catch (err) {
      console.error("Agent group error:", err);
      return { error: (err as Error).message };
    }
  }, [contextGroups.length]);

  const removeContextGroup = (groupId: string) => {
    setContextGroups((prev) => prev.filter((g) => g.id !== groupId));
  };

  const handleDragStart = (id: string, clientX: number, clientY: number) => {
    const up = uploads.find((u) => u.id === id);
    if (!up) return;
    dragRef.current = {
      id,
      startX: clientX,
      startY: clientY,
      offsetX: clientX - up.x,
      offsetY: clientY - up.y,
    };
    setDragging(id);
  };

  const handleDragMove = useCallback((clientX: number, clientY: number) => {
    if (!dragRef.current) return;
    const { id, offsetX, offsetY } = dragRef.current;
    setUploads((u) =>
      u.map((up) => (up.id === id ? { ...up, x: clientX - offsetX, y: clientY - offsetY } : up)),
    );
  }, []);

  const handleDragEnd = () => {
    dragRef.current = null;
    setDragging(null);
  };

  // Handle mic toggle - connects/disconnects Gemini
  const handleMicToggle = () => {
    if (connectionState === "connected") {
      disconnect();
    } else {
      connect();
    }
  };

  const statusDot =
    status === "success"
      ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.7)]"
      : "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.7)]";

  return (
    <div
      ref={canvasRef}
      className="fixed inset-0 bg-background overflow-hidden"
      onMouseMove={(e) => handleDragMove(e.clientX, e.clientY)}
      onMouseUp={handleDragEnd}
      onMouseLeave={handleDragEnd}
      onTouchMove={(e) => {
        const t = e.touches[0];
        if (t) handleDragMove(t.clientX, t.clientY);
      }}
      onTouchEnd={handleDragEnd}
    >
      <Suspense fallback={<div className="absolute inset-0 bg-muted animate-pulse" />}>
        <TldrawCanvas />
      </Suspense>

      {/* Upload overlays — draggable */}
      <div className="absolute inset-0 z-30 pointer-events-none">
        {uploads.map((u) => {
          const isSelected = selectedFileIds.has(u.id);
          const group = contextGroups.find((g) => g.fileIds.includes(u.id));
          return (
            <div
              key={u.id}
              className={`absolute pointer-events-auto ${dragging === u.id ? "z-50 cursor-grabbing" : "cursor-grab"} ${selectMode ? "cursor-pointer" : ""}`}
              style={{ left: u.x, top: u.y, width: 96, height: 96 }}
              title={u.status === "ready" ? (u.fileName ?? "Uploaded file") : undefined}
              onClick={(e) => {
                if (selectMode && u.status === "ready") {
                  e.stopPropagation();
                  toggleFileSelection(u.id, e.shiftKey || e.metaKey);
                }
              }}
              onDoubleClick={(e) => {
                if (!selectMode && u.status === "ready" && u.webViewLink) {
                  e.preventDefault();
                  setPreviewUpload(u);
                }
              }}
              onMouseDown={(e) => {
                if (!selectMode) {
                  e.preventDefault();
                  handleDragStart(u.id, e.clientX, e.clientY);
                }
              }}
              onTouchStart={(e) => {
                if (!selectMode) {
                  const t = e.touches[0];
                  if (t) handleDragStart(u.id, t.clientX, t.clientY);
                }
              }}
            >
              {u.status === "loading" ? (
                <Suspense fallback={null}>
                  <LottieLoader data={loadingLottieData} />
                </Suspense>
              ) : (
                <div className={`relative group ${isSelected ? "ring-2 ring-primary ring-offset-2 ring-offset-background rounded-lg" : ""}`}>
                  <img
                    src={docReadySvg}
                    alt={u.fileName ?? "Document ready"}
                    className="w-24 h-24 drop-shadow-lg pointer-events-none"
                  />
                  {group && (
                    <div
                      className="absolute -top-1 -left-1 w-4 h-4 rounded-full border-2 border-background"
                      style={{ backgroundColor: group.color }}
                    />
                  )}
                  {u.fileName && (
                    <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 max-w-[160px] truncate text-[10px] font-medium text-muted-foreground bg-card/90 border border-border rounded px-1.5 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      {u.fileName}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeUpload(u.id);
                    }}
                    className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-background border border-border shadow flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Context group overlays */}
      {contextGroups.map((group) => {
        const bounds = calculateGroupBounds(group.fileIds);
        if (!bounds) return null;
        return (
          <ContextGroupOverlay
            key={group.id}
            group={group}
            bounds={bounds}
          />
        );
      })}

      {/* Context group badges */}
      {contextGroups.map((group) => {
        const bounds = calculateGroupBounds(group.fileIds);
        if (!bounds) return null;
        const isRenaming = renamingGroupId === group.id;
        return (
          <div
            key={group.id}
            className="absolute z-40 pointer-events-auto"
            style={{ left: bounds.x + bounds.width / 2 - 70, top: bounds.y - 48 }}
          >
            {isRenaming ? (
              <div className="flex items-center gap-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
                <input
                  autoFocus
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRenameContext(group.id);
                    if (e.key === "Escape") { setRenamingGroupId(null); setRenameValue(""); }
                  }}
                  className="h-7 w-32 rounded-full bg-card/95 backdrop-blur-md border px-3 text-xs font-medium text-foreground outline-none focus:border-primary"
                  style={{ borderColor: group.color }}
                  placeholder="New name..."
                />
                <button
                  type="button"
                  onClick={() => handleRenameContext(group.id)}
                  className="h-6 w-6 rounded-full bg-emerald-500/20 text-emerald-500 grid place-items-center hover:bg-emerald-500/30 transition-colors"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  type="button"
                  onClick={() => { setRenamingGroupId(null); setRenameValue(""); }}
                  className="h-6 w-6 rounded-full bg-destructive/10 text-destructive grid place-items-center hover:bg-destructive/20 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <ContextGroupBadge
                group={group}
                x={0}
                y={0}
                onRemove={() => removeContextGroup(group.id)}
                onClick={() => {
                  setRenamingGroupId(group.id);
                  setRenameValue(group.name);
                }}
              />
            )}
          </div>
        );
      })}

      {/* Pending group badge (during creation) */}
      {pendingGroup && (() => {
        const bounds = calculateGroupBounds(pendingGroup.fileIds);
        if (!bounds) return null;
        return (
          <>
            <ContextGroupOverlay group={pendingGroup} bounds={bounds} />
            <ContextGroupBadge
              group={pendingGroup}
              x={bounds.x + bounds.width / 2 - 50}
              y={bounds.y - 40}
            />
          </>
        );
      })()}

      {/* Analysis loader (during Gemini analysis) */}
      {analysisBounds && (
        <ContextAnalysisLoader
          x={analysisBounds.x}
          y={analysisBounds.y}
          width={analysisBounds.width}
          height={analysisBounds.height}
          fileCount={analysisBounds.count}
          color={GROUP_COLORS[contextGroups.length % GROUP_COLORS.length]}
        />
      )}

      {/* Group action button */}
      {selectMode && selectedFileIds.size >= 2 && (
        <div className="absolute top-20 left-1/2 -translate-x-1/2 z-50">
          <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-card/95 backdrop-blur-md border border-border shadow-lg">
            <span className="text-sm font-medium text-foreground">
              {selectedFileIds.size} files selected
            </span>
            <StatefulButton
              state={groupingState}
              onClick={handleGroupFiles}
              loadingText="Analyzing..."
              successText="Grouped!"
            >
              <Group className="w-4 h-4" />
              Group into context
            </StatefulButton>
            <button
              type="button"
              onClick={() => {
                setSelectedFileIds(new Set());
                setSelectMode(false);
              }}
              className="h-8 w-8 rounded-lg grid place-items-center hover:bg-destructive/10 hover:text-destructive transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Top: Connection Status */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-40">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="group flex items-center gap-3 h-11 rounded-full bg-card/95 backdrop-blur-md border border-border pl-4 pr-3 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.15)] hover:shadow-[0_6px_28px_-4px_rgba(0,0,0,0.2)] hover:border-primary/40 active:scale-[0.98] transition-all"
            >
              <span className={`h-2 w-2 rounded-full ${statusDot} transition-all`} aria-hidden />
              <span className="text-sm font-semibold text-foreground tracking-tight">
                Connection
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                  status === "success"
                    ? "bg-emerald-500/10 text-emerald-600"
                    : "bg-red-500/10 text-red-600"
                }`}
              >
                {status === "success" ? "Connected" : "Failure"}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground transition-colors" />
              <div className="h-6 w-px bg-border mx-1" />
              <div className="flex items-center gap-1.5 pr-1">
                <Link2 className="w-4 h-4 text-primary" />
                <span className="text-sm font-bold text-foreground tabular-nums min-w-[1ch]">
                  {linkCount}
                </span>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="center" className="w-64" sideOffset={8}>
            <DropdownMenuLabel className="text-xs uppercase tracking-wider text-muted-foreground">
              Status
            </DropdownMenuLabel>
            <DropdownMenuItem onClick={() => setStatus("success")} className="gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="flex-1">Success</span>
              {status === "success" && <Check className="w-4 h-4 text-emerald-600" />}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setStatus("failure")} className="gap-2">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              <span className="flex-1">Failure</span>
              {status === "failure" && <Check className="w-4 h-4 text-red-600" />}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs uppercase tracking-wider text-muted-foreground">
              Connected clients
            </DropdownMenuLabel>
            <div className="flex items-center justify-between px-2 py-2">
              <button
                type="button"
                onClick={() => setLinkCount((n) => Math.max(0, n - 1))}
                className="h-8 w-8 grid place-items-center rounded-md border border-border bg-background hover:bg-accent active:scale-95 transition"
                aria-label="Decrease clients"
              >
                <Minus className="w-3.5 h-3.5" />
              </button>
              <span className="text-2xl font-bold tabular-nums">{linkCount}</span>
              <button
                type="button"
                onClick={() => setLinkCount((n) => n + 1)}
                className="h-8 w-8 grid place-items-center rounded-md border border-border bg-background hover:bg-accent active:scale-95 transition"
                aria-label="Increase clients"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Bottom-left: KnowledgeBase button */}
      <div className="absolute bottom-6 left-6 z-40">
        <button
          type="button"
          onClick={() => setKbActive((v) => !v)}
          className={`inline-flex items-center gap-2 h-11 px-5 rounded-full font-semibold text-sm border shadow-[0_4px_20px_-4px_rgba(0,0,0,0.15)] hover:shadow-[0_6px_28px_-4px_rgba(0,0,0,0.2)] active:scale-[0.98] transition-all backdrop-blur-md ${
            kbActive
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-card/95 text-foreground border-border hover:border-primary/40"
          }`}
        >
          <BookOpen className="w-4 h-4" />
          KnowledgeBase
          {kbActive && (
            <span className="ml-1 h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          )}
        </button>
      </div>

      {/* Bottom-center: voice aura + mic + upload + screen share */}
      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 rounded-2xl bg-card/95 backdrop-blur-md border border-border p-2 pl-3 shadow-[0_8px_30px_-8px_rgba(0,0,0,0.2)]">
        <button
          type="button"
          className="relative group"
          aria-label={`Agent state: ${agentState}`}
          title={STATE_LABELS[agentState]}
        >
          <VoiceAura size={72} color="#1FD5F9" state={agentState} />
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] font-medium text-muted-foreground whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            {STATE_LABELS[agentState]}
          </span>
        </button>

        <button
          type="button"
          onClick={handleMicToggle}
          className={`h-12 w-12 rounded-xl grid place-items-center text-white shadow-md active:scale-95 transition-all ${
            connectionState === "connected"
              ? "bg-emerald-500 hover:bg-emerald-600"
              : connectionState === "connecting"
                ? "bg-yellow-500 hover:bg-yellow-600"
                : "bg-red-500 hover:bg-red-600"
          }`}
          aria-label={connectionState === "connected" ? "Disconnect" : "Connect"}
        >
          {connectionState === "connected" ? (
            <Mic className="w-5 h-5" />
          ) : (
            <MicOff className="w-5 h-5" />
          )}
        </button>

        <div className="h-8 w-px bg-border" />

        <button
          type="button"
          onClick={() => {
            setSelectMode((v) => !v);
            setSelectedFileIds(new Set());
          }}
          className={`h-12 w-12 rounded-xl grid place-items-center shadow-sm active:scale-95 transition-all ${
            selectMode
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-background border border-border hover:border-primary/40 hover:bg-accent"
          }`}
          aria-label="Toggle select mode"
        >
          <MousePointer2 className="w-5 h-5" />
        </button>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="h-12 w-12 rounded-xl grid place-items-center bg-background border border-border hover:border-primary/40 hover:bg-accent shadow-sm active:scale-95 transition-all"
          aria-label="Upload files"
        >
          <img src={addFilesSvg} alt="" className="w-6 h-6" />
        </button>

        <button
          type="button"
          onClick={() => {
            if (screenSharing) {
              stopScreenSharing();
            } else {
              startScreenSharing();
            }
          }}
          className={`h-12 w-12 rounded-xl grid place-items-center shadow-sm active:scale-95 transition-all ${
            screenSharing
              ? "bg-red-500 text-white border-red-500 hover:bg-red-600"
              : "bg-background border border-border hover:border-primary/40 hover:bg-accent"
          }`}
          aria-label={screenSharing ? "Stop screen sharing" : "Share screen"}
        >
          <Monitor className="w-5 h-5" />
        </button>

        <button
          type="button"
          onClick={() => setCameraOn((v) => !v)}
          className={`h-12 w-12 rounded-xl grid place-items-center shadow-sm active:scale-95 transition-all ${
            cameraOn
              ? "bg-emerald-500 text-white border-emerald-500 hover:bg-emerald-600"
              : "bg-background border border-border hover:border-primary/40 hover:bg-accent"
          }`}
          aria-label={cameraOn ? "Turn camera off" : "Turn camera on"}
        >
          {cameraOn ? (
            <Camera className="w-5 h-5" />
          ) : (
            <CameraOff className="w-5 h-5 text-foreground" />
          )}
        </button>

        <ToolsDrawer toggles={toolToggles} onToggleChange={handleToggleChange} />

        <KnowledgeGraphDialog
          open={kbActive}
          onOpenChange={setKbActive}
          serverUrl="http://localhost:8000"
        />

        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {previewUpload && (
        <div className="fixed inset-0 z-[9999] bg-black/75 flex items-center justify-center p-8" onClick={() => setPreviewUpload(null)}>
          <div className="relative w-full h-full max-w-6xl max-h-[90vh] bg-card rounded-xl overflow-hidden shadow-2xl flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/50">
              <span className="text-sm font-medium truncate max-w-[80%]">{previewUpload.fileName}</span>
              <button
                type="button"
                onClick={() => setPreviewUpload(null)}
                className="h-8 w-8 rounded-lg grid place-items-center hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            {previewUpload.fileId && previewUpload.mimeType?.startsWith("image/") ? (
              <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-muted/20">
                <img
                  src={`https://drive.google.com/thumbnail?id=${previewUpload.fileId}&sz=w1200`}
                  alt={previewUpload.fileName}
                  className="max-w-full max-h-full object-contain rounded-lg shadow-lg"
                />
              </div>
            ) : previewUpload.fileId ? (
              <iframe
                src={`https://drive.google.com/file/d/${previewUpload.fileId}/preview`}
                className="flex-1 w-full border-0"
                title={previewUpload.fileName}
                allow="autoplay"
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                Preview not available
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
