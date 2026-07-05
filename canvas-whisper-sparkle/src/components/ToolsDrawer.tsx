import { useState, useEffect, useRef } from "react";
import { Wrench } from "lucide-react";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

type ToolToggle = {
  id: string;
  label: string;
  description?: string;
  defaultOn: boolean;
};

const SECTIONS: {
  title: string;
  description?: string;
  tools: ToolToggle[];
}[] = [
  {
    title: "Google Grounding",
    description: "Enabling Google grounding will disable custom tools",
    tools: [{ id: "google-grounding", label: "Enable Google grounding", defaultOn: false }],
  },
  {
    title: "Custom Tools",
    tools: [
      {
        id: "show-alert",
        label: "Show Alert Box",
        description: "Display browser alerts",
        defaultOn: true,
      },
      {
        id: "add-css",
        label: "Add CSS Style",
        description: "Inject CSS styles into the page",
        defaultOn: true,
      },
    ],
  },
  {
    title: "Cognee Memory Tools",
    tools: [
      {
        id: "cognee-remember",
        label: "Remember",
        description: "Store single fact - fast, graph builds in background",
        defaultOn: true,
      },
      {
        id: "cognee-batch-remember",
        label: "Batch Remember",
        description: "Store multiple facts at once - efficient",
        defaultOn: true,
      },
      {
        id: "cognee-cognify",
        label: "Cognify",
        description: "Trigger graph rebuild after batch ops",
        defaultOn: true,
      },
      {
        id: "cognee-recall",
        label: "Recall",
        description: "Search stored memories",
        defaultOn: true,
      },
      { id: "cognee-forget", label: "Forget", description: "Remove memories", defaultOn: true },
    ],
  },
  {
    title: "Notion MCP Tools",
    tools: [
      {
        id: "notion-search",
        label: "Search",
        description: "Search Notion workspace",
        defaultOn: true,
      },
      {
        id: "notion-create-page",
        label: "Create Page",
        description: "Create new Notion page",
        defaultOn: true,
      },
      {
        id: "notion-append",
        label: "Append to Page",
        description: "Add content to existing page",
        defaultOn: true,
      },
      {
        id: "notion-get-page",
        label: "Get Page",
        description: "Read Notion page content",
        defaultOn: true,
      },
    ],
  },
  {
    title: "Composio MCP Tools (Slack, Gmail, Calendar)",
    tools: [
      {
        id: "slack-send",
        label: "Slack Send Message",
        description: "Send message to channel",
        defaultOn: true,
      },
      {
        id: "slack-list",
        label: "Slack List Channels",
        description: "List all Slack channels",
        defaultOn: true,
      },
      {
        id: "gmail-fetch",
        label: "Gmail Fetch Emails",
        description: "Read/search emails",
        defaultOn: true,
      },
      { id: "gmail-send", label: "Gmail Send Email", description: "Send email", defaultOn: true },
      {
        id: "calendar-get",
        label: "Calendar Get Events",
        description: "View calendar events",
        defaultOn: true,
      },
      {
        id: "calendar-create",
        label: "Calendar Create Event",
        description: "Schedule new event",
        defaultOn: true,
      },
      {
        id: "calendar-delete",
        label: "Calendar Delete Event",
        description: "Delete/remove event",
        defaultOn: true,
      },
    ],
  },
  {
    title: "Google Drive MCP Tools",
    tools: [
      {
        id: "gdrive-find",
        label: "Find File",
        description: "Search Drive files by name",
        defaultOn: true,
      },
      {
        id: "gdrive-get-meta",
        label: "Get File Metadata",
        description: "Get Drive file metadata + webViewLink",
        defaultOn: true,
      },
      {
        id: "gdrive-download",
        label: "Download File",
        description: "Download a Drive file by id",
        defaultOn: true,
      },
      {
        id: "gdrive-create-text",
        label: "Create Text File",
        description: "Create a text file in Drive",
        defaultOn: true,
      },
      {
        id: "gdrive-create-folder",
        label: "Create Folder",
        description: "Create a folder in Drive",
        defaultOn: true,
      },
      {
        id: "gdrive-fetch-to-canvas",
        label: "Fetch File To Canvas",
        description: "Bring a Drive file onto the canvas",
        defaultOn: true,
      },
    ],
  },
  {
    title: "Transcription Settings",
    tools: [
      {
        id: "input-transcription",
        label: "Enable input transcription",
        description: "Your speech",
        defaultOn: true,
      },
      {
        id: "output-transcription",
        label: "Enable output transcription",
        description: "Gemini responses",
        defaultOn: true,
      },
    ],
  },
];

export function ToolsDrawer({
  toggles,
  onToggleChange,
}: {
  toggles: Record<string, boolean>;
  onToggleChange: (id: string, checked: boolean) => void;
}) {
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isActive = (id: string) => toggles[id] ?? false;
  const toggle = (id: string) => onToggleChange(id, !isActive(id));

  const trigger = (
    <button
      type="button"
      className="h-12 w-12 rounded-xl grid place-items-center bg-background border border-border hover:border-primary/40 hover:bg-accent shadow-sm active:scale-95 transition-all"
      aria-label="Tools"
    >
      <Wrench className="w-5 h-5 text-foreground" />
    </button>
  );

  if (!mounted) {
    return <span className="contents">{trigger}</span>;
  }

  return (
    <Drawer
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setTimeout(() => contentRef.current?.focus(), 0);
        }
      }}
    >
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent ref={contentRef} tabIndex={-1}>
        <DrawerHeader>
          <DrawerTitle>Tools &amp; Integrations</DrawerTitle>
          <DrawerDescription>
            Enable or disable tools, memory, and transcription settings.
          </DrawerDescription>
        </DrawerHeader>
        <div className="flex-1 overflow-y-auto px-4 pb-2 max-h-[70vh]">
          <div className="space-y-6">
            {SECTIONS.map((section) => (
              <div key={section.title}>
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-foreground">{section.title}</h3>
                  {section.title === "Google Grounding" && (
                    <Badge variant="secondary" className="text-[10px]">
                      Off by default
                    </Badge>
                  )}
                </div>
                {section.description && (
                  <p className="text-xs text-muted-foreground mb-3">{section.description}</p>
                )}
                <div className="space-y-3">
                  {section.tools.map((tool) => (
                    <div
                      key={tool.id}
                      className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card/50 px-3 py-2.5"
                    >
                      <div className="flex-1 min-w-0">
                        <Label htmlFor={tool.id} className="text-sm font-medium cursor-pointer">
                          {tool.label}
                        </Label>
                        {tool.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 truncate">
                            {tool.description}
                          </p>
                        )}
                      </div>
                      <Switch
                        id={tool.id}
                        checked={isActive(tool.id)}
                        onCheckedChange={() => toggle(tool.id)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
        <DrawerFooter>
          <DrawerClose asChild>
            <Button variant="outline" className="h-[34px]">
              Close
            </Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}
