import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

interface LibraryFile {
  id: string;
  title: string;
  category: string;
  preview: string;
  size: number;
  ext: string;
}

interface LibraryManifest {
  root: string;
  total_files: number;
  total_size: number;
  categories: string[];
  files: LibraryFile[];
}

let cached: LibraryManifest | null = null;

function loadManifest(): LibraryManifest | null {
  if (cached) return cached;
  try {
    const fp = path.join(process.cwd(), "public", "library_manifest.json");
    cached = JSON.parse(fs.readFileSync(fp, "utf-8")) as LibraryManifest;
    return cached;
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim().toLowerCase();
  const category = searchParams.get("category") || "";
  const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
  const perPage = Math.min(
    parseInt(searchParams.get("per_page") || "50", 10),
    200,
  );
  const id = searchParams.get("id")?.trim();

  const manifest = loadManifest();
  if (!manifest) {
    return NextResponse.json(
      { error: "Library manifest not found. Run: python core/scripts/build_library_manifest.py" },
      { status: 503 },
    );
  }

  // Single file lookup
  if (id) {
    const file = manifest.files.find((f) => f.id === id);
    if (!file) {
      return NextResponse.json({ error: "File not found" }, { status: 404 });
    }
    // Load full content
    try {
      const contentPath = path.join(manifest.root, file.id);
      const content = fs.readFileSync(contentPath, "utf-8");
      return NextResponse.json({
        ...file,
        content: content.slice(0, 50000), // Cap at 50KB
        total_length: content.length,
        truncated: content.length > 50000,
      });
    } catch {
      return NextResponse.json({ error: "File unavailable on disk", ...file });
    }
  }

  // Filter
  let filtered = manifest.files;
  if (category) {
    filtered = filtered.filter((f) => f.category === category);
  }
  if (q) {
    const terms = q.split(/\s+/).filter(Boolean);
    filtered = filtered.filter((f) => {
      const text = (f.title + " " + f.preview).toLowerCase();
      return terms.some((t) => text.includes(t));
    });
  }

  const total = filtered.length;
  const totalPages = Math.ceil(total / perPage);
  const start = (page - 1) * perPage;
  const results = filtered.slice(start, start + perPage).map((f) => ({
    id: f.id,
    title: f.title,
    category: f.category,
    preview: f.preview.slice(0, 200),
    size: f.size,
    ext: f.ext,
  }));

  return NextResponse.json({
    total_files_manifest: manifest.total_files,
    total_size_manifest: manifest.total_size,
    categories: manifest.categories,
    query: q || null,
    category_filter: category || null,
    page,
    per_page: perPage,
    total_results: total,
    total_pages: totalPages,
    results,
  });
}
