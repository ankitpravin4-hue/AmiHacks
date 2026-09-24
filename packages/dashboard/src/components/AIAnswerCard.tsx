import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function AIAnswerCard({
  text,
  generated,
  className,
}: {
  text: string;
  generated: boolean;
  className?: string;
}) {
  return (
    <Card className={cn("px-5 py-4", className)}>
      <p className="text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">
        {generated ? "AI-generated · advisory" : "AI unavailable"}
      </p>
      <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-inktext">{text}</div>
    </Card>
  );
}
