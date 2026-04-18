import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border-light py-10 text-sm text-muted">
      <div className="container-site flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
        <div>
          <span>© {new Date().getFullYear()} WhiteMagic Labs · Lucas</span>
        </div>
        <nav className="flex flex-wrap gap-5">
          <Link href="/services" className="hover:text-fg">
            Services
          </Link>
          <Link href="/writing" className="hover:text-fg">
            Writing
          </Link>
          <Link
            href="https://github.com/whitemagic-ai"
            className="hover:text-fg"
          >
            GitHub
          </Link>
          <Link href="/contact" className="hover:text-fg">
            Contact
          </Link>
        </nav>
      </div>
    </footer>
  );
}
