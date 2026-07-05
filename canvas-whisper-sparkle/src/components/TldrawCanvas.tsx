import { Tldraw, DefaultToolbar } from "tldraw";
import "tldraw/tldraw.css";
import "./tldraw-overrides.css";

export default function TldrawCanvas() {
  return (
    <div className="absolute inset-0">
      <Tldraw
        components={{
          Toolbar: () => <DefaultToolbar orientation="vertical" />,
        }}
      />
    </div>
  );
}
