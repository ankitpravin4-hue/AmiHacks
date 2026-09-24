import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "ghost" | "danger" | "outline";

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>(function Button({ className, variant = "default", ...props }, ref) {
  const styles: Record<Variant, string> = {
    default: "bg-accent hover:bg-accent-dim text-white font-medium",
    ghost: "bg-transparent hover:bg-white/[0.04] text-inktext-muted hover:text-inktext",
    danger: "bg-critical hover:brightness-110 text-white font-medium",
    outline: "border border-line bg-ink-800 hover:bg-ink-700 text-inktext",
  };
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[8px] px-3 py-2 text-sm transition-colors duration-150 disabled:opacity-50",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
});
