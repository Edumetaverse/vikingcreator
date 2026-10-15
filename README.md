# Viking Character Forge

A standalone, browser-based Viking character creator. Open the published site at
<https://edumetaverse.github.io/vikingcreator/>.

Choose one of five character presets, adjust garment and hair colours, and preview
Idle, Walk, Run, Sit and Guard. Idle includes a blink. Sit bends both knees
forward and leans the torso slightly; the preview has no seat. Both GLB exports
include a nine-joint skin and all five animation clips. The high-detail export
preserves the 1024 px textures and currently ranges from about 600–841 KB by
character. The compact export enforces a 200,000-byte limit with reduced detail.

The header uses the official EDUmetaverse logo from
<https://edumetaverse.com.au/>.

## Run locally

Serve this directory over HTTP, for example with `python -m http.server 8000`,
then open <http://localhost:8000/>. Direct `file://` loading will not work because
the character models are fetched by the browser.

## GitHub Pages

The workflow in `.github/workflows/pages.yml` deploys the site on pushes to
`main`. GitHub Pages is configured to build with GitHub Actions. The site needs
no build step or backend.

To regenerate the included models from the simulator workspace, rebuild the
compact and high-detail assets, then run
`python tools/apply-sit-skin-weights.py`,
`python tools/add-character-blink.py`, and `node tools/test-character-studio.mjs`.
