import * as React from "react";
import { Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

type ButtonState = "idle" | "loading" | "success" | "error";

interface StatefulButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  state?: ButtonState;
  loadingText?: string;
  successText?: string;
  errorText?: string;
}

export function StatefulButton({
  state = "idle",
  loadingText,
  successText,
  errorText,
  children,
  className,
  disabled,
  ...props
}: StatefulButtonProps) {
  const isDisabled = disabled || state === "loading";

  const getContent = () => {
    switch (state) {
      case "loading":
        return (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            {loadingText && <span>{loadingText}</span>}
          </>
        );
      case "success":
        return (
          <>
            <Check className="w-4 h-4" />
            {successText && <span>{successText}</span>}
          </>
        );
      case "error":
        return <>{errorText || children}</>;
      default:
        return <>{children}</>;
    }
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all",
        "bg-primary text-primary-foreground hover:bg-primary/90",
        "shadow-sm active:scale-95",
        isDisabled && "opacity-70 cursor-not-allowed",
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {getContent()}
    </button>
  );
}
