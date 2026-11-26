# CAA artwork containment

CAA artwork now uses `object-fit: contain` in search results, archive grids and lists,
and album details. The existing square frame, background, layout and rounded corners
remain unchanged. Uploaded photos and placeholders keep their existing styles.

## Scope

Base main: `ba83392ce179c7e6ad0c099241d86dfeedd49dc3`.

`index.html` adds `caa-art` only in the CAA branch of `art()`. The scoped selectors
`.art.caa-art` and `.coverbtn.tile .art.caa-art` also override the grid's more
specific `cover` rule. No storage, backup, external request, legal or takedown behavior
changes are included.

## Validation

`tests/caa_artwork.py` runs the actual UI in isolated Chromium and WebKit contexts.
All HTTP requests are fulfilled locally or aborted. Fixtures include square 400x400,
portrait 240x480 and landscape 480x240 PNGs, uploaded photos, CAA 404s and missing MBIDs.
It compares the implementation with the base main at widths 390 and 1280 CSS pixels.

All 72 before/after screen comparisons passed:

- Artist search followed by its album results, and album title search.
- Listening and Collection grids and lists.
- Listening and Collection details for all three aspect ratios, an uploaded photo,
  a failed CAA image and a record with no MBID.
- All four colored image edges remain visible for CAA images using contain.
- Frame geometry, title geometry, corner radius, object position and background match.
- Square images remain visually unchanged. Fractional CSS pixel boundaries can produce
  minute rasterization differences: the test permits a mean channel difference below
  0.25/255 and a maximum difference of 16/255. Uploaded photo pixels match exactly.
- Placeholder pixels and persisted archive records match exactly.

Commands and results:

| Check | Result |
| --- | --- |
| `node --test --test-isolation=none tests/*.test.cjs` | 166 passed, 0 failed |
| `python tests/static_build.py` | 5 passed |
| `node scripts/build-static.cjs` | 17 distribution files generated |
| `python tests/static_distribution.py` | All source/dist/clean-URL, path and language scenarios passed, including no-JavaScript legal pages |
| `MLA_WEBKIT=/tmp/mla-webkit python tests/caa_artwork.py` | Chromium and WebKit, 390/1280px, 72 comparisons passed |
| `python tests/browser_smoke.py` | Existing failure at line 94; reproduced unchanged on the base main |
| `git diff --check` | Passed |

The legacy smoke test expects a newly saved record in its localStorage snapshot, while
current persistence uses IndexedDB. Its failure is also present on unmodified main;
this change does not modify that test or persistence behavior.

The custom browser test requires Playwright and Pillow. `MLA_WEBKIT` is optional and
selects an executable when the environment needs a wrapper for local shared libraries;
otherwise Playwright's installed WebKit is used. `MLA_EVIDENCE` selects the screenshot
and JSON output directory (default `/tmp/mla-caa-artwork-evidence`).

## Preview and device validation

Use the existing authenticated Preview at
`https://deploy-preview.my-listening-archive.pages.dev/`, built from `deploy/preview`
with `node scripts/build-static.cjs` and output directory `dist`.
Production and Cloudflare Access configuration are outside this change.

Playwright WebKit is not an iPhone Safari device test. Device approval remains pending.
Use a fresh Preview browser context with no personal archive. Check artist/title search,
both archive layouts, and Listening/Collection details. Confirm full portrait/landscape
artwork within the existing rounded frame, unchanged square artwork, uploaded photos,
and failure placeholders. Automated synthetic CAA responses are local to the browser
test and are not deployed as application features.
