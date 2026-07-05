import * as React from "react";
import type { ContextGroup } from "./ContextGroupBadge";

interface ContextGroupOverlayProps {
  group: ContextGroup;
  bounds: { x: number; y: number; width: number; height: number };
}

export function ContextGroupOverlay({ group, bounds }: ContextGroupOverlayProps) {
  const padding = 20;
  return (
    <div
      className="absolute pointer-events-none z-20 rounded-2xl transition-all duration-500 ease-out"
      style={{
        left: bounds.x - padding,
        top: bounds.y - padding,
        width: bounds.width + padding * 2,
        height: bounds.height + padding * 2,
        border: `2px dashed ${group.color}`,
        backgroundColor: `${group.color}08`,
      }}
    />
  );
}
