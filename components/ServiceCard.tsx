import Link from "next/link";
import { ArrowUpRight, type LucideIcon } from "lucide-react";

export interface ServiceCardProps {
  icon: LucideIcon;
  title: string;
  blurb: string;
  priceHint?: string;
  href: string;
}

export function ServiceCard({
  icon: Icon,
  title,
  blurb,
  priceHint,
  href,
}: ServiceCardProps) {
  return (
    <Link
      href={href}
      className="group flex flex-col justify-between rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
    >
      <div>
        <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-lavender-bg text-lavender">
          <Icon className="h-5 w-5" />
        </div>
        <h3 className="mb-2 font-head text-xl font-semibold text-ink">
          {title}
        </h3>
        <p className="mb-6 text-sm leading-relaxed text-muted">{blurb}</p>
      </div>
      <div className="flex items-center justify-between border-t border-border-light pt-4">
        {priceHint ? (
          <span className="font-mono text-xs uppercase tracking-wider text-dim">
            {priceHint}
          </span>
        ) : (
          <span className="font-mono text-xs uppercase tracking-wider text-dim">
            Research collaboration
          </span>
        )}
        <ArrowUpRight className="h-4 w-4 text-muted transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-lavender" />
      </div>
    </Link>
  );
}
