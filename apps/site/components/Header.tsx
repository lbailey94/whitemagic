"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { Wordmark } from "./Wordmark";
import { ThemeToggle } from "./ThemeToggle";
import { LangToggle } from "./LangToggle";

const NAV = [
  { href: "/research", label: "Research" },
  { href: "/open-source", label: "Open Source" },
  { href: "/sphere", label: "Sphere" },
  { href: "/economy", label: "Economy" },
  { href: "/timeline", label: "Timeline" },
  { href: "/about", label: "About" },
];

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border-light bg-bg/80 backdrop-blur">
      <div className="container-site flex h-16 items-center justify-between gap-4">
        <Wordmark />
        <nav className="hidden items-center gap-5 xl:flex">
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
            Contact
          </Link>
          {/* Mobile hamburger */}
          <button
            className="xl:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? (
              <X className="h-5 w-5 text-fg" />
            ) : (
              <Menu className="h-5 w-5 text-fg" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile menu drawer */}
      {mobileOpen && (
        <div className="border-t border-border-light bg-bg/95 backdrop-blur xl:hidden">
          <nav className="container-site flex flex-col gap-1 py-4">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-surface-alt hover:text-fg"
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/contact"
              onClick={() => setMobileOpen(false)}
              className="btn-primary mt-2 sm:hidden"
            >
              Contact
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
