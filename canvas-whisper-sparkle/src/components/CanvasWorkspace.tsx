import { lazy, Suspense, useRef, useState, useCallback, useEffect } from "react";
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
} from "lucide-react";
import { VoiceAura, type AuraState } from "./VoiceAura";
import { ToolsDrawer } from "./ToolsDrawer";
import { KnowledgeGraphDialog } from "./KnowledgeGraphDialog";
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
  const [kbActive, setKbActive] = useState(false);
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [dragging, setDragging] = useState<string | null>(null);
  const [previewUpload, setPreviewUpload] = useState<Upload | null>(null);
  const dragRef = useRef<{
    id: string;
    startX: number;
    startY: number;
    offsetX: number;
    offsetY: number;
  } | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Gemini Live hook
  const {
    connectionState,
    agentState: geminiAgentState,
    connect,
    disconnect,
    error,
  } = useGeminiLive({
    serverUrl: "http://localhost:8000",
    toolToggles,
    systemInstructions:
      "You are a helpful assistant with persistent memory via Cognee. You can see through the camera and hear through the microphone. You have access to Google Drive: you can find, fetch, and read files the user references, and bring a file onto the canvas when asked.",
    onMessage: (msg: GeminiMessage) => {
      console.log("Gemini message:", msg.type);
      if (msg.type === "tool_result" && msg.data?.name === "gdrive_fetch_to_canvas") {
        const result = msg.data?.result;
        const meta = result?.result && typeof result.result === "object" ? result.result : result;
        const fileName = meta?.name ?? "Fetched file";
        const webViewLink = meta?.webViewLink ?? meta?.display_url;
        const fileId = meta?.id;
        const mimeType = meta?.mimeType;
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
        // Resolve the loading animation after a short delay to mimic fetch.
        setTimeout(() => {
          setUploads((u) => u.map((up) => (up.id === id ? { ...up, status: "ready" } : up)));
        }, 1800);
      }
    },
    onError: (err: Error) => {
      console.error("Gemini error:", err);
      setStatus("failure");
    },
  });

  // Update status based on connection state
  useEffect(() => {
    if (connectionState === "connected") {
      setStatus("success");
    } else if (connectionState === "error") {
      setStatus("failure");
    }
  }, [connectionState]);

  // Use Gemini's agent state when connected, otherwise use local state
  const agentState = connectionState === "connected" ? geminiAgentState : "connecting";

  // Handle toggle updates from ToolsDrawer
  const handleToggleChange = useCallback((id: string, checked: boolean) => {
    setToolToggles((prev) => ({ ...prev, [id]: checked }));
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
        {uploads.map((u) => (
          <div
            key={u.id}
            className={`absolute pointer-events-auto ${dragging === u.id ? "z-50 cursor-grabbing" : "cursor-grab"}`}
            style={{ left: u.x, top: u.y, width: 96, height: 96 }}
            title={u.status === "ready" ? (u.fileName ?? "Uploaded file") : undefined}
            onDoubleClick={(e) => {
              if (u.status === "ready" && u.webViewLink) {
                e.preventDefault();
                setPreviewUpload(u);
              }
            }}
            onMouseDown={(e) => {
              e.preventDefault();
              handleDragStart(u.id, e.clientX, e.clientY);
            }}
            onTouchStart={(e) => {
              const t = e.touches[0];
              if (t) handleDragStart(u.id, t.clientX, t.clientY);
            }}
          >
            {u.status === "loading" ? (
              <Suspense fallback={null}>
                <LottieLoader data={loadingLottieData} />
              </Suspense>
            ) : (
              <div className="relative group">
                <img
                  src={docReadySvg}
                  alt={u.fileName ?? "Document ready"}
                  className="w-24 h-24 drop-shadow-lg pointer-events-none"
                />
                {u.fileName && (
                  <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 max-w-[160px] truncate text-[10px] font-medium text-muted-foreground bg-card/90 border border-border rounded px-1.5 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    {u.fileName}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => removeUpload(u.id)}
                  className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-background border border-border shadow flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

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
          onClick={() => fileInputRef.current?.click()}
          className="h-12 w-12 rounded-xl grid place-items-center bg-background border border-border hover:border-primary/40 hover:bg-accent shadow-sm active:scale-95 transition-all"
          aria-label="Upload files"
        >
          <img src={addFilesSvg} alt="" className="w-6 h-6" />
        </button>

        <button
          type="button"
          onClick={() => {
            if (typeof navigator !== "undefined" && "mediaDevices" in navigator) {
              navigator.mediaDevices
                .getDisplayMedia({ video: true })
                .then(() => {})
                .catch(() => {});
            }
          }}
          className="h-12 w-12 rounded-xl grid place-items-center bg-background border border-border hover:border-primary/40 hover:bg-accent shadow-sm active:scale-95 transition-all"
          aria-label="Share screen"
        >
          <Monitor className="w-5 h-5 text-foreground" />
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
