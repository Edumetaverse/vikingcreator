# Viking Character Forge

A standalone, browser-based Viking character creator. Open the published site at
<https://edumetaverse.github.io/vikingcreator/>.

Choose one of nine character presets, adjust garment and hair colours, and preview
Idle, Blink, Walk and Run. Idle blinks at varied intervals; Blink repeats
slower eyelid mesh morphs for inspection. Both GLB exports include a
thirteen-joint skin and all four animation clips. The standard
export preserves the full mesh and 1024 px textures in a widely compatible GLB
(about 600–850 KB). The smaller full-quality option uses `EXT_meshopt_compression`
to reduce the GLB to about 415–620 KB without changing decoded mesh attributes,
animation keys, or image bytes; the importing engine must support that extension.
The former under-200 KB export reduced geometry and texture detail visibly, so it
is no longer offered in the studio.
The walk uses mirrored contact, down, passing and up poses based on the
[Animation Mentor basic walk-cycle reference](https://www.animationmentor.com/blog/tutorial-animating-human-walk-cycle/).

The four reference-inspired additions are Elder Seer, Shield Bearer, Blacksmith,
and Armored Jarl. They reuse the original detailed skinned bodies and eyelid
morphs with faceted accessories parented to rig joints. The reference image is
in `assets/reference-new-vikings.jpeg`. Regenerate those four GLBs with
`python tools/build-reference-characters.py`.

The header uses the official EDUmetaverse logo from
<https://edumetaverse.com.au/>.

## Run locally

Serve this directory over HTTP, for example with `python -m http.server 8000`,
then open <http://localhost:8000/>. Direct `file://` loading will not work because
the character models are fetched by the browser.

## GitHub Pages

The workflow in `.github/workflows/pages.yml` deploys the site on pushes to
`main`. GitHub Pages is configured to build with GitHub Actions. The published
site needs no build step or backend. To rebuild the committed mesh compression
module, run `npm ci` and `npm run build:meshopt`; `npm test` checks the exports.

To regenerate the original five models from the simulator workspace, rebuild
the compact and high-detail assets and apply the elbow and blink scripts.
Then regenerate the four new variants with
`python tools/build-reference-characters.py` and run `npm test`.
