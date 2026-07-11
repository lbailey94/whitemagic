import { notFound } from "next/navigation";
import Link from "next/link";
import { SECTIONS, HEXAGRAMS, TRIGRAMS } from "@/lib/data/hexagrams";

interface Props {
  params: Promise<{ slug: string }>;
}

export default async function SectionPage({ params }: Props) {
  const { slug } = await params;
  const section = SECTIONS.find((s) => s.slug === slug);
  if (!section) notFound();

  const trigram = TRIGRAMS[section.trigram];

  return (
    <main className="container-site py-16">
      <nav className="mb-8 font-mono text-xs text-dim">
        <Link href="/becoming" className="hover:text-lavender">
          Becoming
        </Link>
        <span className="mx-1">/</span>
        <span className="text-ink">{section.name}</span>
      </nav>

      <header className="mb-10">
        <span className="font-mono text-5xl text-lavender">{trigram.symbol}</span>
        <h1 className="mt-3 font-head text-3xl font-semibold text-ink">
          {section.name}
        </h1>
        <p className="mt-2 font-mono text-sm text-muted">
          Element: {trigram.element} · Direction: {trigram.direction} · Trigram: {trigram.name}
        </p>
        <p className="mt-4 max-w-prose font-head text-xl italic text-ink">
          &ldquo;{section.question}&rdquo;
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {section.chapters.map((chNum) => {
          const hex = HEXAGRAMS[chNum];
          if (!hex) return null;
          return (
            <Link
              key={chNum}
              href={`/becoming/${chNum}`}
              className="group rounded-lg border border-border bg-surface p-4 transition hover:border-lavender"
            >
              <span className="font-mono text-2xl text-lavender">{hex.trigrams}</span>
              <span className="ml-2 font-mono text-xs text-dim">Chapter {chNum}</span>
              <h3 className="mt-2 font-head text-sm font-semibold text-ink">
                {hex.name}
              </h3>
              <p className="mt-1 font-mono text-[11px] text-muted">
                {hex.chinese}
              </p>
              <p className="mt-1 font-mono text-[11px] italic text-dim">
                {hex.guidance}
              </p>
              <div className="mt-2 font-mono text-[10px] text-dim">
                Paired with {hex.pairNumber}. {HEXAGRAMS[hex.pairNumber]?.name} ({hex.pairType})
              </div>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
