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

// ── Singularity curve geometry ──────────────────────────────────────────
// The horizontal timeline is plotted against an exponential curve representing
// the technological-singularity ramp. Dots sit ON the curve at their month's
// computed (x, y) position; the SVG path is sampled from the same function so
// it passes through every dot exactly.
const CURVE_HEIGHT_PX = 240;
const LABEL_ROW_HEIGHT_PX = 36;
const MONTH_WIDTH_PX = 70;
const SINGULARITY_K = 2.5;
// Subtle scroll-linked vertical compression. As the user scrolls forward in
// time, the curve compresses upward (anchored at the bottom), creating a
// "zoom out into the distance" effect — the future climbs into a smaller
// vertical envelope while the early events stay anchored at baseline.
const SCROLL_ZOOM_RANGE = 0.18;

/** Y-ratio for the singularity curve at normalized time t ∈ [0, 1].
 *  Returns 1 at t=0 (oldest, bottom of curve) and 0 at t=1 (newest, top). */
function singularityY(t: number): number {
  const k = SINGULARITY_K;
  return 1 - (Math.exp(k * t) - 1) / (Math.exp(k) - 1);
}

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
  const [scrollProgress, setScrollProgress] = useState(0);
  const spineRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const months = useMemo(() => aggregate(filter), [filter]);
  const totalMonths = months.length;
  const innerWidth = totalMonths * MONTH_WIDTH_PX;

  // Compressed curve geometry derived from scroll progress (0 → 1).
  const scrollFactor = 1 - scrollProgress * SCROLL_ZOOM_RANGE;
  const effectiveCurveHeight = CURVE_HEIGHT_PX * scrollFactor;
  const curveTopOffset = CURVE_HEIGHT_PX - effectiveCurveHeight;

  // Pre-compute the SVG path through 220 sampled points of the singularity
  // function so the rendered curve passes exactly through every dot.
  const svgPath = useMemo(() => {
    const SAMPLES = 220;
    const pts: { x: number; y: number }[] = [];
    for (let i = 0; i <= SAMPLES; i++) {
      const t = i / SAMPLES;
      pts.push({ x: t * 1000, y: singularityY(t) * 240 });
    }
    const linePath = pts
      .map((p, i) =>
        i === 0
          ? `M ${p.x.toFixed(2)},${p.y.toFixed(2)}`
          : `L ${p.x.toFixed(2)},${p.y.toFixed(2)}`,
      )
      .join(" ");
    const fillPath = `${linePath} L 1000,240 L 0,240 Z`;
    return { linePath, fillPath };
  }, []);

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

  // Track horizontal scroll progress (0 → 1) for the subtle curve-compression
  // / zoom-out effect. As the user scrolls right (further into the future),
  // the curve gradually compresses upward toward the baseline.
  useEffect(() => {
    const spine = spineRef.current;
    if (!spine) return;
    const handler = () => {
      const max = spine.scrollWidth - spine.clientWidth;
      if (max <= 0) {
        setScrollProgress(0);
        return;
      }
      const next = Math.min(1, Math.max(0, spine.scrollLeft / max));
      setScrollProgress(next);
    };
    spine.addEventListener("scroll", handler, { passive: true });
    handler();
    return () => spine.removeEventListener("scroll", handler);
  }, [innerWidth]);

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

      {/* Horizontal month spine with singularity curve */}
      <div className="relative rounded-2xl border border-border-light bg-surface/70 p-4 backdrop-blur-sm md:p-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] uppercase tracking-widest text-dim">
          <span>
            ← Scroll or use ← → arrows to navigate · Click a dot to see its
            events
          </span>
          <span className="flex items-center gap-1.5 text-lavender">
            <span className="inline-block h-px w-6 bg-gradient-to-r from-lavender/0 to-lavender" />
            <span>singularity trend</span>
            <span className="text-dim">· AI capability ↑</span>
          </span>
        </div>
        <div
          ref={spineRef}
          className="scrollbar-thin relative overflow-x-auto overflow-y-hidden"
          style={{ scrollSnapType: "x proximity" }}
        >
          {/* Inner content with explicit width — month nodes are positioned
              absolutely on the curve, so the spine uses pixel coordinates
              rather than flex layout. */}
          <div
            className="relative"
            style={{
              width: `${innerWidth}px`,
              height: `${CURVE_HEIGHT_PX + LABEL_ROW_HEIGHT_PX}px`,
            }}
          >
            {/* Curve + dots layer.
                Anchored at the bottom of the curve area; height shrinks
                gradually with scroll progress (subtle zoom-out into the
                distance as the viewer moves forward in time). */}
            <div
              className="absolute left-0 right-0"
              style={{
                top: `${curveTopOffset}px`,
                height: `${effectiveCurveHeight}px`,
                transition: "top 120ms linear, height 120ms linear",
              }}
            >
              {/* Singularity trend curve — purple exponential rising through
                  the timeline. The X-axis is time (Nov 2024 → Feb 2027); the
                  Y-axis is conceptual AI capability. The curve was already
                  trending up before this window began (the early-2020s ramp
                  from GPT-3 → ChatGPT → GPT-4 → Claude 3); what we render is
                  the accelerating segment WhiteMagic operates inside. The
                  SVG path is sampled from the same exponential function as
                  the dot positions, so the curve passes exactly through
                  every node. */}
              <svg
                className="pointer-events-none absolute inset-0 h-full w-full"
                preserveAspectRatio="none"
                viewBox="0 0 1000 240"
                aria-hidden="true"
              >
                <defs>
                  <linearGradient
                    id="singularityFill"
                    x1="0%"
                    y1="0%"
                    x2="0%"
                    y2="100%"
                  >
                    <stop
                      offset="0%"
                      stopColor="rgb(157, 78, 221)"
                      stopOpacity="0.22"
                    />
                    <stop
                      offset="100%"
                      stopColor="rgb(157, 78, 221)"
                      stopOpacity="0"
                    />
                  </linearGradient>
                  <linearGradient
                    id="singularityLine"
                    x1="0%"
                    y1="0%"
                    x2="100%"
                    y2="0%"
                  >
                    <stop
                      offset="0%"
                      stopColor="rgb(157, 78, 221)"
                      stopOpacity="0.30"
                    />
                    <stop
                      offset="55%"
                      stopColor="rgb(157, 78, 221)"
                      stopOpacity="0.60"
                    />
                    <stop
                      offset="100%"
                      stopColor="rgb(157, 78, 221)"
                      stopOpacity="0.95"
                    />
                  </linearGradient>
                </defs>
                <path d={svgPath.fillPath} fill="url(#singularityFill)" />
                <path
                  d={svgPath.linePath}
                  stroke="url(#singularityLine)"
                  strokeWidth="1.8"
                  fill="none"
                  vectorEffect="non-scaling-stroke"
                />
              </svg>

              {/* Month dots — positioned absolutely ON the curve. */}
              {months.map((m, i) => (
                <MonthDot
                  key={m.key}
                  month={m}
                  monthIndex={i}
                  totalMonths={totalMonths}
                  curveHeight={effectiveCurveHeight}
                  isActive={m.key === activeKey}
                  onSelect={() => setActiveKey(m.key)}
                  registerRef={(el) => {
                    if (el) nodeRefs.current.set(m.key, el);
                    else nodeRefs.current.delete(m.key);
                  }}
                />
              ))}
            </div>

            {/* Baseline axis line at the bottom of the curve area. */}
            <div
              className="pointer-events-none absolute left-0 right-0 h-px bg-border-light"
              style={{ top: `${CURVE_HEIGHT_PX - 1}px` }}
              aria-hidden="true"
            />

            {/* Labels row — fixed below the curve. */}
            <div
              className="absolute left-0 right-0"
              style={{
                top: `${CURVE_HEIGHT_PX + 6}px`,
                height: `${LABEL_ROW_HEIGHT_PX - 6}px`,
              }}
            >
              {months.map((m, i) => {
                const xPercent =
                  totalMonths > 1 ? (i / (totalMonths - 1)) * 100 : 50;
                const isActive = m.key === activeKey;
                const empty = m.count === 0;
                return (
                  <span
                    key={m.key}
                    className={cn(
                      "absolute font-mono text-[10px] uppercase tracking-wider transition",
                      isActive
                        ? "font-semibold text-ink"
                        : empty
                          ? "text-dim/60"
                          : "text-muted",
                    )}
                    style={{
                      left: `${xPercent}%`,
                      transform: "translateX(-50%)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {m.short}
                  </span>
                );
              })}
            </div>
          </div>
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

function MonthDot({
  month,
  monthIndex,
  totalMonths,
  curveHeight,
  isActive,
  onSelect,
  registerRef,
}: {
  month: MonthAggregate;
  monthIndex: number;
  totalMonths: number;
  curveHeight: number;
  isActive: boolean;
  onSelect: () => void;
  registerRef: (el: HTMLButtonElement | null) => void;
}) {
  const empty = month.count === 0;
  const t = totalMonths > 1 ? monthIndex / (totalMonths - 1) : 0;
  const xPercent = t * 100;
  const yPx = singularityY(t) * curveHeight;

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
        "group absolute flex flex-col items-center outline-none transition focus-visible:ring-2 focus-visible:ring-lavender",
      )}
      style={{
        left: `${xPercent}%`,
        top: `${yPx}px`,
        transform: "translate(-50%, -50%)",
        transition: "top 120ms linear",
      }}
    >
      {/* Count badge above the dot */}
      <span
        className={cn(
          "mb-1 whitespace-nowrap font-mono text-[10px] font-semibold transition",
          empty && "opacity-0",
          isActive ? "text-lavender" : "text-dim group-hover:text-fg",
        )}
      >
        {month.count > 0 && month.count}
        {month.hasPin && <span className="ml-0.5 text-lavender">★</span>}
      </span>

      {/* The dot itself — positioned exactly on the curve. */}
      <span
        className={cn(
          "inline-block rounded-full shadow-sm transition",
          size,
          dotClass,
          isActive && `ring-4 ${ringClass}`,
        )}
        aria-hidden="true"
      />
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
