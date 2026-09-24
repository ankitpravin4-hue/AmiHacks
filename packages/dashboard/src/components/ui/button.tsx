import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "ghost" | "danger" | "outline";

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>(function Button({ className, variant = "default", ...props }, ref) {
  const styles: Record<Variant, string> = {
    default:
      "bg-sky-500/90 hover:bg-sky-400 text-ink-950 font-semibold shadow-glow",
    ghost: "bg-transparent hover:bg-white/5 text-slate-200",
    danger: "bg-critical hover:bg-rose-400 text-white font-semibold",
    outline: "border border-line bg-ink-800 hover:bg-ink-700 text-slate-100",
  };
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm transition disabled:opacity-50",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
});
