"use client";

import { usePathname } from "next/navigation";
import { Header } from "./Header";
import { Footer } from "./Footer";
import { FloatingLibrarian } from "./FloatingLibrarian";
import { HelloHuman } from "./HelloHuman";

/**
 * ConditionalChrome — shows Header/Footer/Librarian/HelloHuman
 * on all pages except the tome homepage.
 * The tome homepage ("/") provides its own navigation via TomeShell.
 */
export function ConditionalChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isTomeHome = pathname === "/";

  if (isTomeHome) {
    return <main>{children}</main>;
  }

  return (
    <div className="relative z-10">
      <Header />
      <main>{children}</main>
      <Footer />
      <FloatingLibrarian />
      <HelloHuman />
    </div>
  );
}
