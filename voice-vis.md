'use client';

import { useTheme } from 'next-themes';
import { useAgent } from '@livekit/components-react';
import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura';

function Demo() {
  const { state } = useAgent();
  const { resolvedTheme } = useTheme();

  return (
    <AgentAudioVisualizerAura
      size="xl"
      color="#1FD5F9"
      colorShift={0.3}
      state="speaking"
      themeMode={resolvedTheme}
      className="aspect-square size-auto w-full"
    />
  );
}
