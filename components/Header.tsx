"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { Wordmark } from "./Wordmark";
import { ThemeToggle } from "./ThemeToggle";
import { LangToggle } from "./LangToggle";

const NAV = [
  { href: "/mcp-bridge", label: "Get Started" },
  { href: "/open-source", label: "Docs" },
  { href: "/pricing", label: "Pricing" },
  { href: "/governance", label: "Governance" },
  { href: "/research", label: "Research" },
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
          <Link href="/mcp-bridge" className="btn-primary hidden sm:inline-flex">
            Get Started
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
              href="/mcp-bridge"
              onClick={() => setMobileOpen(false)}
              className="btn-primary mt-2 sm:hidden"
            >
              Get Started
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
