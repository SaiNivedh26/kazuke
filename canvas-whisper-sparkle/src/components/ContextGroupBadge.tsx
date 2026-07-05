import * as React from "react";
import { Layers, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ContextGroup = {
  id: string;
  name: string;
  fileIds: string[];
  color: string;
  createdAt: number;
};

interface ContextGroupBadgeProps {
  group: ContextGroup;
  x: number;
  y: number;
  onRemove?: () => void;
  onClick?: () => void;
}

export function ContextGroupBadge({ group, x, y, onRemove, onClick }: ContextGroupBadgeProps) {
  return (
    <div
      className="absolute z-40 pointer-events-auto animate-in fade-in slide-in-from-top-2 duration-300"
      style={{ left: x, top: y }}
    >
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-full shadow-lg border backdrop-blur-md",
          "bg-card/95 text-foreground text-xs font-semibold",
          "hover:shadow-xl transition-shadow cursor-pointer"
        )}
        style={{ borderColor: group.color }}
        onClick={onClick}
      >
        <Layers className="w-3.5 h-3.5" style={{ color: group.color }} />
        <span>{group.name}</span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full font-bold"
          style={{ backgroundColor: `${group.color}20`, color: group.color }}
        >
          {group.fileIds.length}
        </span>
        {onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="ml-1 h-4 w-4 rounded-full grid place-items-center hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
}
