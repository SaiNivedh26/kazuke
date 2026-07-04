import { Tldraw } from "tldraw";
import "tldraw/tldraw.css";
import "./tldraw-overrides.css";

export default function TldrawCanvas() {
  return (
    <div className="absolute inset-0 tldraw-vertical-toolbar">
      <Tldraw />
    </div>
  );
}
