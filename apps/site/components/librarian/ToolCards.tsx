/**
 * Rich cards rendered inline in the Librarian chat in response to tool
 * calls. One component per ToolResult `kind`; <ToolResultCard /> is the
 * dispatcher.
 */

import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  XCircle,
  Clock,
  Tag,
} from "lucide-react";
import type { Service } from "@/lib/data/services";
import type { PricingTier } from "@/lib/data/pricing";
import type { Capability } from "@/lib/data/platform";
import type { TimelineEntry } from "@/components/timeline-data";

type UnknownResult = { kind: string; data: unknown };

export function ToolResultCard({ result }: { result: UnknownResult | null }) {
  if (!result || typeof result !== "object" || !("kind" in result)) return null;
  switch (result.kind) {
    case "service_detail":
      return <ServiceCard service={result.data as Service | null} />;
    case "service_list":
      return <ServiceListCard services={result.data as Service[]} />;
    case "pricing_tier":
      return <PricingCard tier={result.data as PricingTier | null} />;
    case "pricing_list":
      return <PricingListCard tiers={result.data as PricingTier[]} />;
    case "platform_capability":
      return <CapabilityCard cap={result.data as Capability | null} />;
    case "platform_search":
      return <CapabilityListCard caps={result.data as Capability[]} />;
    case "timeline_matches":
      return (
        <TimelineCard
          data={
            result.data as { query: string; entries: TimelineEntry[]; total: number }
          }
        />
      );
    case "booking_initiated":
      return (
        <BookingCard
          data={
            result.data as {
              tierName: string;
              tierSlug: string;
              checkoutUrl: string;
              isStripe: boolean;
              topic: string;
            }
          }
        />
      );
    case "contact_submitted":
      return (
        <ContactSubmittedCard
          data={
            result.data as { reference: string; topic: string; summary: string }
          }
        />
      );
    case "error":
      return <ErrorCard message={(result.data as { message: string }).message} />;
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Shared styling
// ---------------------------------------------------------------------------

function CardFrame({
  tone = "default",
  children,
}: {
  tone?: "default" | "accent" | "success" | "danger";
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    default: "border-border-light bg-surface",
    accent: "border-lavender/30 bg-lavender/5",
    success: "border-emerald-400/40 bg-emerald-50/40 dark:bg-emerald-950/20",
    danger: "border-red-400/40 bg-red-50/40 dark:bg-red-950/20",
  };
  return (
    <div className={`my-2 overflow-hidden rounded-lg border ${tones[tone]} p-4`}>
      {children}
    </div>
  );
}

function CardLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-lavender">
      {children}
    </p>
  );
}

function CardTitle({
  href,
  children,
}: {
  href?: string;
  children: React.ReactNode;
}) {
  if (href) {
    return (
      <Link
        href={href}
        className="font-head text-base font-semibold text-ink hover:text-lavender"
      >
        {children}
      </Link>
    );
  }
  return (
    <h4 className="font-head text-base font-semibold text-ink">{children}</h4>
  );
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

function ServiceCard({ service }: { service: Service | null }) {
  if (!service) {
    return <ErrorCard message="Service not found." />;
  }
  return (
    <CardFrame tone="accent">
      <CardLabel>Service</CardLabel>
      <CardTitle href={service.path}>{service.name}</CardTitle>
      <p className="mb-3 mt-1 text-sm leading-relaxed text-fg">
        {service.oneLiner}
      </p>
      <div className="mb-3 grid gap-2 text-xs text-muted sm:grid-cols-2">
        <div className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5" />
          <span>{service.typicalDuration}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Tag className="h-3.5 w-3.5" />
          <span>{service.startingPrice}</span>
        </div>
      </div>
      <p className="mb-1 text-xs font-medium text-fg">What you get:</p>
      <ul className="mb-3 space-y-1 text-xs text-muted">
        {service.whatYouGet.slice(0, 3).map((item, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-lavender">—</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <Link
        href={service.path}
        className="inline-flex items-center gap-1 text-xs font-medium text-lavender hover:underline"
      >
        Full details <ArrowRight className="h-3 w-3" />
      </Link>
    </CardFrame>
  );
}

function ServiceListCard({ services }: { services: Service[] }) {
  return (
    <CardFrame>
      <CardLabel>Services</CardLabel>
      <div className="space-y-2">
        {services.map((s) => (
          <Link
            key={s.slug}
            href={s.path}
            className="block rounded border border-border-light/60 p-2 hover:border-lavender/40 hover:bg-surface-alt"
          >
            <p className="font-head text-sm font-semibold text-ink">
              {s.name}
            </p>
            <p className="mt-0.5 text-xs text-muted">{s.oneLiner}</p>
          </Link>
        ))}
      </div>
    </CardFrame>
  );
}

// ---------------------------------------------------------------------------
// Pricing
// ---------------------------------------------------------------------------

function PricingCard({ tier }: { tier: PricingTier | null }) {
  if (!tier) return <ErrorCard message="Pricing tier not found." />;
  return (
    <CardFrame tone={tier.featured ? "accent" : "default"}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <CardLabel>Pricing tier{tier.featured ? " · featured" : ""}</CardLabel>
          <CardTitle href="/pricing">{tier.name}</CardTitle>
        </div>
        <div className="text-right">
          <p className="font-head text-lg font-semibold text-ink">
            {tier.price}
          </p>
          <p className="text-[10px] text-muted">{tier.priceNote}</p>
        </div>
      </div>
      <p className="mb-3 text-sm leading-relaxed text-fg">{tier.oneLiner}</p>
      <p className="mb-1 text-xs font-medium text-fg">Includes:</p>
      <ul className="mb-3 space-y-1 text-xs text-muted">
        {tier.whatIsIncluded.slice(0, 4).map((item, i) => (
          <li key={i} className="flex gap-1.5">
            <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-lavender" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <div className="flex items-center gap-3">
        <Link
          href="/pricing"
          className="text-xs font-medium text-lavender hover:underline"
        >
          All tiers →
        </Link>
      </div>
    </CardFrame>
  );
}

function PricingListCard({ tiers }: { tiers: PricingTier[] }) {
  return (
    <CardFrame>
      <CardLabel>Pricing tiers</CardLabel>
      <div className="space-y-2">
        {tiers.map((t) => (
          <div
            key={t.slug}
            className={`rounded border p-2 ${t.featured ? "border-lavender/40 bg-lavender/5" : "border-border-light/60"}`}
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="font-head text-sm font-semibold text-ink">
                {t.name}
                {t.featured && (
                  <span className="ml-1.5 text-[10px] font-medium text-lavender">
                    · featured
                  </span>
                )}
              </p>
              <p className="font-head text-sm font-semibold text-ink">
                {t.price}
              </p>
            </div>
            <p className="mt-0.5 text-xs text-muted">{t.oneLiner}</p>
          </div>
        ))}
      </div>
      <Link
        href="/pricing"
        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-lavender hover:underline"
      >
        Full pricing page <ArrowRight className="h-3 w-3" />
      </Link>
    </CardFrame>
  );
}

// ---------------------------------------------------------------------------
// Platform capability
// ---------------------------------------------------------------------------

function CapabilityCard({ cap }: { cap: Capability | null }) {
  if (!cap) return <ErrorCard message="Capability not found." />;
  return (
    <CardFrame tone="accent">
      <CardLabel>
        Platform capability{cap.status !== "shipped" && ` · ${cap.status}`}
      </CardLabel>
      <CardTitle>{cap.name}</CardTitle>
      <p className="mb-2 mt-1 text-sm leading-relaxed text-fg">{cap.oneLiner}</p>
      <p className="mb-1 text-xs font-medium text-fg">What it is:</p>
      <p className="mb-2 text-xs leading-relaxed text-muted">{cap.what}</p>
      <p className="mb-1 text-xs font-medium text-fg">Why:</p>
      <p className="mb-2 text-xs leading-relaxed text-muted">{cap.why}</p>
      {cap.shipped && (
        <p className="text-[10px] text-muted">Shipped: {cap.shipped}</p>
      )}
      {cap.maps_to && cap.maps_to.length > 0 && (
        <p className="mt-1 text-[10px] text-muted">
          Maps to: {cap.maps_to.join(" · ")}
        </p>
      )}
    </CardFrame>
  );
}

function CapabilityListCard({ caps }: { caps: Capability[] }) {
  if (caps.length === 0) return <ErrorCard message="No capabilities matched." />;
  return (
    <CardFrame>
      <CardLabel>Matching capabilities</CardLabel>
      <div className="space-y-2">
        {caps.map((c) => (
          <div
            key={c.slug}
            className="rounded border border-border-light/60 p-2"
          >
            <p className="font-head text-sm font-semibold text-ink">{c.name}</p>
            <p className="mt-0.5 text-xs text-muted">{c.oneLiner}</p>
          </div>
        ))}
      </div>
    </CardFrame>
  );
}

// ---------------------------------------------------------------------------
// Timeline
// ---------------------------------------------------------------------------

function TimelineCard({
  data,
}: {
  data: { query: string; entries: TimelineEntry[]; total: number };
}) {
  if (data.entries.length === 0) {
    return (
      <ErrorCard message={`No timeline entries match "${data.query}".`} />
    );
  }
  return (
    <CardFrame>
      <CardLabel>
        Timeline · {data.total} match{data.total === 1 ? "" : "es"} for &ldquo;
        {data.query}&rdquo;
      </CardLabel>
      <div className="space-y-2">
        {data.entries.map((e, i) => (
          <div
            key={`${e.date}-${i}`}
            className="rounded border border-border-light/60 p-2"
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="font-head text-sm font-semibold text-ink">
                {e.title}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-widest text-lavender">
                {e.monthLabel}
              </p>
            </div>
            <p className="mt-0.5 text-xs leading-relaxed text-muted">
              {e.description}
            </p>
            {e.gap && (
              <p className="mt-1 text-[10px] font-medium text-lavender">
                {e.gap}
              </p>
            )}
          </div>
        ))}
      </div>
      {data.total > data.entries.length && (
        <Link
          href="/timeline"
          className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-lavender hover:underline"
        >
          View full timeline ({data.total} total)
          <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </CardFrame>
  );
}

// ---------------------------------------------------------------------------
// Booking + contact
// ---------------------------------------------------------------------------

function BookingCard({
  data,
}: {
  data: {
    tierName: string;
    tierSlug: string;
    checkoutUrl: string;
    isStripe: boolean;
    topic: string;
  };
}) {
  return (
    <CardFrame tone="accent">
      <CardLabel>
        {data.isStripe ? "Booking · ready to pay" : "Booking · via contact form"}
      </CardLabel>
      <CardTitle>{data.tierName}</CardTitle>
      <p className="mb-2 mt-1 text-sm leading-relaxed text-fg">
        Topic on file:{" "}
        <span className="italic text-muted">&ldquo;{data.topic}&rdquo;</span>
      </p>
      <p className="mb-3 text-xs text-muted">
        {data.isStripe
          ? "Click through to complete payment — Lucas will email you within 2 business hours to schedule."
          : "Click through to the contact form — Lucas will reach out within 1 business day."}
      </p>
      <a
        href={data.checkoutUrl}
        target={data.checkoutUrl.startsWith("http") ? "_blank" : undefined}
        rel={
          data.checkoutUrl.startsWith("http") ? "noopener noreferrer" : undefined
        }
        className="inline-flex items-center gap-1.5 rounded-md bg-lavender px-3 py-1.5 text-xs font-medium text-white hover:bg-lavender/90"
      >
        {data.isStripe ? "Continue to checkout" : "Continue to contact form"}
        <ExternalLink className="h-3 w-3" />
      </a>
    </CardFrame>
  );
}

function ContactSubmittedCard({
  data,
}: {
  data: { reference: string; topic: string; summary: string };
}) {
  return (
    <CardFrame tone="success">
      <CardLabel>Contact request submitted</CardLabel>
      <p className="mb-2 text-sm leading-relaxed text-fg">
        <CheckCircle2 className="mr-1.5 inline h-4 w-4 text-emerald-600" />
        Lucas will be in touch. Your reference is{" "}
        <span className="font-mono text-xs">{data.reference}</span>.
      </p>
      <div className="mt-2 border-t border-border-light/50 pt-2 text-xs text-muted">
        <p>
          <span className="font-medium text-fg">Topic:</span> {data.topic}
        </p>
        <p className="mt-1">
          <span className="font-medium text-fg">Summary:</span>{" "}
          <span className="italic">
            {data.summary.length > 160
              ? data.summary.slice(0, 160) + "…"
              : data.summary}
          </span>
        </p>
      </div>
    </CardFrame>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <CardFrame tone="danger">
      <div className="flex items-start gap-2 text-sm text-fg">
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
        <span>{message}</span>
      </div>
    </CardFrame>
  );
}
