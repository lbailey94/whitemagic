import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { ArrowRight } from "lucide-react";

export const metadata = {
  title: "Work — WhiteMagic Labs",
  description: "Case studies from client engagements.",
};

export default function WorkPage() {
  return (
    <>
      <PageHeader
        eyebrow="Work"
        title="Case studies — coming soon."
        lede="Client engagements produce case studies, which land here. Until the first handful are complete and publishable, you're seeing the honest version of this page."
      />
      <section className="container-site py-16">
        <div className="mx-auto max-w-prose rounded-2xl border border-border bg-surface-alt p-8 text-muted">
          <p className="mb-5">
            Currently booking the first engagements for 2026. Rather than
            manufacture fictional case studies, this page stays minimal
            until there&apos;s real work to document — with client
            permission.
          </p>
          <p className="mb-5">
            For a preview of what client work will look like, see:
          </p>
          <ul className="mb-5 list-disc pl-5">
            <li>
              <Link
                href="/open-source"
                className="text-lavender underline underline-offset-4 hover:text-lavender-dark"
              >
                Open-source work
              </Link>{" "}
              — the codebases that power every engagement
            </li>
            <li>
              <Link
                href="/writing"
                className="text-lavender underline underline-offset-4 hover:text-lavender-dark"
              >
                Writing
              </Link>{" "}
              — technical posts, architecture breakdowns, post-mortems
            </li>
          </ul>
          <Link href="/contact" className="btn-primary">
            Be the first case study
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
