import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border-light py-10 text-sm text-muted">
      <div className="container-site grid gap-8 md:grid-cols-4">
        <div>
          <span className="font-head text-sm font-semibold text-ink">WhiteMagic Labs</span>
          <p className="mt-2 text-xs leading-relaxed text-dim">
            Cognitive OS for agentic AI. Open-source governance, memory, and
            tool infrastructure.
          </p>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Research
          </h4>
          <ul className="space-y-2">
            <li><Link href="/research" className="hover:text-fg">Research</Link></li>
            <li><Link href="/sphere" className="hover:text-fg">Knowledge Sphere</Link></li>
            <li><Link href="/library" className="hover:text-fg">Library</Link></li>
            <li><Link href="/timeline" className="hover:text-fg">Timeline</Link></li>
            <li><Link href="/prescience" className="hover:text-fg">Prescience</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Product
          </h4>
          <ul className="space-y-2">
            <li><Link href="/economy" className="hover:text-fg">Agent Economy</Link></li>
            <li><Link href="/governance" className="hover:text-fg">Governance</Link></li>
            <li><Link href="/pricing" className="hover:text-fg">Pricing</Link></li>
            <li><Link href="/open-source" className="hover:text-fg">Open Source</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Company
          </h4>
          <ul className="space-y-2">
            <li><Link href="/about" className="hover:text-fg">About</Link></li>
            <li><Link href="/becoming" className="hover:text-fg">Becoming</Link></li>
            <li><Link href="/contact" className="hover:text-fg">Contact</Link></li>
            <li><Link href="/fund" className="hover:text-fg">Fund</Link></li>
          </ul>
        </div>
      </div>

      <div className="container-site mt-8 border-t border-border-light pt-4 text-xs text-dim">
        © {new Date().getFullYear()} WhiteMagic Labs
      </div>
    </footer>
  );
}
