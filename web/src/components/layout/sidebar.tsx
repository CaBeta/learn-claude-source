"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LAYERS, VERSION_META } from "@/lib/constants";
import { cn } from "@/lib/utils";

const LAYER_COLORS: Record<string, string> = {
  core: "bg-blue-500",
  intelligence: "bg-emerald-500",
  extension: "bg-amber-500",
  production: "bg-red-500",
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <nav className="sticky top-20 space-y-4">
        {LAYERS.map((layer) => (
          <div key={layer.id}>
            <div className="flex items-center gap-2 mb-1.5">
              <div className={cn("h-2 w-2 rounded-full", LAYER_COLORS[layer.id])} />
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
                {layer.label}
              </span>
            </div>
            <div className="space-y-0.5">
              {layer.versions.map((vid) => {
                const meta = VERSION_META[vid];
                const href = `/learn/${vid}`;
                const isActive = pathname === href;
                return (
                  <Link
                    key={vid}
                    href={href}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                      isActive
                        ? "bg-zinc-100 font-medium dark:bg-zinc-800"
                        : "text-[var(--color-text-secondary)] hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                    )}
                  >
                    <span className="font-mono text-xs">{vid}</span>
                    <span className="truncate">{meta?.title}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
