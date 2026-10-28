# Gen3 generated contract artifacts

The release tail writes the Gen3 route/schema manifest to
`docs/gen3/route-schema-manifest.json` from the exact released Gen3 binary's
`wm contract --json` output. It validates the manifest version, format, family,
and route counts before replacing this file.

This Gen3 path is separate from the historical Gen2
`docs/contract/route-schema-manifest.json`. A Gen3 release must never recreate,
replace, or relabel that Gen2 artifact. The v9 route catalog at
`catalogs/routes_v9_enriched.json` remains Gen2-owned as well.
