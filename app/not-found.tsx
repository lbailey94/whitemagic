import Link from "next/link";

export default function NotFound() {
  return (
    <main className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="font-head text-4xl font-bold text-ink">404</h1>
      <p className="mt-4 font-mono text-xs uppercase tracking-widest text-dim">
        This page does not exist
      </p>
      <Link
        href="/"
        className="mt-8 font-mono text-xs uppercase tracking-wide text-lavender transition hover:text-fg"
      >
        Return to sigil
      </Link>
    </main>
  );
}
