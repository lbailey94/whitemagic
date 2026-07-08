/**
 * TomePage — wrapper for each page/section in the tome.
 *
 * In scroll mode, pages stack vertically.
 * In codex mode, each page is a full-viewport snap point.
 */

interface TomePageProps {
  id: string;
  label?: string;
  children: React.ReactNode;
  className?: string;
}

export function TomePage({ id, label, children, className = "" }: TomePageProps) {
  return (
    <section
      id={id}
      data-tome-label={label || ""}
      className={`tome-page ${className}`}
    >
      {children}
    </section>
  );
}

/**
 * TomeBookHeader — standard header for a book's opening page.
 */
export function TomeBookHeader({
  roman,
  title,
  subtitle,
}: {
  roman: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-12 text-center">
      <div className="tome-ornament mb-6">❦</div>
      <p className="tome-book-subtitle">Book {roman}</p>
      <h2 className="tome-book-title">{title}</h2>
      <p className="mt-3 text-sm italic leading-relaxed text-muted">{subtitle}</p>
      <div className="tome-ornament mt-6">❦</div>
    </div>
  );
}

/**
 * TomeChapterHeading — heading for a chapter within a book.
 */
export function TomeChapterHeading({
  title,
  desc,
}: {
  title: string;
  desc?: string;
}) {
  return (
    <div className="mb-8">
      <h3 className="tome-chapter-title">{title}</h3>
      {desc && <p className="mt-1 text-sm text-muted">{desc}</p>}
    </div>
  );
}

/**
 * TomeOrnament — decorative divider between chapters.
 */
export function TomeOrnament({ symbol = "❧" }: { symbol?: string }) {
  return <div className="tome-ornament my-12">{symbol}</div>;
}
