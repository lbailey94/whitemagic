import type { ComparisonRow } from "@/lib/data/governance";
export function ComparisonTable({ rows, leftLabel, rightLabel }: { rows: ComparisonRow[]; leftLabel: string; rightLabel: string }) {
  return (<section className="border-t border-border-light bg-surface-alt py-16"><div className="container-site mx-auto max-w-3xl">
    <h2 className="font-head text-2xl font-semibold text-ink">{leftLabel} vs {rightLabel}</h2>
    <p className="mt-2 text-muted">WhiteMagic shipped governance on <strong className="text-fg">Feb 7, 2026</strong> — four weeks before Microsoft AGT (Mar 4, 2026).</p>
    <div className="mt-8 overflow-hidden rounded-2xl border border-border"><table className="w-full text-sm"><thead>
      <tr className="border-b border-border bg-surface">
        <th className="px-5 py-3 text-left font-mono text-xs uppercase tracking-wider text-dim">Feature</th>
        <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-lavender">{leftLabel}</th>
        <th className="px-5 py-3 text-center font-mono text-xs uppercase tracking-wider text-dim">{rightLabel}</th>
      </tr></thead><tbody>
      {rows.map((row, i) => (<tr key={row.feature} className={i % 2 === 0 ? "bg-surface/50" : "bg-transparent"}>
        <td className="px-5 py-3 text-ink">{row.feature}</td>
        <td className="px-5 py-3 text-center font-mono text-sm text-lavender">{row.wm}</td>
        <td className="px-5 py-3 text-center font-mono text-sm text-muted">{row.msft}</td>
      </tr>))}
    </tbody></table></div>
  </div></section>);
}