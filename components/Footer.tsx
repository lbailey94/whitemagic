import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border-light py-10 text-sm text-muted">
      <div className="container-site grid gap-8 md:grid-cols-4">
        <div>
          <span className="font-head text-sm font-semibold text-ink">
            WhiteMagic
          </span>
          <p className="mt-2 text-xs leading-relaxed text-dim">
            Cognitive operating system for AI agents. MIT-licensed, open source, local-first.
          </p>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Product
          </h4>
          <ul className="space-y-2">
            <li><Link href="/mcp-bridge" className="hover:text-fg">Get Started</Link></li>
            <li><Link href="/pricing" className="hover:text-fg">Pricing</Link></li>
            <li><Link href="/open-source" className="hover:text-fg">Docs</Link></li>
            <li><Link href="/governance" className="hover:text-fg">Governance</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Research
          </h4>
          <ul className="space-y-2">
            <li><Link href="/research" className="hover:text-fg">Research</Link></li>
            <li><Link href="/timeline" className="hover:text-fg">Timeline</Link></li>
            <li><Link href="/performance" className="hover:text-fg">Performance</Link></li>
            <li><Link href="/library" className="hover:text-fg">Library</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Company
          </h4>
          <ul className="space-y-2">
            <li><Link href="/about" className="hover:text-fg">About</Link></li>
            <li><Link href="/contact" className="hover:text-fg">Contact</Link></li>
            <li><Link href="/fund" className="hover:text-fg">Fund</Link></li>
            <li><Link href="/llms.txt" className="hover:text-fg">llms.txt</Link></li>
          </ul>
        </div>
      </div>

      <div className="container-site mt-8 border-t border-border-light pt-4 text-xs text-dim">
        © {new Date().getFullYear()} WhiteMagic · MIT Licensed · Built by Lucas Bailey
        {" · "}
        <a href="mailto:whitemagicdev@proton.me" className="hover:text-fg">
          whitemagicdev@proton.me
        </a>
      </div>
    </footer>
  );
}
