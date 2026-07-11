"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tag = "div" | "li" | "section" | "article";

/**
 * One-shot scroll reveal. Adds `.is-visible` when the element enters the
 * viewport, then stops observing. Respects prefers-reduced-motion via CSS
 * in globals.css.
 */
export function Reveal({
  children,
  className,
  as = "div",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  as?: Tag;
  delay?: number;
}) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setVisible(true);
      return;
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.unobserve(entry.target);
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -60px 0px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const style = delay ? { transitionDelay: `${delay}ms` } : undefined;
  const classes = cn("reveal", visible && "is-visible", className);

  // Explicit branch per tag — React 19 + Next 15 infer refs correctly this way
  // without needing JSX.IntrinsicElements gymnastics.
  if (as === "li") {
    return (
      <li
        ref={ref as React.RefObject<HTMLLIElement>}
        style={style}
        className={classes}
      >
        {children}
      </li>
    );
  }
  if (as === "section") {
    return (
      <section
        ref={ref as React.RefObject<HTMLElement>}
        style={style}
        className={classes}
      >
        {children}
      </section>
    );
  }
  if (as === "article") {
    return (
      <article
        ref={ref as React.RefObject<HTMLElement>}
        style={style}
        className={classes}
      >
        {children}
      </article>
    );
  }
  return (
    <div
      ref={ref as React.RefObject<HTMLDivElement>}
      style={style}
      className={classes}
    >
      {children}
    </div>
  );
}
