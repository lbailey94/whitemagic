import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border-light py-10 text-sm text-muted">
      <div className="container-site grid gap-8 md:grid-cols-3">
        <div>
          <span className="font-head text-sm font-semibold text-ink">
            WhiteMagic
          </span>
          <p className="mt-2 text-xs leading-relaxed text-dim">
            Cognitive operating system for AI agents. MIT-licensed, open source, local-first.
          </p>
          <div className="mt-3 flex flex-wrap gap-3 text-xs">
            <Link href="/getting-started" className="hover:text-fg">Getting Started</Link>
            <Link href="/mcp-bridge" className="hover:text-fg">MCP Bridge</Link>
            <Link href="/open-source" className="hover:text-fg">Open Source</Link>
            <Link href="/coming-soon" className="hover:text-fg">Roadmap</Link>
          </div>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Explore
          </h4>
          <ul className="space-y-2">
            <li><Link href="/vision" className="hover:text-fg">Vision</Link></li>
            <li><Link href="/capabilities" className="hover:text-fg">Capabilities</Link></li>
            <li><Link href="/benchmarks" className="hover:text-fg">Evidence</Link></li>
            <li><Link href="/strata" className="hover:text-fg">STRATA</Link></li>
            <li><Link href="/timeline" className="hover:text-fg">Timeline</Link></li>
            <li><Link href="/research" className="hover:text-fg">Research</Link></li>
            <li><Link href="/prescience" className="hover:text-fg">Prescience</Link></li>
            <li><Link href="/ganas" className="hover:text-fg">28 Ganas</Link></li>
            <li><Link href="/grimoire" className="hover:text-fg">Grimoire</Link></li>
            <li><Link href="/substrate" className="hover:text-fg">Substrate</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Project
          </h4>
          <ul className="space-y-2">
            <li><Link href="/economy" className="hover:text-fg">Economy &amp; Services</Link></li>
            <li><Link href="/governance" className="hover:text-fg">Governance</Link></li>
            <li><Link href="/becoming" className="hover:text-fg">Becoming</Link></li>
            <li><Link href="/contact" className="hover:text-fg">Contact</Link></li>
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
