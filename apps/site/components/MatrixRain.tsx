"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";

/**
 * Subtle polyglot matrix rain.
 *
 * - Fixed canvas behind all content (pointer-events:none).
 * - Theme-aware: lavender on ink (dark) or cream (light).
 * - ~12 fps throttled, DPR-scaled, pauses on tab hide.
 * - Respects prefers-reduced-motion (skips effect).
 *
 * Column layout:
 *   Column stride is wider than font size so double-width CJK / Hangul / Arabic
 *   glyphs don't bleed into adjacent columns (which created a "twinned" look
 *   in the previous version). Characters render center-aligned within their
 *   column so any residual width difference is symmetric, not a left-bias.
 *
 * Character set (deduped, single pass per glyph to avoid visible pairing):
 *   CJK hanzi (traditional + simplified), katakana, hangul, Cyrillic,
 *   Greek, Devanagari, Arabic, Hebrew, Latin, digits, binary emphasis.
 */
export function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const el = canvasRef.current;
    if (!el) return;
    const ctxMaybe = el.getContext("2d", { alpha: true });
    if (!ctxMaybe) return;

    const canvas: HTMLCanvasElement = el;
    const ctx: CanvasRenderingContext2D = ctxMaybe;

    const CHARS = Array.from(
      new Set(
        (
          // ── CJK hanzi (Chinese + shared Japanese kanji) ──
          "白術龍鳳虎龜磁氣道靈神光影陰陽水火木金土日月山川風雷雨雪石玉心意志行性命天地" +
          // ── Japanese katakana ──
          "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロ" +
          // ── Korean hangul (syllable sampler) ──
          "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호" +
          // ── Cyrillic ──
          "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ" +
          // ── Greek ──
          "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω" +
          // ── Devanagari (Sanskrit sampler) ──
          "अआइईउऊऋएऐओऔकखगघचछजझञटठडढणतथदधनपफबभमयरलवशषसह" +
          // ── Arabic (isolated letters — canvas renders these without shaping) ──
          "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" +
          "٠١٢٣٤٥٦٧٨٩" +
          // ── Hebrew ──
          "אבגדהוזחטיכלמנסעפצקרשת" +
          // ── Latin uppercase + a few lowercase for variety ──
          "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij" +
          // ── Digits + binary emphasis (single, not repeating — avoids paired appearance) ──
          "0123456789"
        ).split(""),
      ),
    );

    const FONT_SIZE = 16;
    const COLUMN_STRIDE = 22; // wider than font to accommodate double-width glyphs
    const FRAME_MS = 70; // slightly faster than the original 80
    const FADE_ALPHA = 0.12; // high enough that trails fully clear within ~1.5s
    const DROP_STEP = FONT_SIZE; // full row per frame — original cadence

    let drops: number[] = [];
    let raf = 0;
    let last = 0;
    let running = true;

    const isDark = () =>
      resolvedTheme === "dark" ||
      (resolvedTheme === "system" &&
        window.matchMedia("(prefers-color-scheme: dark)").matches);

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      // Wipe any stale pixels from prior effect runs (HMR in dev keeps the
      // canvas DOM element alive; without this clear, edits to fade logic
      // don't visually take effect until a hard refresh).
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      const columns = Math.ceil(window.innerWidth / COLUMN_STRIDE);
      drops = new Array(columns)
        .fill(0)
        .map(() => Math.random() * -window.innerHeight);
    };

    const render = (t: number) => {
      if (!running) return;
      if (t - last > FRAME_MS) {
        const dark = isDark();

        // Trail fade using destination-out composite. This actually SUBTRACTS
        // alpha from existing pixels each frame instead of painting a
        // translucent color over them. On a transparent canvas, source-over
        // fading can never reach alpha=0 — trails accumulate as permanent
        // column stripes over time. destination-out properly decays pixels
        // back to transparent, so no ghost stripes build up regardless of
        // how long the site is left open.
        ctx.globalCompositeOperation = "destination-out";
        ctx.fillStyle = `rgba(0,0,0,${FADE_ALPHA})`;
        ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);
        ctx.globalCompositeOperation = "source-over";

        ctx.fillStyle = dark
          ? "rgba(184, 169, 212, 0.42)"
          : "rgba(124, 92, 191, 0.18)";
        // Font stack includes Noto Sans fallbacks so CJK/Arabic/Devanagari
        // get rendered as proper glyphs instead of tofu. Browsers will pick
        // whatever's installed locally; failing that, the system default
        // still supplies at least one covering font on every major OS.
        ctx.font = `${FONT_SIZE}px "JetBrains Mono", "Noto Sans CJK SC", "Noto Sans Arabic", "Noto Sans Devanagari", "Noto Sans Hebrew", "Noto Sans", monospace`;

        for (let i = 0; i < drops.length; i++) {
          const ch = CHARS[Math.floor(Math.random() * CHARS.length)];
          // Center each glyph within its column stride — wide glyphs overflow
          // symmetrically instead of bleeding right into the next column.
          const x = i * COLUMN_STRIDE + COLUMN_STRIDE / 2;
          const y = drops[i];
          ctx.fillText(ch, x, y);
          if (y > window.innerHeight && Math.random() > 0.975) {
            drops[i] = 0;
          } else {
            drops[i] = y + DROP_STEP;
          }
        }
        last = t;
      }
      raf = requestAnimationFrame(render);
    };

    const onVisibility = () => {
      if (document.hidden) {
        running = false;
        cancelAnimationFrame(raf);
      } else if (!running) {
        running = true;
        last = 0;
        raf = requestAnimationFrame(render);
      }
    };

    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    raf = requestAnimationFrame(render);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [resolvedTheme]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0"
    />
  );
}
