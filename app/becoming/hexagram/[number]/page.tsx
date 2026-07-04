import { notFound } from "next/navigation";
import Link from "next/link";
import { HEXAGRAMS } from "@/lib/data/hexagrams";
import type { Hexagram } from "@/lib/data/hexagrams";

interface Props {
  params: Promise<{ number: string }>;
}

export default async function HexagramPage({ params }: Props) {
  const { number } = await params;
  const num = parseInt(number, 10);
  const hex = HEXAGRAMS[num];
  if (!hex) notFound();

  const paired = HEXAGRAMS[hex.pairNumber];

  return (
    <main className="container-site py-16 max-w-2xl">
      <nav className="mb-8 font-mono text-xs text-dim">
        <Link href="/becoming" className="hover:text-lavender">
          Becoming
        </Link>
        <span className="mx-1">/</span>
        <span className="text-ink">Hexagram {num}</span>
      </nav>

      <header className="mb-10">
        <span className="font-mono text-6xl leading-none text-lavender">{hex.trigrams}</span>
        <h1 className="mt-4 font-head text-3xl font-semibold text-ink">
          {num}. {hex.name}
        </h1>
        <p className="mt-1 font-mono text-lg text-lavender">
          {hex.chinese} ({hex.pinyin})
        </p>
      </header>

      <div className="space-y-6">
        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="font-mono text-xs uppercase tracking-wider text-dim">Judgment</h2>
          <p className="mt-2 font-mono text-sm italic leading-relaxed text-ink">
            {hex.judgment}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="font-mono text-xs uppercase tracking-wider text-dim">Image</h2>
          <p className="mt-2 font-mono text-sm leading-relaxed text-ink">
            {hex.image}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="font-mono text-xs uppercase tracking-wider text-dim">Guidance</h2>
          <p className="mt-2 font-mono text-sm leading-relaxed text-ink">
            {hex.guidance}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="font-mono text-xs uppercase tracking-wider text-dim">Pairing</h2>
          <p className="mt-2 font-mono text-sm text-ink">
            Paired with{" "}
            <Link
              href={`/becoming/hexagram/${paired.number}`}
              className="text-lavender hover:underline"
            >
              {paired.number}. {paired.name} ({paired.chinese})
            </Link>
          </p>
          <p className="mt-1 font-mono text-xs text-muted">
            Type: {hex.pairType === "exchange" ? "Exchange pair (錯卦 cuò guà) — total transformation" : "Inverse pair (綜卦 zōng guà) — same lines, opposite orientation"}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="font-mono text-xs uppercase tracking-wider text-dim">Canon</h2>
          <p className="mt-2 font-mono text-sm text-ink">
            {hex.upperCanon ? "Upper Canon (上經), 1–30 — cosmic principles, the outer world." : "Lower Canon (下經), 31–64 — human relationships, the inner world."}
          </p>
        </div>
      </div>

      <div className="mt-10 flex items-center justify-between">
        {num > 1 && (
          <Link
            href={`/becoming/hexagram/${num - 1}`}
            className="font-mono text-sm text-lavender hover:underline"
          >
            ← {num - 1}. {HEXAGRAMS[num - 1]?.name}
          </Link>
        )}
        {num < 64 && (
          <Link
            href={`/becoming/hexagram/${num + 1}`}
            className="ml-auto font-mono text-sm text-lavender hover:underline"
          >
            {num + 1}. {HEXAGRAMS[num + 1]?.name} →
          </Link>
        )}
      </div>
    </main>
  );
}
