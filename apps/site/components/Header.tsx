import Link from "next/link";
import { Wordmark } from "./Wordmark";
import { ThemeToggle } from "./ThemeToggle";
import { LangToggle } from "./LangToggle";

const NAV = [
  { href: "/services", label: "Services" },
  { href: "/pricing", label: "Pricing" },
  { href: "/ladder", label: "Ladder" },
  { href: "/timeline", label: "Timeline" },
  { href: "/economy", label: "Economy" },
  { href: "/librarian", label: "Librarian" },
  { href: "/work", label: "Work" },
  { href: "/writing", label: "Writing" },
  { href: "/open-source", label: "Open Source" },
  { href: "/about", label: "About" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border-light bg-bg/80 backdrop-blur">
      <div className="container-site flex h-16 items-center justify-between gap-4">
        <Wordmark />
        <nav className="hidden items-center gap-6 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm text-muted transition hover:text-fg"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <LangToggle />
          <ThemeToggle />
          <Link href="/contact" className="btn-primary hidden sm:inline-flex">
            Book a call
          </Link>
        </div>
      </div>
    </header>
  );
}
