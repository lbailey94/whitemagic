import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { WM_FACTS } from "@/lib/facts";

export const metadata = {
  title: "Writing — WhiteMagic",
  description:
    `Technical writing on private AI, agent governance, MCP engineering, and the honest lessons from shipping a ${WM_FACTS.linesShort}-line solo project.`,
};

interface Post {
  slug: string;
  title: string;
  blurb: string;
  date: string;
  cluster: "Private AI" | "Agent Governance" | "MCP" | "Strategy";
  ready: boolean;
}

const POSTS: Post[] = [
  {
    slug: "whitemagic-post-mortem",
    title: "WhiteMagic: an honest post-mortem",
    blurb:
      `Six months, ${WM_FACTS.linesLong} lines, ${WM_FACTS.testsPassing} passing tests, and a hard lesson in the difference between building a product and running a research lab. What worked, what didn't, and what I'd do differently.`,
    date: "2026-04",
    cluster: "Strategy",
    ready: false,
  },
  {
    slug: "private-ai-deployment-guide",
    title: "How I deploy private AI for regulated teams",
    blurb:
      "A concrete architecture for on-prem AI with persistent memory, tool use, governance, and audit — the kind of deployment your compliance team will actually sign off on.",
    date: "2026-04",
    cluster: "Private AI",
    ready: false,
  },
  {
    slug: "agent-governance-before-microsoft",
    title: "I built agent governance before Microsoft — here's what I learned",
    blurb:
      "In February 2026 I shipped a Dharma rules engine, Karma audit ledger, and 8-stage middleware pipeline. In April 2026 Microsoft shipped the Agent Governance Toolkit. Overlap is high. Differences matter.",
    date: "2026-04",
    cluster: "Agent Governance",
    ready: false,
  },
];

export default function WritingPage() {
  return (
    <>
      <PageHeader
        eyebrow="Writing"
        title="Technical writing, honest post-mortems."
        lede="Three clusters: private AI architecture, agent governance, and MCP engineering. Plus the occasional strategic essay when something in the market deserves a proper response."
      />
      <section className="container-site py-16">
        <ul className="mx-auto max-w-3xl space-y-4">
          {POSTS.map((post) => (
            <li key={post.slug}>
              <PostRow post={post} />
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function PostRow({ post }: { post: Post }) {
  const content = (
    <>
      <div className="mb-2 flex items-center gap-3 text-xs">
        <span className="font-mono uppercase tracking-wider text-lavender">
          {post.cluster}
        </span>
        <span className="text-dim">·</span>
        <span className="font-mono text-dim">{post.date}</span>
        {!post.ready && (
          <>
            <span className="text-dim">·</span>
            <span className="font-mono uppercase tracking-wider text-dim">
              Draft
            </span>
          </>
        )}
      </div>
      <h2 className="mb-2 font-head text-xl font-semibold text-ink">
        {post.title}
      </h2>
      <p className="text-muted">{post.blurb}</p>
    </>
  );

  if (post.ready) {
    return (
      <Link
        href={`/writing/${post.slug}`}
        className="block rounded-2xl border border-border bg-surface p-6 transition hover:border-lavender hover:bg-lavender-bg"
      >
        {content}
      </Link>
    );
  }
  return (
    <div className="rounded-2xl border border-dashed border-border bg-surface-alt/50 p-6 opacity-80">
      {content}
    </div>
  );
}
