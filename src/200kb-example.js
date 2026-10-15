import * as pc from 'playcanvas';
import { CLIPS, JOINTS, EYELIDS, poseAt, blinkAmount } from './character-studio-core.js';

const canvas = document.getElementById('example-canvas');
const status = document.getElementById('status');
const buttons = document.getElementById('clips');
let clip = 'idle';
let elapsed = 0;
let yaw = -15;
let dragX = null;
let joints = {};
let eyelids = [];

buttons.innerHTML = CLIPS.map(({ id, label }) => `<button type="button" data-clip="${id}" aria-pressed="${id === clip}">${label}</button>`).join('');
buttons.addEventListener('click', (event) => {
    const button = event.target.closest('[data-clip]');
    if (!button) return;
    clip = button.dataset.clip;
    elapsed = 0;
    for (const item of buttons.querySelectorAll('button')) item.setAttribute('aria-pressed', String(item === button));
});
canvas.addEventListener('pointerdown', (event) => { dragX = event.clientX; canvas.setPointerCapture(event.pointerId); });
canvas.addEventListener('pointermove', (event) => {
    if (dragX === null) return;
    yaw += (event.clientX - dragX) * 0.55;
    dragX = event.clientX;
});
canvas.addEventListener('pointerup', () => { dragX = null; });
canvas.addEventListener('pointercancel', () => { dragX = null; });

try {
    const device = await pc.createGraphicsDevice(canvas, { deviceTypes: ['webgl2'], antialias: true, alpha: false });
    device.maxPixelRatio = Math.min(devicePixelRatio || 1, 2);
    const options = new pc.AppOptions();
    options.graphicsDevice = device;
    options.componentSystems = [pc.RenderComponentSystem, pc.CameraComponentSystem, pc.LightComponentSystem];
    options.resourceHandlers = [pc.TextureHandler, pc.ContainerHandler];
    const app = new pc.AppBase(canvas);
    app.init(options);
    app.setCanvasFillMode(pc.FILLMODE_NONE);
    app.setCanvasResolution(pc.RESOLUTION_AUTO);
    app.scene.ambientLight = new pc.Color(0.58, 0.62, 0.64);

    const camera = new pc.Entity('Camera');
    camera.addComponent('camera', { fov: 32, nearClip: 0.1, farClip: 100, clearColor: new pc.Color(0.11, 0.17, 0.18) });
    camera.setPosition(0, 1.08, 4.9);
    camera.lookAt(0, 0.97, 0);
    app.root.addChild(camera);

    const key = new pc.Entity('Warm key');
    key.addComponent('light', { type: 'directional', intensity: 1.6, castShadows: true, shadowResolution: 1024,
        color: new pc.Color(1, 0.88, 0.72) });
    key.setEulerAngles(45, 145, 0);
    app.root.addChild(key);
    const fill = new pc.Entity('Cool fill');
    fill.addComponent('light', { type: 'directional', intensity: 0.55, color: new pc.Color(0.55, 0.74, 0.86) });
    fill.setEulerAngles(25, -65, 0);
    app.root.addChild(fill);

    const stool = new pc.Entity('Sit preview stool');
    stool.addComponent('render', { type: 'cylinder', castShadows: true });
    stool.setLocalScale(0.98, 0.08, 0.62);
    stool.setPosition(0, 0.38, -0.18);
    const wood = new pc.StandardMaterial();
    wood.diffuse = new pc.Color(0.29, 0.17, 0.10);
    wood.gloss = 0.08;
    wood.update();
    stool.render.material = wood;
    const stoolLegs = [-0.34, 0.34].map((x) => {
        const leg = new pc.Entity('Sit preview stool leg');
        leg.addComponent('render', { type: 'cylinder', castShadows: true });
        leg.setLocalScale(0.12, 0.38, 0.12);
        leg.setPosition(x, 0.16, -0.18);
        leg.render.material = wood;
        return leg;
    });

    const pivot = new pc.Entity('Turntable');
    app.root.addChild(pivot);
    pivot.addChild(stool);
    for (const leg of stoolLegs) pivot.addChild(leg);
    const asset = new pc.Asset('199 KB trader', 'container', { url: './assets/models/characters/examples/viking-trader-199kb.glb' });
    const loaded = new Promise((resolve, reject) => {
        asset.once('load', () => resolve(asset));
        asset.once('error', (error) => reject(error || new Error('Could not load the GLB')));
    });
    app.assets.add(asset);
    app.assets.load(asset);
    await loaded;
    const model = asset.resource.instantiateRenderEntity({ castShadows: true });
    model.setLocalPosition(0, 0.96, 0);
    pivot.addChild(model);
    joints = Object.fromEntries(JOINTS.map((joint) => [joint, model.findByName(joint)]));
    if (Object.values(joints).some((joint) => !joint)) throw new Error('The sample rig is incomplete');
    eyelids = EYELIDS.map((eyelid) => model.findByName(eyelid));
    if (eyelids.some((eyelid) => !eyelid)) throw new Error('The sample eyelids are missing');
    status.textContent = '198.7 KB · ready';

    app.on('update', (dt) => {
        elapsed += Math.min(dt, 0.05);
        const pose = poseAt(clip, elapsed);
        for (const joint of JOINTS) joints[joint].setLocalEulerAngles(...pose.rotations[joint]);
        for (const eyelid of eyelids) eyelid.setLocalScale(1, blinkAmount(clip, elapsed), 1);
        joints.WalkRoot.setLocalPosition(0, pose.rise, 0);
        pivot.setLocalEulerAngles(0, yaw, 0);
        stool.enabled = clip === 'sit';
        for (const leg of stoolLegs) leg.enabled = clip === 'sit';
    });
    const resize = () => {
        const rect = canvas.getBoundingClientRect();
        if (rect.width && rect.height) app.resizeCanvas(Math.round(rect.width), Math.round(rect.height));
    };
    new ResizeObserver(resize).observe(canvas);
    app.start();
    resize();
} catch (error) {
    status.textContent = 'Preview unavailable';
    console.error(error);
}
