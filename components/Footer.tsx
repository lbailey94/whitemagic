import Link from "next/link";
import { WIP_MODE, WIP_FOOTER } from "@/lib/wip";
import { WipScramble } from "@/components/WipScramble";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border-light py-10 text-sm text-muted">
      <div className="container-site grid gap-8 md:grid-cols-4">
        <div>
          <span className="font-head text-sm font-semibold text-ink">
            {WIP_MODE ? "WhiteMagic" : "WhiteMagic Labs"}
          </span>
          <p className="mt-2 text-xs leading-relaxed text-dim">
            <WipScramble text={WIP_FOOTER.blurb} />
          </p>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Research
          </h4>
          <ul className="space-y-2">
            {WIP_MODE ? (
              <>
                <li><Link href="/research" className="hover:text-fg">Research</Link></li>
                <li><Link href="/library" className="hover:text-fg">Library</Link></li>
                <li><Link href="/timeline" className="hover:text-fg">Timeline</Link></li>
              </>
            ) : (
              <>
                <li><Link href="/research" className="hover:text-fg">Research</Link></li>
                <li><Link href="/sphere" className="hover:text-fg">Knowledge Sphere</Link></li>
                <li><Link href="/library" className="hover:text-fg">Library</Link></li>
                <li><Link href="/timeline" className="hover:text-fg">Timeline</Link></li>
                <li><Link href="/prescience" className="hover:text-fg">Prescience</Link></li>
              </>
            )}
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            Product
          </h4>
          <ul className="space-y-2">
            {WIP_MODE ? (
              <>
                <li><Link href="/governance" className="hover:text-fg">Governance</Link></li>
                <li><Link href="/open-source" className="hover:text-fg">Open Source</Link></li>
                <li><Link href="/chat" className="hover:text-fg">Talk to Aria</Link></li>
              </>
            ) : (
              <>
                <li><Link href="/economy" className="hover:text-fg">Agent Economy</Link></li>
                <li><Link href="/governance" className="hover:text-fg">Governance</Link></li>
                <li><Link href="/pricing" className="hover:text-fg">Pricing</Link></li>
                <li><Link href="/open-source" className="hover:text-fg">Open Source</Link></li>
              </>
            )}
          </ul>
        </div>

        <div>
          <h4 className="mb-3 font-mono text-[10px] font-semibold uppercase tracking-widest text-dim">
            {WIP_MODE ? "Stay in touch" : "Company"}
          </h4>
          <ul className="space-y-2">
            {WIP_MODE ? (
              <>
                <li><Link href={WIP_FOOTER.contactHref} className="hover:text-fg">{WIP_FOOTER.contactLabel}</Link></li>
                <li><Link href="/about" className="hover:text-fg">About</Link></li>
                <li><Link href="/llms.txt" className="hover:text-fg">llms.txt</Link></li>
              </>
            ) : (
              <>
                <li><Link href="/about" className="hover:text-fg">About</Link></li>
                <li><Link href="/becoming" className="hover:text-fg">Becoming</Link></li>
                <li><Link href={WIP_FOOTER.contactHref} className="hover:text-fg">{WIP_FOOTER.contactLabel}</Link></li>
                <li><Link href="/fund" className="hover:text-fg">Fund</Link></li>
              </>
            )}
          </ul>
        </div>
      </div>

      <div className="container-site mt-8 border-t border-border-light pt-4 text-xs text-dim">
        © {new Date().getFullYear()} {WIP_MODE ? "WhiteMagic" : "WhiteMagic Labs"}
        {WIP_FOOTER.showEmail ? (
          <>
            {" · "}
            <a href="mailto:whitemagicdev@proton.me" className="hover:text-fg">
              whitemagicdev@proton.me
            </a>
          </>
        ) : null}
      </div>
    </footer>
  );
}
