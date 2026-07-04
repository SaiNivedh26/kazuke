import { createFileRoute } from "@tanstack/react-router";
import { CanvasWorkspace } from "@/components/CanvasWorkspace";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Voice Canvas — Annotate & Collaborate" },
      {
        name: "description",
        content:
          "Infinite annotatable canvas with voice agent, knowledge base, and drag-and-drop file uploads.",
      },
      { property: "og:title", content: "Voice Canvas" },
      {
        property: "og:description",
        content: "Infinite annotatable canvas with voice agent and file uploads.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return <CanvasWorkspace />;
}
