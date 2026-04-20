/**
 * Inline <script type="application/ld+json"> renderer.
 *
 * Accepts a single object or an array; serializes with `JSON.stringify`.
 * Use in any Server Component — no client JS, no hydration cost.
 */
export function JsonLd({
  data,
}: {
  data: Record<string, unknown> | Record<string, unknown>[];
}) {
  const payload = Array.isArray(data) ? data : [data];
  return (
    <>
      {payload.map((obj, i) => (
        <script
          // eslint-disable-next-line react/no-array-index-key
          key={i}
          type="application/ld+json"
          // Next/React will escape unsafe chars; keep raw JSON otherwise.
          dangerouslySetInnerHTML={{ __html: JSON.stringify(obj) }}
        />
      ))}
    </>
  );
}
