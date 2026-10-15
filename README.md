# Viking Character Forge

A standalone, browser-based Viking character creator. Open the published site at
<https://edumetaverse.github.io/vikingcreator/>.

Choose one of five character presets, adjust garment and hair colours, and preview
Idle, Blink, Walk, Run and Sit. Idle blinks at varied intervals; Blink repeats
slower eyelid mesh morphs for inspection. Sit bends both knees
forward and leans the torso slightly; the preview has no seat. Both GLB exports
include a thirteen-joint skin and all five animation clips. Sit places the
thighs at 75 degrees, lowers the hips by 0.24 m to keep feet on the floor, and
uses separate hip and knee hinges for the front of long garments. The high-detail
export preserves the 1024 px textures and uses `EXT_meshopt_compression` to
reduce the GLB to about 418–623 KB per character without changing decoded mesh
attributes, animation keys, or image bytes. Game engines need support for this
glTF extension. The compact export enforces a 200,000-byte limit with reduced detail.
The walk uses mirrored contact, down, passing and up poses based on the
[Animation Mentor basic walk-cycle reference](https://www.animationmentor.com/blog/tutorial-animating-human-walk-cycle/).

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

To regenerate the included models from the simulator workspace, rebuild the
compact and high-detail assets, then run
`python tools/apply-sit-skin-weights.py`,
`python tools/align-sit-knees.py`, `python tools/add-character-elbows.py`, `python tools/add-character-blink.py`,
`python tools/add-seated-garment-joint.py`,
and `node tools/test-character-studio.mjs`.
