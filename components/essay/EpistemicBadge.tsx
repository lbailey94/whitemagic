import { epistemicColors, type EpistemicTag } from "@/lib/design-tokens";

export function EpistemicBadge({ tag }: { tag: EpistemicTag }) {
  const colors = epistemicColors[tag];
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-mono font-medium"
      style={{ backgroundColor: colors.bg, color: colors.fg }}
    >
      [{tag}]
    </span>
  );
}
