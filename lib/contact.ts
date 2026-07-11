/**
 * Contact submissions — shared store used by both:
 *   - the `/api/contact` POST route (form on /contact)
 *   - the Librarian `submit_contact_request` tool
 *
 * Both land in the same KV namespace so /admin can surface them uniformly.
 * KV schema:
 *   contact:<reference>     → JSON ContactSubmission
 *   contact:index           → JSON string[] of references (newest first, cap 200)
 *
 * No PII beyond what the visitor explicitly provided. In-memory fallback KV
 * applies when Upstash isn't configured (dev only — resets on restart).
 */

import { getKV } from "./librarian/rate-limit";
import { sendContactNotification } from "./notify";

export interface ContactSubmission {
  reference: string;
  timestamp: number;
  email: string;
  topic: string;
  summary: string;
  /** Where the submission came from (e.g. "form", "librarian"). */
  source: "form" | "librarian";
  /** Optional — present only for Librarian-sourced entries. */
  sessionId?: string;
  /** Optional — path the visitor was on. */
  pagePath?: string;
}

const INDEX_KEY = "contact:index";
const INDEX_CAP = 200;
const ENTRY_TTL_SEC = 60 * 60 * 24 * 90; // 90 days
const INDEX_TTL_SEC = 60 * 60 * 24 * 180;

function isEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

function genReference(): string {
  return `wm-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export interface StoreContactInput {
  email: string;
  topic: string;
  summary: string;
  source: ContactSubmission["source"];
  sessionId?: string;
  pagePath?: string;
}

export interface StoreContactResult {
  ok: boolean;
  reference?: string;
  error?: string;
}

/**
 * Validate + persist a contact submission. Pure-ish (KV writes happen best
 * effort; failures are logged but do not surface to the caller as errors
 * beyond a boolean).
 */
export async function storeContactRequest(
  input: StoreContactInput,
): Promise<StoreContactResult> {
  const email = input.email.trim().toLowerCase();
  const topic = input.topic.trim();
  const summary = input.summary.trim();

  if (!isEmail(email)) return { ok: false, error: "Invalid email address." };
  if (topic.length < 3)
    return { ok: false, error: "Topic must be at least 3 characters." };
  if (topic.length > 200)
    return { ok: false, error: "Topic must be 200 characters or fewer." };
  if (summary.length < 10)
    return { ok: false, error: "Summary must be at least 10 characters." };
  if (summary.length > 2000)
    return { ok: false, error: "Summary must be 2000 characters or fewer." };

  const reference = genReference();
  const entry: ContactSubmission = {
    reference,
    timestamp: Date.now(),
    email,
    topic: topic.slice(0, 200),
    summary: summary.slice(0, 2000),
    source: input.source,
    sessionId: input.sessionId,
    pagePath: input.pagePath,
  };

  const kv = getKV();
  try {
    await kv.set(`contact:${reference}`, JSON.stringify(entry), ENTRY_TTL_SEC);
    const indexRaw = (await kv.get(INDEX_KEY)) ?? "[]";
    let index: string[] = [];
    try {
      index = JSON.parse(indexRaw);
    } catch {
      index = [];
    }
    index.unshift(reference);
    await kv.set(
      INDEX_KEY,
      JSON.stringify(index.slice(0, INDEX_CAP)),
      INDEX_TTL_SEC,
    );
  } catch (e) {
    console.error("[contact] KV write failed:", e);
    // Still return ok=true with reference — the visitor's submission is
    // considered accepted even if the admin-side store is flaky.
  }

  // Fire-and-forget notification — never blocks or surfaces errors.
  // No-op when RESEND_API_KEY / CONTACT_NOTIFY_EMAIL aren't configured.
  void sendContactNotification(entry).catch((e) => {
    console.error("[contact] notifier threw:", e);
  });

  return { ok: true, reference };
}

export async function listRecentContactRequests(
  limit = 50,
): Promise<ContactSubmission[]> {
  const kv = getKV();
  let index: string[] = [];
  try {
    const raw = (await kv.get(INDEX_KEY)) ?? "[]";
    index = JSON.parse(raw);
  } catch {
    index = [];
  }
  const slice = index.slice(0, Math.min(limit, INDEX_CAP));
  const entries = await Promise.all(
    slice.map(async (ref) => {
      try {
        const raw = await kv.get(`contact:${ref}`);
        return raw ? (JSON.parse(raw) as ContactSubmission) : null;
      } catch {
        return null;
      }
    }),
  );
  return entries.filter((e): e is ContactSubmission => e !== null);
}
