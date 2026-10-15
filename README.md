# Viking Character Forge

A standalone, browser-based Viking character creator. Open the published site at
<https://edumetaverse.github.io/vikingcreator/>.

Choose one of five character presets, adjust garment and hair colours, and preview
Idle, Walk, Run, Sit and Guard. Both GLB exports include a nine-joint skin and all
five animation clips. The high-detail export preserves the 1024 px textures; the
compact export enforces a 200,000-byte limit.

An [animated 199 KB example](https://edumetaverse.github.io/vikingcreator/200kb-example.html)
loads the exact downloadable GLB in the viewer. The sample is 198,716 bytes and
contains the skinned mesh, colour atlas, blinking eyelids and all five clips. It uses the current
quantized compact export; Meshopt compression has not been applied to this sample.

## Run locally

Serve this directory over HTTP, for example with `python -m http.server 8000`,
then open <http://localhost:8000/>. Direct `file://` loading will not work because
the character models are fetched by the browser.

## GitHub Pages

The workflow in `.github/workflows/pages.yml` deploys the site on pushes to
`main`. GitHub Pages is configured to build with GitHub Actions. The site needs
no build step or backend.
