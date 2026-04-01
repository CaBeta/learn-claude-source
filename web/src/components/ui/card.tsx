import { cn } from "@/lib/utils";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={cn("rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-4", className)}>
      {children}
    </div>
  );
}
