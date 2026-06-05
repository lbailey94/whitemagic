/**
 * Edge middleware — Basic-Auth gate for the /admin surface.
 *
 * Env:
 *   ADMIN_PASSWORD_HASH   SHA-256 hex digest of the shared admin password.
 *                         If unset, /admin is left ungated (dev convenience).
 *                         Set it in production.
 *   ADMIN_USER            Optional — defaults to "admin". Username portion
 *                         of Basic Auth; not a secret.
 *
 * Generate a hash:
 *   node -e "require('crypto').createHash('sha256').update('your-password').digest('hex')"
 *   # or
 *   echo -n 'your-password' | sha256sum
 *
 * Constant-time compare is used on the hex digest to avoid timing leaks
 * when someone probes the admin endpoint.
 */

import { NextResponse, type NextRequest } from "next/server";

export const config = {
  matcher: ["/admin", "/admin/:path*"],
};

const REALM = 'Basic realm="WhiteMagic Admin", charset="UTF-8"';

function timingSafeEqualHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function unauthorized(): NextResponse {
  return new NextResponse("Authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": REALM,
      "Cache-Control": "no-store",
    },
  });
}

export async function middleware(req: NextRequest): Promise<NextResponse> {
  const expectedHash = (process.env.ADMIN_PASSWORD_HASH ?? "").toLowerCase();
  // Dev convenience: if no hash configured, do not gate.
  if (!expectedHash) {
    return NextResponse.next();
  }

  const expectedUser = process.env.ADMIN_USER ?? "admin";
  const header = req.headers.get("authorization") ?? "";
  if (!header.toLowerCase().startsWith("basic ")) {
    return unauthorized();
  }

  let decoded: string;
  try {
    decoded = atob(header.slice(6).trim());
  } catch {
    return unauthorized();
  }

  const sep = decoded.indexOf(":");
  if (sep < 0) return unauthorized();
  const user = decoded.slice(0, sep);
  const pass = decoded.slice(sep + 1);

  if (user !== expectedUser) {
    return unauthorized();
  }

  const suppliedHash = await sha256Hex(pass);
  if (!timingSafeEqualHex(suppliedHash, expectedHash)) {
    return unauthorized();
  }

  return NextResponse.next();
}
