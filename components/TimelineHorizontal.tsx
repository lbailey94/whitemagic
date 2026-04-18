"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/utils";
import { Reveal } from "./Reveal";
import {
  TIMELINE_DATA,
  monthRange,
  type Category,
  type TimelineEntry,
} from "./timeline-data";

type FilterKey = Category | "all";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All events" },
  { key: "whitemagic", label: "WhiteMagic" },
  { key: "industry", label: "Industry & standards" },
  { key: "regulatory", label: "Regulatory" },
];

const CAT_DOT: Record<Category, string> = {
  whitemagic: "bg-lavender",
  industry: "bg-muted",
  regulatory: "bg-lavender-dark dark:bg-lavender-light",
};

const CAT_RING: Record<Category, string> = {
  whitemagic: "ring-lavender/40",
  industry: "ring-border",
  regulatory: "ring-lavender/30",
};

const CAT_BADGE: Record<Category, string> = {
  whitemagic:
    "bg-lavender-bg text-lavender-dark dark:text-lavender border border-lavender/40",
  industry: "bg-surface-alt text-muted border border-border",
  regulatory: "bg-surface-alt text-ink border border-dashed border-lavender",
};

const CAT_LABEL: Record<Category, string> = {
  whitemagic: "WhiteMagic",
  industry: "Industry",
  regulatory: "Regulatory",
};

interface MonthAggregate {
  key: string;
  short: string;
  label: string;
  events: TimelineEntry[];
  dominant: Category | null;
  hasPin: boolean;
  count: number;
}

function aggregate(filter: FilterKey): MonthAggregate[] {
  const months = monthRange();
  const filtered =
    filter === "all"
      ? TIMELINE_DATA
      : TIMELINE_DATA.filter((e) => e.category === filter);

  const byKey = new Map<string, TimelineEntry[]>();
  for (const e of filtered) {
    if (!byKey.has(e.monthKey)) byKey.set(e.monthKey, []);
    byKey.get(e.monthKey)!.push(e);
  }

  return months.map((m) => {
    const events = byKey.get(m.key) ?? [];
    const counts: Record<Category, number> = {
      whitemagic: 0,
      industry: 0,
      regulatory: 0,
    };
    let hasPin = false;
    for (const e of events) {
      counts[e.category]++;
      if (e.pin) hasPin = true;
    }
    let dominant: Category | null = null;
    let best = 0;
    (Object.keys(counts) as Category[]).forEach((c) => {
      if (counts[c] > best) {
        best = counts[c];
        dominant = c;
      }
    });
    return {
      key: m.key,
      short: m.short,
      label: events[0]?.monthLabel ?? m.label,
      events,
      dominant,
      hasPin,
      count: events.length,
    };
  });
}

export function TimelineHorizontal() {
  const [filter, setFilter] = useState<FilterKey>("all");
  const [activeKey, setActiveKey] = useState<string>("2026-02");
  const spineRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const months = useMemo(() => aggregate(filter), [filter]);

  const counts = useMemo(() => {
    const c: Record<FilterKey, number> = {
      all: TIMELINE_DATA.length,
      whitemagic: 0,
      industry: 0,
      regulatory: 0,
    };
    for (const e of TIMELINE_DATA) c[e.category]++;
    return c;
  }, []);

  const active = months.find((m) => m.key === activeKey) ?? null;

  // If the active month has no events under current filter, fall back to the
  // nearest populated month.
  useEffect(() => {
    if (!active || active.count > 0) return;
    const populated = months.filter((m) => m.count > 0);
    if (populated.length === 0) return;
    // Pick the one with the most events (signature cluster by default)
    populated.sort((a, b) => b.count - a.count);
    setActiveKey(populated[0].key);
  }, [active, months]);

  // Scroll the active node into the center of the spine when it changes.
  useEffect(() => {
    const node = nodeRefs.current.get(activeKey);
    const spine = spineRef.current;
    if (!node || !spine) return;
    const nodeRect = node.getBoundingClientRect();
    const spineRect = spine.getBoundingClientRect();
    const delta =
      nodeRect.left -
      spineRect.left -
      spineRect.width / 2 +
      nodeRect.width / 2;
    spine.scrollBy({ left: delta, behavior: "smooth" });
  }, [activeKey]);

  const onKey = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      const populated = months.filter((m) => m.count > 0);
      const idx = populated.findIndex((m) => m.key === activeKey);
      if (idx === -1) return;
      if (e.key === "ArrowRight" && idx < populated.length - 1) {
        e.preventDefault();
        setActiveKey(populated[idx + 1].key);
      } else if (e.key === "ArrowLeft" && idx > 0) {
        e.preventDefault();
        setActiveKey(populated[idx - 1].key);
      }
    },
    [months, activeKey],
  );

  return (
    <section className="container-site py-10" onKeyDown={onKey}>
      {/* Filter pills */}
      <div className="mx-auto mb-8 flex max-w-4xl flex-wrap gap-2">
        {FILTERS.map((f) => {
          const isActive = f.key === filter;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition",
                isActive
                  ? "border-lavender bg-lavender text-white"
                  : "border-border bg-surface text-muted hover:border-lavender hover:text-fg",
              )}
            >
              <span>{f.label}</span>
              <span
                className={cn(
                  "font-mono text-[11px]",
                  isActive ? "text-white/80" : "text-dim",
                )}
              >
                {counts[f.key]}
              </span>
            </button>
          );
        })}
      </div>

      {/* Horizontal month spine */}
      <div className="relative rounded-2xl border border-border-light bg-surface/70 p-4 backdrop-blur-sm md:p-6">
        <p className="mb-3 font-mono text-[11px] uppercase tracking-widest text-dim">
          ← Scroll or use ← → arrows to navigate · Click a month to see its events
        </p>
        <div
          ref={spineRef}
          className="scrollbar-thin relative flex items-end gap-1 overflow-x-auto overflow-y-hidden pb-2 pt-12"
          style={{ scrollSnapType: "x proximity" }}
        >
          {/* Axis line */}
          <div
            className="pointer-events-none absolute left-0 right-0 top-[64px] h-px bg-border-light"
            aria-hidden="true"
          />
          {months.map((m) => (
            <MonthNode
              key={m.key}
              month={m}
              isActive={m.key === activeKey}
              onSelect={() => setActiveKey(m.key)}
              registerRef={(el) => {
                if (el) nodeRefs.current.set(m.key, el);
                else nodeRefs.current.delete(m.key);
              }}
            />
          ))}
        </div>
      </div>

      {/* Detail panel */}
      {active && active.count > 0 && (
        <div className="mt-8">
          <div className="mb-4 flex items-baseline gap-3 border-b border-border-light pb-3">
            <h2 className="font-head text-2xl font-semibold text-ink md:text-3xl">
              {active.label}
            </h2>
            <span className="font-mono text-xs uppercase tracking-wider text-dim">
              {active.count} event{active.count === 1 ? "" : "s"}
            </span>
          </div>
          <div className="space-y-4">
            {active.events.map((e, i) => (
              <Reveal
                key={`${e.date}-${e.title}`}
                as="article"
                delay={Math.min(i * 50, 250)}
                className={cn(
                  "rounded-xl border bg-surface p-5 transition",
                  e.pin
                    ? "border-lavender shadow-[0_0_0_1px_var(--lavender)]"
                    : "border-border hover:border-lavender/60",
                )}
              >
                <EventCard entry={e} />
              </Reveal>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function MonthNode({
  month,
  isActive,
  onSelect,
  registerRef,
}: {
  month: MonthAggregate;
  isActive: boolean;
  onSelect: () => void;
  registerRef: (el: HTMLButtonElement | null) => void;
}) {
  const empty = month.count === 0;
  // Dot size based on count (capped)
  const size = empty
    ? "h-2 w-2"
    : month.count >= 6
      ? "h-5 w-5"
      : month.count >= 3
        ? "h-4 w-4"
        : "h-3 w-3";
  const dotClass = empty
    ? "bg-border"
    : month.dominant
      ? CAT_DOT[month.dominant]
      : "bg-muted";
  const ringClass = month.dominant ? CAT_RING[month.dominant] : "ring-border";

  return (
    <button
      ref={registerRef}
      type="button"
      onClick={onSelect}
      title={`${month.label} — ${month.count} event${month.count === 1 ? "" : "s"}`}
      aria-label={`${month.label}, ${month.count} events. ${isActive ? "Currently selected" : "Click to view"}`}
      aria-pressed={isActive}
      className={cn(
        "group relative flex min-w-[64px] shrink-0 flex-col items-center gap-2 rounded-lg px-2 py-1 outline-none transition focus-visible:ring-2 focus-visible:ring-lavender md:min-w-[80px]",
        "scroll-snap-align-center",
      )}
      style={{ scrollSnapAlign: "center" }}
    >
      {/* Count badge above axis */}
      <span
        className={cn(
          "absolute top-0 font-mono text-[10px] font-semibold transition",
          empty && "opacity-0",
          isActive ? "text-lavender" : "text-dim group-hover:text-fg",
        )}
      >
        {month.count > 0 && month.count}
        {month.hasPin && <span className="ml-0.5 text-lavender">★</span>}
      </span>

      {/* Dot on axis */}
      <span
        className={cn(
          "mt-10 inline-block rounded-full transition",
          size,
          dotClass,
          isActive && `ring-4 ${ringClass}`,
        )}
        aria-hidden="true"
      />

      {/* Month label below axis */}
      <span
        className={cn(
          "whitespace-nowrap font-mono text-[10px] uppercase tracking-wider transition",
          isActive
            ? "font-semibold text-ink"
            : empty
              ? "text-dim/60"
              : "text-muted group-hover:text-fg",
        )}
      >
        {month.short}
      </span>
    </button>
  );
}

function EventCard({ entry }: { entry: TimelineEntry }) {
  return (
    <>
      <header className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs font-semibold uppercase tracking-wider text-ink">
          {entry.displayDate}
        </span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
            CAT_BADGE[entry.category],
          )}
        >
          {CAT_LABEL[entry.category]}
        </span>
        {entry.version && (
          <span className="font-mono text-[11px] text-dim">
            {entry.version}
          </span>
        )}
      </header>

      <h3 className="mb-1.5 font-head text-lg font-semibold leading-snug text-ink">
        {entry.title}
      </h3>
      <p className="text-sm leading-relaxed text-muted">{entry.description}</p>

      {entry.gap && (
        <p className="mt-3 inline-block rounded-full bg-lavender-bg px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider text-lavender-dark dark:text-lavender">
          {entry.gap}
        </p>
      )}

      {entry.source && (
        <p className="mt-3 text-xs text-dim">
          Source:{" "}
          {entry.source.url ? (
            <a
              href={entry.source.url}
              target="_blank"
              rel="noreferrer"
              className="text-muted underline decoration-dotted underline-offset-2 hover:text-lavender"
            >
              {entry.source.label}
            </a>
          ) : (
            <span>{entry.source.label}</span>
          )}
        </p>
      )}
    </>
  );
}
