import { PageHeader } from "@/components/PageHeader";
import { GalacticSubstrateDemo } from "@/components/GalacticSubstrateDemo";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Galactic Substrate Demo — WhiteMagic Labs",
  description:
    "Interactive demo of the galactic memory lifecycle. Create memories in-browser, classify them by importance, and watch them distribute across 5 galactic zones. All data stays local — powered by IndexedDB.",
};

export default function SubstratePage() {
  return (
    <>
      <PageHeader
        title="Galactic Substrate"
        lede="Local-first memory with 5-zone lifecycle classification"
      />

      <section className="container-site py-12">
        <div className="mx-auto mb-12 max-w-3xl">
          <p className="mb-4 text-muted">
            WhiteMagic&apos;s memory system uses a galactic lifecycle model:
            memories are classified by importance into five zones, from the
            dense Core to the sparse Far Edge. Memories are never deleted —
            they simply drift outward as their importance decays.
          </p>
          <p className="mb-4 text-muted">
            This demo runs entirely in your browser using IndexedDB. Create
            memories, set their importance, and watch the zone distribution
            shift in real time. No data leaves your device.
          </p>
          <div className="rounded-xl border border-border bg-surface-alt p-4">
            <p className="font-mono text-xs text-dim">
              The same architecture powers the WhiteMagic browser extension,
              which classifies browsing history into galactic zones with a
              Dharma audit log. The core Python system uses SQLite with the
              same 5-zone model.
            </p>
          </div>
        </div>

        <GalacticSubstrateDemo />
      </section>
    </>
  );
}
