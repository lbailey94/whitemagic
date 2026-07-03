import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Typographic wrapper for long-form content (about, services detail, writing).
 * Hand-rolled to match the Crimson Pro aesthetic — don't need @tailwindcss/typography yet.
 */
export function Prose({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "prose-custom max-w-prose font-body text-lg leading-relaxed text-fg",
        "[&_h2]:mt-12 [&_h2]:mb-4 [&_h2]:font-head [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-ink",
        "[&_h3]:mt-8 [&_h3]:mb-3 [&_h3]:font-head [&_h3]:text-xl [&_h3]:font-semibold [&_h3]:text-ink",
        "[&_p]:mb-5",
        "[&_ul]:mb-5 [&_ul]:list-disc [&_ul]:pl-6 [&_ul>li]:mb-1",
        "[&_ol]:mb-5 [&_ol]:list-decimal [&_ol]:pl-6 [&_ol>li]:mb-1",
        "[&_a]:text-lavender [&_a]:underline [&_a]:underline-offset-4 hover:[&_a]:text-lavender-dark",
        "[&_code]:font-mono [&_code]:text-base [&_code]:bg-surface-alt [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded",
        "[&_strong]:font-semibold [&_strong]:text-ink",
        "[&_blockquote]:border-l-2 [&_blockquote]:border-lavender [&_blockquote]:pl-5 [&_blockquote]:italic [&_blockquote]:text-muted",
        className,
      )}
    >
      {children}
    </div>
  );
}
