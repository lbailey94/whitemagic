/**
 * /zodiac — Interactive 12-core zodiac visualization
 *
 * 12 WhiteMagic coordination personas grouped by element (fire, earth,
 * air, water) and mode (cardinal, fixed, mutable). Each sign links to
 * its MCP endpoint (gana name) and shows its capabilities.
 *
 * v22.2.3: zodiac_list_cores / zodiac_activate_core / zodiac_consult_council
 * bridge functions now work end-to-end. See /mcp-bridge.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Prose } from "@/components/Prose";
import ZodiacCoreActivator from "@/components/ZodiacCoreActivator";
import {
  ELEMENT_COLORS,
  MODE_LABELS,
  ZODIAC_SIGNS,
  type Element,
  type Mode,
  type ZodiacSign,
} from "@/lib/data/zodiac-signs";
import { WM_FACTS } from "@/lib/facts";

export const metadata: Metadata = {
  title: "Zodiac Cores — WhiteMagic Labs",
  description:
    `The 12 WhiteMagic coordination personas — element, mode, ruler, capabilities, MCP endpoint. Part of the ${WM_FACTS.callableTools}-tool substrate.`,
};

const ELEMENTS: Element[] = ["fire", "earth", "air", "water"];
const MODES: Mode[] = ["cardinal", "fixed", "mutable"];

function SignCard({ sign }: { sign: ZodiacSign }) {
  const colors = ELEMENT_COLORS[sign.element];
  return (
    <div
      className={`group rounded-lg border ${colors.border} ${colors.bg} p-4 transition hover:scale-[1.02] hover:shadow-lg hover:shadow-${sign.element === "fire" ? "red" : sign.element === "earth" ? "emerald" : sign.element === "air" ? "sky" : "indigo"}-500/10`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl leading-none">{sign.symbol}</span>
          <div>
            <div className={`font-mono text-sm font-semibold ${colors.text}`}>
              {sign.name}
            </div>
            <div className="font-mono text-[10px] text-fg/50">
              {sign.dateRange}
            </div>
          </div>
        </div>
        {sign.availability === "live" ? (
          <span className="font-mono text-[9px] uppercase tracking-widest text-emerald-400 border border-emerald-500/30 rounded px-1.5 py-0.5">
            live
          </span>
        ) : (
          <span className="font-mono text-[9px] uppercase tracking-widest text-fg/30 border border-fg/10 rounded px-1.5 py-0.5">
            planned
          </span>
        )}
      </div>

      <div className="text-xs text-fg/60 mb-3 italic">{sign.quality}</div>

      <p className="text-xs text-fg/80 mb-3 leading-relaxed">
        {sign.description}
      </p>

      <div className="space-y-1.5 text-[11px] font-mono">
        <div className="flex justify-between">
          <span className="text-fg/40">ruler</span>
          <span className="text-fg/70">{sign.ruler}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-fg/40">polarity</span>
          <span className="text-fg/70">{sign.polarity}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-fg/40">MCP</span>
          <Link
            href="/api/manifest.json"
            className={`${colors.text} hover:underline`}
          >
            {sign.mcpEndpoint}
          </Link>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-fg/5">
        <div className="text-[9px] text-fg/40 mb-1.5 uppercase tracking-wider">
          capabilities
        </div>
        <div className="flex flex-wrap gap-1">
          {sign.capabilities.map((c) => (
            <span
              key={c}
              className="font-mono text-[10px] text-fg/60 bg-fg/5 border border-fg/10 rounded px-1.5 py-0.5"
            >
              {c}
            </span>
          ))}
        </div>
      </div>

      <ZodiacCoreActivator sign={sign} />
    </div>
  );
}

function ElementColumn({ element }: { element: Element }) {
  const colors = ELEMENT_COLORS[element];
  const signs = ZODIAC_SIGNS.filter((s) => s.element === element);
  return (
    <div>
      <div
        className={`mb-4 rounded-lg border ${colors.border} bg-gradient-to-br ${colors.gradient} p-3`}
      >
        <div className={`font-mono text-xs uppercase tracking-widest ${colors.text}`}>
          {element}
        </div>
        <div className="font-mono text-[10px] text-fg/50">
          {signs.length} sign{signs.length === 1 ? "" : "s"}
        </div>
      </div>
      <div className="space-y-3">
        {signs.map((s) => (
          <SignCard key={s.id} sign={s} />
        ))}
      </div>
    </div>
  );
}

export default function ZodiacPage() {
  return (
    <>
      <PageHeader
        eyebrow="Coordination substrate"
        title="Twelve cores."
        lede="The 12 WhiteMagic zodiac cores — stable coordination personas that route work across the substrate. Each sign is an element × mode combination with a distinct capability vector and a planetary ruler."
      />

      <section className="container-site pb-12">
        <Prose className="mx-auto">
          <p className="text-fg/80">
            The 12 cores are the public surface of the zodiac coordination
            layer. Each sign maps to a Gana (the actual tool surface — 28
            Ganas cover all 12). Aries and Cancer are live; the other 10 are
            planned. As of v{WM_FACTS.version}, the bridge functions
            <code className="text-lavender"> zodiac_list_cores</code>,
            <code className="text-lavender"> zodiac_activate_core</code>,
            and <code className="text-lavender"> zodiac_consult_council</code>
            are importable and functional.
          </p>
          <p className="text-fg/80">
            Machine-readable catalog:{" "}
            <Link href="/api/zodiac.json" className="text-lavender underline">
              /api/zodiac.json
            </Link>
            . Cross-core workflows: <em>full_audit</em> (Virgo + Libra +
            Scorpio), <em>prescience_consensus</em> (Aquarius + Gemini +
            Aries), <em>memory_dream_cycle</em> (Taurus + Pisces + Cancer).
          </p>
        </Prose>
      </section>

      <section className="container-site pb-12">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {ELEMENTS.map((el) => (
            <ElementColumn key={el} element={el} />
          ))}
        </div>
      </section>

      <section className="container-site pb-16">
        <div className="rounded-xl border border-fg/10 bg-fg/[0.02] p-6">
          <h2 className="font-head text-xl font-semibold text-fg mb-4">
            Element × Mode matrix
          </h2>
          <p className="text-fg/70 text-sm mb-6">
            Each sign occupies a unique (element, mode) cell. The 12 cells
            together form the canonical WhiteMagic coordination grid.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="text-left p-2 font-mono text-xs text-fg/40"></th>
                  {MODES.map((m) => (
                    <th
                      key={m}
                      className="text-left p-2 font-mono text-xs text-fg/60 capitalize"
                    >
                      {m}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ELEMENTS.map((el) => (
                  <tr key={el}>
                    <td
                      className={`p-2 font-mono text-xs uppercase tracking-widest ${ELEMENT_COLORS[el].text}`}
                    >
                      {el}
                    </td>
                    {MODES.map((m) => {
                      const sign = ZODIAC_SIGNS.find(
                        (s) => s.element === el && s.mode === m,
                      );
                      if (!sign) {
                        return <td key={m} className="p-2 text-fg/30">—</td>;
                      }
                      return (
                        <td key={m} className="p-2">
                          <div
                            className={`rounded border ${ELEMENT_COLORS[el].border} ${ELEMENT_COLORS[el].bg} px-3 py-2`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-lg leading-none">
                                {sign.symbol}
                              </span>
                              <div>
                                <div
                                  className={`font-mono text-sm ${ELEMENT_COLORS[el].text}`}
                                >
                                  {sign.name}
                                </div>
                                <div className="font-mono text-[10px] text-fg/50">
                                  {sign.ruler}
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="container-site pb-24">
        <Prose className="mx-auto">
          <h2>How a session routes through the zodiac</h2>
          <p>
            When a new session is created (<code className="text-lavender">session_init</code>),
            it bootstraps through Aries (Gana Horn). Memory writes pass
            through Taurus (Gana Neck). Code review fires Virgo (Gana
            Stomach). Ethics review fires Libra. Threats are caught by
            Scorpio. Long-range plans route through Sagittarius. Policy
            stratification lives with Capricorn. Prescience lives with
            Aquarius. Dream-cycle consolidation happens in Pisces.
            Karma audit runs through Cancer.
          </p>
          <p>
            This is the same 12-step architecture the{" "}
            <Link href="/mcp-bridge" className="text-lavender underline">
              MCP bridge
            </Link>{" "}
            exposes. The static catalog here documents what the live
            coordination layer will route.
          </p>
        </Prose>
      </section>
    </>
  );
}
