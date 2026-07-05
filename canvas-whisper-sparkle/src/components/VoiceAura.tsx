import { useEffect, useState } from "react";

export type AuraState = "connecting" | "listening" | "speaking" | "thinking";

export function VoiceAura({
  size = 96,
  color = "#1FD5F9",
  state = "listening",
}: {
  size?: number;
  color?: string;
  state?: AuraState;
}) {
  const [t, setT] = useState(0);

  useEffect(() => {
    let raf: number;
    const loop = () => {
      setT((v) => {
        const speeds: Record<AuraState, number> = {
          connecting: 0.004,
          listening: 0.008,
          speaking: 0.025,
          thinking: 0.015,
        };
        return v + (speeds[state] ?? 0.008);
      });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [state]);

  const amplitude = state === "connecting" ? 5 : 14;
  const blur = state === "connecting" ? 8 : 6;

  const blob = (offset: number, scale: number, opacity: number) => {
    const x = 50 + Math.sin(t + offset) * amplitude * scale;
    const y = 50 + Math.cos(t * 1.3 + offset) * amplitude * scale;
    return { cx: x, cy: y, opacity };
  };

  const b1 = blob(0, 1, 0.9);
  const b2 = blob(2.1, 0.8, 0.7);
  const b3 = blob(4.3, 1.1, 0.6);

  return (
    <div
      className="relative rounded-full overflow-hidden"
      style={{
        width: size,
        height: size,
        background: "radial-gradient(circle at 50% 50%, #0b2735 0%, #050b12 100%)",
        boxShadow: `0 0 30px ${color}66, inset 0 0 24px rgba(0,0,0,0.6)`,
      }}
      aria-label={`Voice aura — ${state}`}
    >
      <svg viewBox="0 0 100 100" className="absolute inset-0 w-full h-full">
        <defs>
          <radialGradient id="aura-a" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={color} stopOpacity="1" />
            <stop offset="60%" stopColor={color} stopOpacity="0.2" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </radialGradient>
          <radialGradient id="aura-b" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#7B61FF" stopOpacity="1" />
            <stop offset="70%" stopColor="#7B61FF" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="aura-c" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="80%" stopColor={color} stopOpacity="0" />
          </radialGradient>
          <filter id="aura-blur">
            <feGaussianBlur stdDeviation={blur} />
          </filter>
        </defs>
        <g filter="url(#aura-blur)">
          <circle cx={b1.cx} cy={b1.cy} r="42" fill="url(#aura-a)" opacity={b1.opacity} />
          <circle cx={b2.cx} cy={b2.cy} r="34" fill="url(#aura-b)" opacity={b2.opacity} />
          <circle cx={b3.cx} cy={b3.cy} r="22" fill="url(#aura-c)" opacity={b3.opacity} />
        </g>
      </svg>
      {state === "connecting" && (
        <div className="absolute inset-0 rounded-full border-2 border-primary/40 animate-pulse" />
      )}
    </div>
  );
}
