/**
 * Email notifications — thin Resend wrapper.
 *
 * Env-gated: if RESEND_API_KEY or CONTACT_NOTIFY_EMAIL are missing, every
 * exported function becomes a silent no-op. This keeps dev builds clean
 * until a real key lands, and prevents a flaky mail provider from ever
 * surfacing an error to the visitor.
 *
 * No SDK dependency — Resend exposes a simple REST endpoint.
 *
 * Env:
 *   RESEND_API_KEY         required to send
 *   CONTACT_NOTIFY_EMAIL   where submissions are forwarded
 *   CONTACT_FROM_EMAIL     optional; defaults to Resend onboarding sender
 */
import type { ContactSubmission } from "./contact";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const DEFAULT_FROM = "WhiteMagic <onboarding@resend.dev>";

function notifyEnv(): { apiKey: string; to: string; from: string } | null {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.CONTACT_NOTIFY_EMAIL;
  if (!apiKey || !to) return null;
  const from = process.env.CONTACT_FROM_EMAIL ?? DEFAULT_FROM;
  return { apiKey, to, from };
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderHtml(entry: ContactSubmission): string {
  const when = new Date(entry.timestamp).toISOString();
  const summaryHtml = escapeHtml(entry.summary).replace(/\n/g, "<br/>");
  return `<!doctype html>
<html>
  <body style="font-family:system-ui,sans-serif;max-width:640px;margin:24px auto;color:#111">
    <h2 style="margin:0 0 8px">New contact submission</h2>
    <p style="color:#666;margin:0 0 16px">Reference: <code>${escapeHtml(entry.reference)}</code> &middot; ${escapeHtml(when)} &middot; via ${escapeHtml(entry.source)}</p>
    <table cellpadding="6" style="border-collapse:collapse;width:100%">
      <tr><td style="border:1px solid #eee;width:120px"><b>Email</b></td><td style="border:1px solid #eee"><a href="mailto:${escapeHtml(entry.email)}">${escapeHtml(entry.email)}</a></td></tr>
      <tr><td style="border:1px solid #eee"><b>Topic</b></td><td style="border:1px solid #eee">${escapeHtml(entry.topic)}</td></tr>
      ${entry.pagePath ? `<tr><td style="border:1px solid #eee"><b>Page</b></td><td style="border:1px solid #eee"><code>${escapeHtml(entry.pagePath)}</code></td></tr>` : ""}
      ${entry.sessionId ? `<tr><td style="border:1px solid #eee"><b>Session</b></td><td style="border:1px solid #eee"><code>${escapeHtml(entry.sessionId)}</code></td></tr>` : ""}
    </table>
    <h3 style="margin:20px 0 6px">Summary</h3>
    <div style="border:1px solid #eee;padding:12px;white-space:pre-wrap">${summaryHtml}</div>
  </body>
</html>`;
}

function renderText(entry: ContactSubmission): string {
  const when = new Date(entry.timestamp).toISOString();
  const lines = [
    `New contact submission`,
    `Reference: ${entry.reference}`,
    `When:      ${when}`,
    `Source:    ${entry.source}`,
    `Email:     ${entry.email}`,
    `Topic:     ${entry.topic}`,
  ];
  if (entry.pagePath) lines.push(`Page:      ${entry.pagePath}`);
  if (entry.sessionId) lines.push(`Session:   ${entry.sessionId}`);
  lines.push("", "Summary:", entry.summary);
  return lines.join("\n");
}

/**
 * Fire-and-forget notification. Never throws; logs failures and returns
 * false. Safe to `await` or not — callers typically don't block on it.
 */
export async function sendContactNotification(
  entry: ContactSubmission,
): Promise<boolean> {
  const env = notifyEnv();
  if (!env) return false;

  const payload = {
    from: env.from,
    to: [env.to],
    reply_to: entry.email,
    subject: `[WhiteMagic] ${entry.source === "librarian" ? "Librarian" : "Form"}: ${entry.topic.slice(0, 80)}`,
    html: renderHtml(entry),
    text: renderText(entry),
    tags: [
      { name: "source", value: entry.source },
      { name: "kind", value: "contact-submission" },
    ],
  };

  try {
    const res = await fetch(RESEND_ENDPOINT, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(
        `[notify] Resend responded ${res.status}: ${text.slice(0, 200)}`,
      );
      return false;
    }
    return true;
  } catch (e) {
    console.error("[notify] Resend request failed:", e);
    return false;
  }
}

/** True when notification env is configured — used by /admin to show status. */
export function isNotifyConfigured(): boolean {
  return notifyEnv() !== null;
}
