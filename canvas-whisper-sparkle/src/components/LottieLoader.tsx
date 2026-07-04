import { useEffect, useRef } from "react";
import lottie, { type AnimationItem } from "lottie-web";

// Use lottie-web directly — lottie-react's default export doesn't
// interop cleanly in this bundler chain and returns an object.
export default function LottieLoader({ data, size = 96 }: { data: unknown; size?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    let anim: AnimationItem | null = null;
    try {
      anim = lottie.loadAnimation({
        container: ref.current,
        renderer: "svg",
        loop: true,
        autoplay: true,
        animationData: data as object,
      });
    } catch (e) {
      console.error("Lottie failed to load", e);
    }
    return () => {
      anim?.destroy();
    };
  }, [data]);

  return <div ref={ref} style={{ width: size, height: size }} />;
}
