"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { neoStore, emitGlimmer, subscribeRainToggle } from "@/store/neoStore";

/**
 * Polyglot matrix rain with pastel rainbow fade.
 *
 * - clearRect each frame for zero residue (no destination-out ghosting).
 * - High density: tight column spacing.
 * - Longer trail with gradual pastel fade.
 * - Glimmer linger: white chars freeze in place and fade while the
 *   column continues dropping beneath them.
 * - Freeze glitch: columns occasionally stall before resuming.
 * - Reads live parameters from neoStore for NEO arcade controls.
 * - Emits glimmer events for the Glimmer Tracker typewriter.
 * - DPR-scaled, pauses on tab hide, respects prefers-reduced-motion.
 */
export function MatrixRain() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [enabled, setEnabled] = useState(neoStore.rainEnabled);

  useEffect(() => {
    const unsub = subscribeRainToggle(() => setEnabled(neoStore.rainEnabled));
    return unsub;
  }, []);

  const toggle = useCallback(() => {
    neoStore.toggleRain();
  }, []);

  const openControls = useCallback(() => {
    const fn = (window as unknown as { __wmRainControlsToggle?: () => void }).__wmRainControlsToggle;
    if (fn) fn();
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const el = canvasRef.current;
    if (!el) return;
    const ctxMaybe = el.getContext("2d", { alpha: true });
    if (!ctxMaybe) return;

    const canvas: HTMLCanvasElement = el;
    let ctx: CanvasRenderingContext2D | null = ctxMaybe;

    const BASE_CHARS = Array.from(
      new Set(
        (
          "白術龍鳳虎龜磁氣道靈神光影陰陽水火木金土日月山川風雷雨雪石玉心意志行性命天地" +
          "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロ" +
          "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호" +
          "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ" +
          "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω" +
          "अआइईउऊऋएऐओऔकखगघचछजझञटठडढणतथदधनपफबभमयरलवशषसह" +
          "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" +
          "٠١٢٣٤٥٦٧٨٩" +
          "אבגדהוזחטיכלמנסעפצקרשת" +
          "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij" +
          "0123456789"
        ).split(""),
      ),
    );

    // Genetic code character set for DNA mode
    const DNA_CHARS = "ATGCUatgcuΔΨΩ∑∏∂∞≈≠≤≥←↑→↓↔⇌⇄⇅".split("");

    const FONT_SIZE = 14;

    // Read mutable params from neoStore — canvas reads these each frame
    const getParams = () => neoStore.matrixRain;

    interface GlimmerLinger {
      y: number;
      ch: string;
      hue: number;
      timer: number;
    }

    let drops: number[] = [];
    let charTimers: number[] = [];
    let freezeTimers: number[] = [];
    let glimmerLingers: (GlimmerLinger | null)[] = [];
    let columnChars: string[] = [];
    let morphStates: ({ stepsLeft: number; targetChar: string } | null)[] = [];
    let raf = 0;
    let lastFrameTime = 0;
    let running = true;
    let disposed = false;
    let hue = 0;
    let lastColumnStride = getParams().columnStride;

    const resize = () => {
      if (!ctx || disposed) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = window.innerWidth;
      const h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.clearRect(0, 0, w, h);
      const stride = getParams().columnStride;
      const columns = Math.ceil(w / stride);
      const chars = neoStore.dnaActive ? DNA_CHARS : BASE_CHARS;
      drops = new Array(columns)
        .fill(0)
        .map(() => Math.random() * -h);
      charTimers = new Array(columns).fill(0);
      freezeTimers = new Array(columns).fill(0);
      glimmerLingers = new Array(columns).fill(null);
      columnChars = new Array(columns)
        .fill("")
        .map(() => chars[Math.floor(Math.random() * chars.length)]);
      morphStates = new Array(columns).fill(null);
      lastColumnStride = stride;
    };

    const render = (currentTime: number) => {
      if (disposed || !running || !ctx) return;

      raf = requestAnimationFrame(render);

      const p = getParams();
      const fpsInterval = 1000 / p.fps;
      const elapsed = currentTime - lastFrameTime;
      if (elapsed < fpsInterval) return;
      lastFrameTime = currentTime - (elapsed % fpsInterval);
      hue = (hue + 0.15) % 360;

      const w = window.innerWidth;
      const h = window.innerHeight;

      // Resize if column stride changed via NEO controls
      if (p.columnStride !== lastColumnStride) {
        resize();
      }

      // Fade mode: gradual erase using destination-out (theme-agnostic), or clearRect for zero residue
      if (p.fadeMode > 0.5) {
        ctx.globalCompositeOperation = "destination-out";
        ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
        ctx.fillRect(0, 0, w, h);
        ctx.globalCompositeOperation = "source-over";
      } else {
        ctx.clearRect(0, 0, w, h);
      }
      ctx.font = `${FONT_SIZE}px "JetBrains Mono", "Noto Sans CJK SC", "Noto Sans Arabic", "Noto Sans Devanagari", "Noto Sans Hebrew", "Noto Sans", monospace`;

      const dna = neoStore.dnaActive;
      const activeChars = dna ? DNA_CHARS : BASE_CHARS;
      const charsLen = activeChars.length;
      const baseH = hue;
      const glimmerThreshold = dna ? p.glimmerChance * 2 : p.glimmerChance;

      // Recombination: swap adjacent columns occasionally
      if (dna && Math.random() < 0.001 && drops.length > 2) {
        const swapIdx = 1 + Math.floor(Math.random() * (drops.length - 2));
        const tmp = drops[swapIdx];
        drops[swapIdx] = drops[swapIdx + 1];
        drops[swapIdx + 1] = tmp;
      }

      for (let i = 0; i < drops.length; i++) {
        const x = i * p.columnStride + p.columnStride / 2;
        const y = drops[i];
        const colH = (baseH + i * 4) % 360;

        // Character changes at controlled rate with optional morph steps
        charTimers[i]++;
        let ch = columnChars[i] ?? activeChars[Math.floor(Math.random() * charsLen)];
        let isMorphing = false;
        if (charTimers[i] >= p.charChangeInterval && !morphStates[i]) {
          charTimers[i] = 0;
          const newChar = activeChars[Math.floor(Math.random() * charsLen)];
          if (p.morphSteps > 0) {
            morphStates[i] = { stepsLeft: p.morphSteps, targetChar: newChar };
          } else {
            columnChars[i] = newChar;
            ch = newChar;
          }
        }
        const morph = morphStates[i];
        if (morph) {
          isMorphing = true;
          ch = activeChars[Math.floor(Math.random() * charsLen)];
          morph.stepsLeft--;
          if (morph.stepsLeft <= 0) {
            columnChars[i] = morph.targetChar;
            morphStates[i] = null;
          }
        }

        // Glimmer: occasional white flash — DNA doubles the rate
        const glimmer = Math.random() < glimmerThreshold;
        if (glimmer && !glimmerLingers[i]) {
          glimmerLingers[i] = {
            y,
            ch,
            hue: colH,
            timer: p.lingerFrames,
          };
          emitGlimmer();
        }

        // Mutation flash: DNA mode occasionally colors chars red/blue
        const mutating = dna && Math.random() < 0.03;
        const leadingColor = glimmer
          ? `rgba(255,255,255,${0.75 + (charTimers[i] / p.charChangeInterval) * 0.15})`
          : mutating
            ? (Math.random() < 0.5 ? "rgba(255,100,100,0.55)" : "rgba(100,150,255,0.55)")
            : isMorphing
              ? `hsla(${colH}, 85%, 78%, 0.75)`
              : `hsla(${colH}, 70%, 65%, 0.42)`;

        ctx.fillStyle = leadingColor;
        ctx.fillText(ch, x, y);

        // Trail with hue shift — live trail length from store
        // In fade mode, the overlay handles trailing so we draw fewer manual trail chars
        const effectiveTrail = p.fadeMode > 0.5 ? Math.min(p.trailSteps, 4) : p.trailSteps;
        for (let trail = 1; trail <= effectiveTrail; trail++) {
          const trailAlpha = 0.28 - trail * 0.022;
          if (trailAlpha > 0) {
            const trailH = (colH + trail * 6) % 360;
            ctx.fillStyle = dna
              ? (Math.random() < 0.5
                ? `rgba(255,120,120,${trailAlpha})`
                : `rgba(120,180,255,${trailAlpha})`)
              : `hsla(${trailH}, 60%, 55%, ${trailAlpha})`;
            ctx.fillText(
              activeChars[Math.floor(Math.random() * charsLen)],
              x,
              y - trail * FONT_SIZE,
            );
          }
        }

        // Draw lingering glimmer at its frozen Y while it fades out
        const linger = glimmerLingers[i];
        if (linger) {
          const lingerAlpha = (linger.timer / p.lingerFrames) * 0.6;
          ctx.fillStyle = dna && Math.random() < 0.5
            ? `rgba(180,220,255,${lingerAlpha})`
            : `rgba(255,255,255,${lingerAlpha})`;
          ctx.fillText(linger.ch, x, linger.y);
          linger.timer--;
          if (linger.timer <= 0) {
            glimmerLingers[i] = null;
          }
        }

        // Freeze glitch: column stalls for a few frames before advancing
        if (freezeTimers[i] > 0) {
          freezeTimers[i]--;
        } else if (Math.random() < p.freezeChance) {
          freezeTimers[i] = 2 + Math.floor(Math.random() * 4);
        } else {
          drops[i] = y + p.dropStep;
        }

        if (y > h && Math.random() > 0.975) {
          drops[i] = 0;
          charTimers[i] = 0;
          freezeTimers[i] = 0;
          glimmerLingers[i] = null;
          columnChars[i] = activeChars[Math.floor(Math.random() * charsLen)];
          morphStates[i] = null;
        }
      }
    };

    const onVisibility = () => {
      if (document.hidden) {
        running = false;
        cancelAnimationFrame(raf);
      } else if (!running && !disposed) {
        running = true;
        lastFrameTime = performance.now();
        raf = requestAnimationFrame(render);
      }
    };

    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);
    lastFrameTime = performance.now();
    raf = requestAnimationFrame(render);

    return () => {
      disposed = true;
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // @ts-ignore
        ctx = null;
      }
    };
  }, [enabled]);

  return (
    <>
      {enabled && (
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 z-0"
        />
      )}
      <div className="fixed bottom-4 right-4 z-50 flex gap-2">
        <button
          onClick={toggle}
          aria-label={enabled ? "Disable matrix rain" : "Enable matrix rain"}
          title={enabled ? "Disable matrix rain" : "Enable matrix rain"}
          className="rounded-full border border-border bg-surface/80 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-dim backdrop-blur-sm transition hover:border-lavender hover:text-lavender"
        >
          {enabled ? (
            <span><span className="font-zh text-[9px] text-dim/50">雨</span> Rain: ON</span>
          ) : (
            <span><span className="font-zh text-[9px] text-dim/50">雨</span> Rain: OFF</span>
          )}
        </button>
        {enabled && (
          <button
            onClick={openControls}
            aria-label="Matrix rain controls"
            title="Adjust matrix rain parameters"
            className="rounded-full border border-border bg-surface/80 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-dim backdrop-blur-sm transition hover:border-lavender hover:text-lavender"
          >
            ⚙
          </button>
        )}
      </div>
    </>
  );
}
