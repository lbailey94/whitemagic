import Link from "next/link";
import { ArrowRight } from "lucide-react";

export const metadata = {
  title: "白術實驗室 — 私有 AI 部署",
  description: "為受監管的團隊提供私有 AI 部署、代理治理與 MCP 工程服務。",
};

/**
 * Chinese surface — Phase 1 stub.
 * Full translation lives here as pages are migrated. Single source of truth
 * for the 白術 wordmark and any Mandarin-first visual treatments.
 */
export default function ZhHomePage() {
  return (
    <section className="container-site py-24">
      <div className="mx-auto max-w-2xl text-center">
        <div className="mb-6 font-zh text-7xl font-bold text-lavender">
          白術
        </div>
        <p className="mb-3 font-mono text-xs uppercase tracking-widest text-lavender">
          白術實驗室 · WhiteMagic Labs
        </p>
        <h1 className="mb-6 font-zh text-4xl font-bold leading-tight text-ink md:text-5xl">
          私有 AI，部署於您的基礎設施之上。
        </h1>
        <p className="mb-10 text-lg leading-relaxed text-muted">
          中文版內容正在翻譯中。若您使用英文閱讀更為方便，請切換至英文版。
          若需直接聯繫，歡迎透過郵件。
        </p>
        <p className="mb-10 font-body text-base italic leading-relaxed text-muted">
          The Chinese surface is being translated. For now, the primary
          language is English — switch with the toggle in the top nav, or
          reach out directly by email.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/" className="btn-primary">
            English site
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="mailto:whitemagicdev@proton.me"
            className="btn-ghost"
          >
            whitemagicdev@proton.me
          </a>
        </div>
      </div>
    </section>
  );
}
