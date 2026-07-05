import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

type KnowledgeGraphDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverUrl?: string;
};

export function KnowledgeGraphDialog({
  open,
  onOpenChange,
  serverUrl = "http://localhost:8000",
}: KnowledgeGraphDialogProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    setHtml(null);
    try {
      const res = await fetch(`${serverUrl}/api/cognee/visualize`, {
        method: "GET",
        headers: { Accept: "text/html" },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const text = await res.text();
      setHtml(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && html === null && !loading && !error) {
      loadGraph();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl w-[95vw] h-[85vh] p-0 gap-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-4 py-3 border-b border-border flex-row items-center justify-between space-y-0">
          <div className="flex flex-col space-y-0.5">
            <DialogTitle className="text-base">Knowledge Graph</DialogTitle>
            <DialogDescription className="text-xs">
              Cognee memory graph — live from the persistent dataset
            </DialogDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadGraph}
            disabled={loading}
            className="h-8 gap-1.5 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </DialogHeader>

        <div className="relative flex-1 bg-white">
          {loading && (
            <div className="absolute inset-0 grid place-items-center bg-background/80">
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="text-sm">Loading graph…</span>
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="absolute inset-0 grid place-items-center bg-background/80">
              <div className="flex flex-col items-center gap-3 text-center max-w-sm px-4">
                <AlertCircle className="w-8 h-8 text-destructive" />
                <div>
                  <p className="text-sm font-semibold text-foreground">Failed to load graph</p>
                  <p className="text-xs text-muted-foreground mt-1 break-words">{error}</p>
                </div>
                <Button variant="outline" size="sm" onClick={loadGraph} className="h-8 gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Try again
                </Button>
              </div>
            </div>
          )}

          {html && !loading && !error && (
            <iframe
              title="Cognee Knowledge Graph"
              srcDoc={html}
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              className="w-full h-full border-0"
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
