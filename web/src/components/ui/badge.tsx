import { cn } from "@/lib/utils";

const LAYER_COLORS: Record<string, string> = {
  core: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  intelligence: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  extension: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  production: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface LayerBadgeProps {
  layer: string;
  children: React.ReactNode;
  className?: string;
}

export function LayerBadge({ layer, children, className }: LayerBadgeProps) {
  return (
    <span className={cn("inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium", LAYER_COLORS[layer], className)}>
      {children}
    </span>
  );
}
