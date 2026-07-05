import * as React from "react";
import { cn } from "@/lib/utils";

interface ContextAnalysisLoaderProps {
  x: number;
  y: number;
  width: number;
  height: number;
  color?: string;
  fileCount: number;
}

export function ContextAnalysisLoader({
  x,
  y,
  width,
  height,
  color = "#8B5CF6",
  fileCount,
}: ContextAnalysisLoaderProps) {
  const padding = 20;
  return (
    <div
      className="absolute z-50 pointer-events-none animate-in fade-in duration-300"
      style={{
        left: x - padding,
        top: y - padding,
        width: width + padding * 2,
        height: height + padding * 2 + 48,
      }}
    >
      <div
        className="relative w-full h-full rounded-2xl overflow-hidden"
        style={{
          border: `2px dashed ${color}`,
          backgroundColor: `${color}10`,
        }}
      >
        <div
          className="absolute inset-0 animate-pulse"
          style={{ backgroundColor: `${color}08` }}
        />

        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <div className="relative">
            <div
              className="w-10 h-10 rounded-full border-2 border-t-transparent animate-spin"
              style={{ borderColor: `${color}40`, borderTopColor: "transparent" }}
            />
            <div
              className="absolute inset-1 rounded-full animate-ping opacity-30"
              style={{ backgroundColor: color }}
            />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-semibold text-foreground/80">
              Analyzing {fileCount} files
            </span>
            <span className="flex gap-0.5">
              <span className="w-1 h-1 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: "0ms" }} />
              <span className="w-1 h-1 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: "150ms" }} />
              <span className="w-1 h-1 rounded-full animate-bounce" style={{ backgroundColor: color, animationDelay: "300ms" }} />
            </span>
          </div>
          <span className="text-[10px] text-muted-foreground">
            Generating context name...
          </span>
        </div>

        <div
          className="absolute bottom-0 left-0 h-0.5 animate-progress"
          style={{ backgroundColor: color }}
        />
      </div>
    </div>
  );
}
