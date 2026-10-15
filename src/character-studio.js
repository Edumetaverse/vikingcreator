import * as pc from 'playcanvas';
import { PRESETS, DYES, CLIPS, JOINTS, poseAt, parseGlb, buildCharacterGlb } from './character-studio-core.js';

const $ = (id) => document.getElementById(id);
const defaults = ['Harald', 'Bjørn', 'Tove', 'Sigrid', 'Ulf'];
const HAIR_COLORS = [
    { id: 'original', label: 'Original', color: '#8f7159' },
    { id: 'raven', label: 'Raven black', color: '#292727', hue: 27, sat: 0.18, base: 0.05, scale: 0.42 },
    { id: 'chestnut', label: 'Chestnut brown', color: '#754328', hue: 25, sat: 0.55, base: 0.09, scale: 0.80 },
    { id: 'copper', label: 'Copper red', color: '#b6532d', hue: 17, sat: 0.70, base: 0.16, scale: 1.02 },
    { id: 'blonde', label: 'Golden blonde', color: '#d7b764', hue: 37, sat: 0.42, base: 0.52, scale: 0.78 },
    { id: 'silver', label: 'Silver grey', color: '#b4b4ad', hue: 38, sat: 0.08, base: 0.38, scale: 0.65 }
];
const saved = (() => { try { return JSON.parse(localStorage.getItem('viking-character-forge') || '{}'); } catch { return {}; } })();
const state = {
    preset: PRESETS.some((p) => p.id === saved.preset) ? saved.preset : 'Chief',
    dye: DYES.some((d) => d.id === saved.dye) ? saved.dye : 'original',
    hair: HAIR_COLORS.some((color) => color.id === saved.hair) ? saved.hair : 'original',
    clip: 'idle', name: typeof saved.name === 'string' ? saved.name.slice(0, 40) : 'Harald',
    yaw: -15, playing: true, elapsed: 0
};
let app, device, model, pivot, joints = {}, sourceBuffer, textureCanvas, activeTexture;
let loadCounter = 0, paletteCounter = 0, dragX = null;
const sourceCache = new Map();
const assetCache = new Map();
const textureCache = new Map();
const garmentMaskCache = new Map();
const hairMaskCache = new Map();

function setMessage(message) { $('footer-message').textContent = message.toUpperCase(); }
function updateControls() {
    $('preset-list').innerHTML = PRESETS.map((p) => `<button class="preset" type="button" data-preset="${p.id}" aria-pressed="${state.preset === p.id}"><span class="preset-avatar">${p.initials}</span><span class="preset-text"><strong>${p.label}</strong><small>${p.subtitle}</small></span><span class="preset-check">✓</span></button>`).join('');
    $('dye-list').innerHTML = DYES.map((d) => `<button class="dye" type="button" data-dye="${d.id}" title="${d.label}" aria-label="${d.label}" aria-pressed="${state.dye === d.id}"><span style="background:${d.color}"></span></button>`).join('') +
        `<span class="dye-caption">${DYES.find((d) => d.id === state.dye).label}</span>`;
    $('hair-list').innerHTML = HAIR_COLORS.map((color) => `<button class="dye" type="button" data-hair="${color.id}" title="${color.label}" aria-label="${color.label}" aria-pressed="${state.hair === color.id}"><span style="background:${color.color}"></span></button>`).join('') +
        `<span class="dye-caption">${HAIR_COLORS.find((color) => color.id === state.hair).label}</span>`;
    const symbols = { idle: '◇', walk: '↗', run: '➜', sit: '▣', guard: '⬡' };
    $('animation-list').innerHTML = CLIPS.map((clip) => `<button class="animation-option" type="button" data-clip="${clip.id}" aria-pressed="${state.clip === clip.id}"><span class="animation-symbol">${symbols[clip.id]}</span><span class="animation-text"><strong>${clip.label}</strong><small>${clip.note}</small></span><span class="animation-play">${state.clip === clip.id ? 'Ⅱ' : '▶'}</span></button>`).join('');
    $('character-name').value = state.name;
}

function initUi() {
    updateControls();
    $('preset-list').addEventListener('click', (event) => {
        const button = event.target.closest('[data-preset]');
        if (!button || button.dataset.preset === state.preset) return;
        state.preset = button.dataset.preset;
        state.name = defaults[PRESETS.findIndex((p) => p.id === state.preset)];
        state.elapsed = 0;
        updateControls(); loadCharacter();
    });
    $('dye-list').addEventListener('click', (event) => {
        const button = event.target.closest('[data-dye]');
        if (!button || button.dataset.dye === state.dye) return;
        state.dye = button.dataset.dye;
        updateControls(); applyPalette();
    });
    $('hair-list').addEventListener('click', (event) => {
        const button = event.target.closest('[data-hair]');
        if (!button || button.dataset.hair === state.hair) return;
        state.hair = button.dataset.hair;
        updateControls(); applyPalette();
    });
    $('animation-list').addEventListener('click', (event) => {
        const button = event.target.closest('[data-clip]');
        if (!button) return;
        if (state.clip === button.dataset.clip) state.playing = !state.playing;
        else { state.clip = button.dataset.clip; state.playing = true; state.elapsed = 0; }
        updateControls();
    });
    $('character-name').addEventListener('input', (event) => { state.name = event.target.value; });
    $('reset-view').addEventListener('click', () => { state.yaw = -15; });
    $('save-design').addEventListener('click', () => {
        localStorage.setItem('viking-character-forge', JSON.stringify({ preset: state.preset, dye: state.dye, hair: state.hair, name: state.name }));
        setMessage('Design saved in this browser');
    });
    $('export-glb').addEventListener('click', () => exportGlb('high'));
    $('export-compact').addEventListener('click', () => exportGlb('compact'));
    const dialog = $('reference-dialog');
    $('reference-button').addEventListener('click', () => dialog.showModal());
    $('close-reference').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    const canvas = $('character-canvas');
    canvas.addEventListener('pointerdown', (event) => { dragX = event.clientX; canvas.setPointerCapture(event.pointerId); });
    canvas.addEventListener('pointermove', (event) => {
        if (dragX === null) return;
        state.yaw += (event.clientX - dragX) * 0.55;
        dragX = event.clientX;
    });
    canvas.addEventListener('pointerup', () => { dragX = null; });
    canvas.addEventListener('pointercancel', () => { dragX = null; });
}

async function initScene() {
    const canvas = $('character-canvas');
    device = await pc.createGraphicsDevice(canvas, { deviceTypes: ['webgl2'], antialias: true, alpha: false });
    device.maxPixelRatio = Math.min(devicePixelRatio || 1, 2);
    const options = new pc.AppOptions();
    options.graphicsDevice = device;
    options.componentSystems = [pc.RenderComponentSystem, pc.CameraComponentSystem, pc.LightComponentSystem];
    options.resourceHandlers = [pc.TextureHandler, pc.ContainerHandler];
    app = new pc.AppBase(canvas);
    app.init(options);
    app.setCanvasFillMode(pc.FILLMODE_NONE);
    app.setCanvasResolution(pc.RESOLUTION_AUTO);
    app.scene.ambientLight = new pc.Color(0.48, 0.52, 0.54);
    const camera = new pc.Entity('Studio camera');
    camera.addComponent('camera', { fov: 32, nearClip: 0.1, farClip: 100, clearColor: new pc.Color(0.16, 0.21, 0.24) });
    camera.setPosition(0, 1.08, 4.2);
    camera.lookAt(0, 0.97, 0);
    app.root.addChild(camera);
    const key = new pc.Entity('Large soft key');
    key.addComponent('light', { type: 'directional', intensity: 1.6, castShadows: true, shadowResolution: 1024,
        shadowDistance: 12, shadowBias: 0.15, normalOffsetBias: 0.03, color: new pc.Color(1, 0.88, 0.72) });
    key.setEulerAngles(45, 145, 0);
    app.root.addChild(key);
    const fill = new pc.Entity('Cool fill');
    fill.addComponent('light', { type: 'directional', intensity: 0.55, color: new pc.Color(0.55, 0.74, 0.86) });
    fill.setEulerAngles(25, -65, 0);
    app.root.addChild(fill);
    const plinth = new pc.Entity('Display plinth');
    plinth.addComponent('render', { type: 'cylinder', castShadows: false, receiveShadows: true });
    plinth.setLocalScale(1.8, 0.09, 1.8);
    plinth.setPosition(0, -0.05, 0);
    const stone = new pc.StandardMaterial();
    stone.diffuse = new pc.Color(0.28, 0.33, 0.33);
    stone.metalness = 0.05; stone.gloss = 0.15; stone.update();
    plinth.render.material = stone;
    app.root.addChild(plinth);
    const stool = new pc.Entity('Sit preview stool');
    stool.addComponent('render', { type: 'cylinder', castShadows: true, receiveShadows: true });
    stool.setLocalScale(0.98, 0.08, 0.62);
    stool.setPosition(0, 0.48, -0.18);
    const wood = new pc.StandardMaterial();
    wood.diffuse = new pc.Color(0.29, 0.17, 0.10); wood.gloss = 0.08; wood.update();
    stool.render.material = wood;
    app.root.addChild(stool);
    const stoolLegs = [-0.34, 0.34].map((x) => {
        const leg = new pc.Entity('Sit preview stool leg');
        leg.addComponent('render', { type: 'cylinder', castShadows: true });
        leg.setLocalScale(0.12, 0.48, 0.12);
        leg.setPosition(x, 0.21, -0.18);
        leg.render.material = wood;
        app.root.addChild(leg);
        return leg;
    });
    pivot = new pc.Entity('Character turntable');
    app.root.addChild(pivot);
    app.on('update', (dt) => {
        const delta = Math.min(dt, 0.05);
        if (state.playing) state.elapsed += delta;
        const pose = poseAt(state.clip, state.elapsed);
        for (const joint of JOINTS) joints[joint]?.setLocalEulerAngles(...pose.rotations[joint]);
        if (joints.WalkRoot) joints.WalkRoot.setLocalPosition(0, pose.rise, 0);
        pivot.setLocalEulerAngles(0, state.yaw, 0);
        stool.enabled = state.clip === 'sit';
        for (const leg of stoolLegs) leg.enabled = state.clip === 'sit';
    });
    const resize = () => {
        const rect = canvas.getBoundingClientRect();
        if (rect.width && rect.height) app.resizeCanvas(Math.round(rect.width), Math.round(rect.height));
    };
    new ResizeObserver(resize).observe(canvas);
    app.start();
    resize();
}

async function getSource(id, tier = 'high') {
    const key = `${tier}:${id}`;
    const folder = tier === 'high' ? 'studio-high' : 'studio';
    if (!sourceCache.has(key)) sourceCache.set(key, fetch(`./assets/models/characters/${folder}/${id}.glb`).then((response) => {
        if (!response.ok) throw new Error(`Could not load ${id}.glb (${response.status}).`);
        return response.arrayBuffer();
    }));
    return sourceCache.get(key);
}

async function getAsset(id) {
    if (!assetCache.has(id)) assetCache.set(id, new Promise((resolve, reject) => {
        const asset = new pc.Asset(id, 'container', { url: `./assets/models/characters/studio-high/${id}.glb` });
        asset.once('load', () => resolve(asset));
        asset.once('error', (error) => reject(error || new Error(`Could not open ${id}.glb`)));
        app.assets.add(asset);
        app.assets.load(asset);
    }));
    return assetCache.get(id);
}

async function loadCharacter() {
    const ticket = ++loadCounter;
    const id = state.preset;
    $('export-glb').disabled = true;
    $('export-compact').disabled = true;
    sourceBuffer = null;
    textureCanvas = null;
    $('model-status').textContent = `Loading ${id}…`;
    setMessage(`Preparing ${id}`);
    try {
        const [asset, source] = await Promise.all([getAsset(id), getSource(id)]);
        if (ticket !== loadCounter) return;
        if (model) model.destroy();
        if (activeTexture) { activeTexture.destroy(); activeTexture = null; }
        model = asset.resource.instantiateRenderEntity({ castShadows: true, receiveShadows: false });
        model.setLocalPosition(0, 0.96, 0);
        pivot.addChild(model);
        joints = Object.fromEntries(JOINTS.map((joint) => [joint, model.findByName(joint)]));
        if (Object.values(joints).some((joint) => !joint)) throw new Error('Character rig is incomplete.');
        const skinned = model.findComponents('render').some((render) => render.meshInstances.some((mi) => mi.skinInstance));
        if (!skinned) throw new Error('Character has no skinned mesh.');
        sourceBuffer = source;
        $('model-status').textContent = `${PRESETS.find((p) => p.id === id).label} · high-detail rig`;
        setMessage(`${id} ready`);
        await applyPalette();
        if (ticket === loadCounter) {
            $('export-glb').disabled = false;
            $('export-compact').disabled = false;
        }
    } catch (error) {
        $('model-status').textContent = 'Model unavailable';
        setMessage(error.message || 'Could not load character');
        console.error(error);
    }
}

async function getBaseImage(id, source) {
    if (!textureCache.has(id)) textureCache.set(id, (async () => {
        const { json, binary } = parseGlb(source);
        const texture = json.materials[0].pbrMetallicRoughness.baseColorTexture.index;
        const image = json.images[json.textures[texture].source];
        const view = json.bufferViews[image.bufferView];
        const bytes = binary.slice(view.byteOffset, view.byteOffset + view.byteLength);
        return createImageBitmap(new Blob([bytes], { type: image.mimeType }));
    })());
    return textureCache.get(id);
}

function rgbToHsv(r, g, b) {
    const max = Math.max(r, g, b), min = Math.min(r, g, b), delta = max - min;
    let hue = 0;
    if (delta) {
        if (max === r) hue = ((g - b) / delta) % 6;
        else if (max === g) hue = (b - r) / delta + 2;
        else hue = (r - g) / delta + 4;
        hue = (hue * 60 + 360) % 360;
    }
    return [hue, max ? delta / max : 0, max];
}

function hsvToRgb(h, s, v) {
    const c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
    const sectors = [[c, x, 0], [x, c, 0], [0, c, x], [0, x, c], [x, 0, c], [c, 0, x]];
    return sectors[Math.floor(h / 60) % 6].map((value) => Math.round((value + m) * 255));
}

function surfaceMask(source, width, height, includeTriangle) {
    const { json, binary } = parseGlb(source);
    const primitive = json.meshes[0].primitives[0];
    const accessor = (index) => {
        const info = json.accessors[index], view = json.bufferViews[info.bufferView];
        const count = info.count, width = info.type === 'VEC3' ? 3 : info.type === 'VEC2' ? 2 : 1;
        const size = info.componentType === 5126 || info.componentType === 5125 ? 4 :
            info.componentType === 5123 ? 2 : 1;
        const offset = view.byteOffset + (info.byteOffset || 0);
        const stride = view.byteStride || width * size;
        const data = new DataView(binary.buffer, binary.byteOffset, binary.byteLength);
        const values = new Float32Array(count * width);
        for (let i = 0; i < count; i++) for (let j = 0; j < width; j++) {
            const at = offset + i * stride + j * size;
            values[i * width + j] = info.componentType === 5126 ? data.getFloat32(at, true) :
                info.componentType === 5125 ? data.getUint32(at, true) :
                info.componentType === 5123 ? data.getUint16(at, true) / (info.normalized ? 65535 : 1) :
                data.getUint8(at) / (info.normalized ? 255 : 1);
        }
        return values;
    };
    const pos = accessor(primitive.attributes.POSITION);
    const uv = accessor(primitive.attributes.TEXCOORD_0);
    const indices = accessor(primitive.indices);
    const mask = document.createElement('canvas');
    mask.width = width; mask.height = height;
    const context = mask.getContext('2d', { willReadFrequently: true });
    context.fillStyle = '#fff';
    for (let i = 0; i < indices.length; i += 3) {
        const a = indices[i], b = indices[i + 1], c = indices[i + 2];
        const x = (pos[a * 3] + pos[b * 3] + pos[c * 3]) / 3;
        const y = (pos[a * 3 + 1] + pos[b * 3 + 1] + pos[c * 3 + 1]) / 3;
        const z = (pos[a * 3 + 2] + pos[b * 3 + 2] + pos[c * 3 + 2]) / 3;
        if (!includeTriangle(x, y, z)) continue;
        context.beginPath();
        context.moveTo(uv[a * 2] * width, uv[a * 2 + 1] * height);
        context.lineTo(uv[b * 2] * width, uv[b * 2 + 1] * height);
        context.lineTo(uv[c * 2] * width, uv[c * 2 + 1] * height);
        context.closePath(); context.fill();
    }
    return context.getImageData(0, 0, width, height).data;
}

function recolor(image, dye, hair, source) {
    const canvas = document.createElement('canvas');
    canvas.width = image.width; canvas.height = image.height;
    const context = canvas.getContext('2d', { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    if (dye.id === 'original' && hair.id === 'original') return canvas;
    const frame = context.getImageData(0, 0, canvas.width, canvas.height);
    const data = frame.data;
    const original = new Uint8ClampedArray(data);
    const key = `${state.preset}:${canvas.width}`;
    if (dye.id !== 'original') {
        if (!garmentMaskCache.has(key)) {
            const skirt = state.preset === 'FemaleTrader' || state.preset === 'Sheildmaiden';
            const minY = skirt ? -0.63 : -0.37;
            garmentMaskCache.set(key, surfaceMask(source, canvas.width, canvas.height,
                (x, y) => y >= minY && y <= 0.49 && Math.abs(x) <= 0.33));
        }
        const mask = garmentMaskCache.get(key);
        for (let i = 0; i < data.length; i += 4) {
            if (mask[i + 3] < 128) continue;
            const r = original[i] / 255, g = original[i + 1] / 255, b = original[i + 2] / 255;
            const [hue, saturation, value] = rgbToHsv(r, g, b);
            const skin = r > 0.49 && r > g * 1.11 && g > b * 1.08 && value > 0.48;
            const trim = (hue < 16 || hue > 345) && saturation > 0.48 && value > 0.35;
            const cloth = saturation > 0.16 && value > 0.10 && value < 0.84 &&
                ((hue > 155 && hue < 265) || (hue > 17 && hue < 58 && value < 0.65) || (hue > 265 && hue < 340));
            if (!cloth || skin || trim) continue;
            const strength = (hue > 155 && hue < 265) ? 0.92 : 0.67;
            const [nr, ng, nb] = hsvToRgb(dye.hue, Math.max(dye.sat * 0.7, Math.min(0.75, dye.sat + saturation * 0.15)), value);
            data[i] = Math.round(data[i] * (1 - strength) + nr * strength);
            data[i + 1] = Math.round(data[i + 1] * (1 - strength) + ng * strength);
            data[i + 2] = Math.round(data[i + 2] * (1 - strength) + nb * strength);
        }
    }
    if (hair.id !== 'original') {
        const blondeSource = state.preset === 'Sheildmaiden';
        const braidedSource = state.preset === 'FemaleTrader';
        const longHairSource = state.preset === 'Chief' || state.preset === 'Warrior';
        if (!hairMaskCache.has(key)) hairMaskCache.set(key, surfaceMask(source, canvas.width, canvas.height,
            blondeSource
                ? (x, y, z) => y >= 0.18 && Math.abs(x) <= 0.19 && Math.abs(z) <= 0.26
                : (x, y, z) => (y >= 0.72 && Math.abs(x) <= 0.16 && Math.abs(z) <= 0.23) ||
                    (state.preset === 'Chief'
                        ? y >= 0.59 && Math.abs(x) <= 0.12 && z >= 0.14 && z <= 0.24
                        : y >= 0.62 && Math.abs(x) <= 0.16 && z >= 0.02 && z <= 0.24) ||
                    (longHairSource && y >= 0.57 && Math.abs(x) <= 0.14 && z <= -0.12 && z >= -0.24) ||
                    (braidedSource && y >= 0.38 && Math.abs(x) >= 0.06 && Math.abs(x) <= 0.21 && z >= -0.08 && z <= 0.24)));
        const mask = hairMaskCache.get(key);
        for (let i = 0; i < data.length; i += 4) {
            if (mask[i + 3] < 128) continue;
            const r = original[i] / 255, g = original[i + 1] / 255, b = original[i + 2] / 255;
            const [hue, saturation, value] = rgbToHsv(r, g, b);
            const skin = hue < 36 && value > 0.62 && r > g * 1.1 && g > b * 1.08;
            const pale = value > 0.68 && saturation < 0.18;
            const naturallyHair = blondeSource
                ? hue >= 33 && hue <= 65 && saturation >= 0.27 && value >= 0.55 && r > b * 1.4 && g > b * 1.3
                : hue >= 10 && hue <= 55 && saturation >= 0.20 && value >= 0.08 && value <= 0.65;
            if (!naturallyHair || skin || pale) continue;
            const [nr, ng, nb] = hsvToRgb(hair.hue, hair.sat, Math.min(0.96, hair.base + value * hair.scale));
            data[i] = nr; data[i + 1] = ng; data[i + 2] = nb;
        }
    }
    context.putImageData(frame, 0, 0);
    return canvas;
}

async function applyPalette() {
    const ticket = ++paletteCounter;
    if (!model || !sourceBuffer) return;
    if (state.dye === 'original' && state.hair === 'original') {
        textureCanvas = null;
        for (const render of model.findComponents('render')) for (const mi of render.meshInstances) {
            if (mi._forgeOriginalMaterial) mi.material = mi._forgeOriginalMaterial;
        }
        if (activeTexture) { activeTexture.destroy(); activeTexture = null; }
        setMessage('Original palette');
        return;
    }
    const id = state.preset;
    const image = await getBaseImage(id, sourceBuffer);
    const canvas = recolor(image, DYES.find((d) => d.id === state.dye),
        HAIR_COLORS.find((color) => color.id === state.hair), sourceBuffer);
    if (ticket !== paletteCounter || id !== state.preset) return;
    const texture = new pc.Texture(device, { width: canvas.width, height: canvas.height,
        format: pc.PIXELFORMAT_RGBA8, mipmaps: true });
    texture.setSource(canvas);
    if (activeTexture) activeTexture.destroy();
    activeTexture = texture;
    textureCanvas = canvas;
    for (const render of model.findComponents('render')) for (const mi of render.meshInstances) {
        if (!mi._forgeOriginalMaterial) mi._forgeOriginalMaterial = mi.material;
        const material = mi._forgeOriginalMaterial.clone();
        material.diffuseMap = texture;
        material.update();
        mi.material = material;
    }
    setMessage(`${DYES.find((d) => d.id === state.dye).label} garments · ${HAIR_COLORS.find((color) => color.id === state.hair).label} hair`);
}

async function exportGlb(tier) {
    if (!sourceBuffer || !model) return;
    const buttons = [$('export-glb'), $('export-compact')];
    buttons.forEach((button) => { button.disabled = true; });
    try {
        const name = state.name.trim() || PRESETS.find((p) => p.id === state.preset).label;
        const source = tier === 'compact' ? await getSource(state.preset, 'compact') : sourceBuffer;
        let buffer;
        const paletteId = `${state.dye}-garments-${state.hair}-hair`;
        if (!textureCanvas) buffer = buildCharacterGlb(source, null, name, paletteId);
        else if (tier === 'high') {
            const image = await new Promise((resolve) => textureCanvas.toBlob(resolve, 'image/jpeg', 0.90));
            if (!image) throw new Error('Could not encode colour palette.');
            buffer = buildCharacterGlb(source, new Uint8Array(await image.arrayBuffer()), name, paletteId);
        } else {
            for (const size of [512, 384, 320, 256]) {
                const atlas = document.createElement('canvas');
                atlas.width = size; atlas.height = size;
                atlas.getContext('2d').drawImage(textureCanvas, 0, 0, size, size);
                for (const quality of [0.72, 0.56, 0.42]) {
                    const image = await new Promise((resolve) => atlas.toBlob(resolve, 'image/jpeg', quality));
                    if (!image) throw new Error('Could not encode colour palette.');
                    buffer = buildCharacterGlb(source, new Uint8Array(await image.arrayBuffer()), name, paletteId);
                    if (buffer.byteLength < 200_000) break;
                }
                if (buffer.byteLength < 200_000) break;
            }
        }
        if (tier === 'compact' && buffer.byteLength >= 200_000)
            throw new Error(`Compact export is ${(buffer.byteLength / 1000).toFixed(0)} KB. Try another palette.`);
        const blob = new Blob([buffer], { type: 'model/gltf-binary' });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `${name.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'viking'}-${tier === 'compact' ? 'compact' : 'high-detail'}-animated.glb`;
        document.body.appendChild(anchor);
        anchor.click(); anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        setMessage(`Exported ${anchor.download} · ${(buffer.byteLength / 1000).toFixed(1)} KB`);
    } catch (error) {
        setMessage(error.message || 'Export failed');
        console.error(error);
    } finally { buttons.forEach((button) => { button.disabled = false; }); }
}

initUi();
try { await initScene(); await loadCharacter(); }
catch (error) { $('model-status').textContent = '3D preview unavailable'; setMessage(error.message || 'Studio failed to start'); console.error(error); }
