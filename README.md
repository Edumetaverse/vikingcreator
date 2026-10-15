# Viking Character Forge

A standalone, browser-based Viking character creator. Open the published site at
<https://edumetaverse.github.io/vikingcreator/>.

Choose one of five character presets, adjust garment and hair colours, and preview
Idle, Walk, Run, Sit and Guard. Both GLB exports include a nine-joint skin and all
five animation clips. The high-detail export preserves the 1024 px textures; the
compact export enforces a 200,000-byte limit.

## Run locally

Serve this directory over HTTP, for example with `python -m http.server 8000`,
then open <http://localhost:8000/>. Direct `file://` loading will not work because
the character models are fetched by the browser.

## GitHub Pages

The workflow in `.github/workflows/pages.yml` deploys the site on pushes to
`main`. On first setup, set **Settings → Pages → Build and deployment → Source**
to **GitHub Actions**. The site needs no build step or backend.
