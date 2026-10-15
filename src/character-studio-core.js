// Shared pose and GLB export logic for the character studio. Both detail tiers
// have the same nine-joint skin; this module adds authored keyframes.
export const PRESETS = [
    { id: 'Chief', label: 'Chieftain', subtitle: 'Fur cloak · mail · braided beard', initials: 'CH' },
    { id: 'Farmer', label: 'Settler', subtitle: 'Wool tunic · working boots', initials: 'SE' },
    { id: 'FemaleTrader', label: 'Trader', subtitle: 'Linen apron · long braid', initials: 'TR' },
    { id: 'Sheildmaiden', label: 'Shieldmaiden', subtitle: 'Layered dress · beadwork', initials: 'SH' },
    { id: 'Warrior', label: 'Warrior', subtitle: 'Leather vest · bracers', initials: 'WA' }
];

export const DYES = [
    { id: 'original', label: 'Original', color: '#897262', hue: 0, sat: 0 },
    { id: 'fjord', label: 'Fjord blue', color: '#477989', hue: 194, sat: 0.43 },
    { id: 'forest', label: 'Pine green', color: '#556c51', hue: 116, sat: 0.32 },
    { id: 'ochre', label: 'Golden ochre', color: '#a5783e', hue: 36, sat: 0.50 },
    { id: 'wine', label: 'Oxblood', color: '#773c45', hue: 350, sat: 0.43 },
    { id: 'slate', label: 'Slate', color: '#58656d', hue: 206, sat: 0.19 }
];

export const CLIPS = [
    { id: 'idle', label: 'Idle', duration: 2.4, note: 'Planted feet · breath · blink · head tilt' },
    { id: 'walk', label: 'Walk', duration: 1.25, note: 'Grounded travelling gait' },
    { id: 'run', label: 'Run', duration: 0.72, note: 'Fast stride and arm drive' },
    { id: 'sit', label: 'Sit', duration: 2.2, note: 'Resting seated pose' },
    { id: 'guard', label: 'Guard', duration: 1.6, note: 'Ready stance' }
];

export const JOINTS = ['WalkRoot', 'LeftThigh', 'RightThigh', 'LeftShin', 'RightShin', 'LeftArm', 'RightArm', 'Chest', 'Head'];
export const EYELIDS = ['BlinkLeft', 'BlinkRight'];

export function blinkAmount(clipId, seconds) {
    if (clipId !== 'idle') return 0.001;
    const phase = ((seconds % 2.4) + 2.4) % 2.4;
    return Math.max(0.001, 1 - Math.abs(phase - 1.2) / 0.1);
}

export function poseAt(clipId, seconds) {
    const clip = CLIPS.find((item) => item.id === clipId) || CLIPS[0];
    const phase = seconds / clip.duration * Math.PI * 2;
    const s = Math.sin(phase), c = Math.cos(phase);
    const out = Object.fromEntries(JOINTS.map((name) => [name, [0, 0, 0]]));
    let rise = 0;
    if (clipId === 'walk' || clipId === 'run') {
        const run = clipId === 'run';
        const stride = run ? 45 : 30;
        out.LeftThigh[0] = stride * s;
        out.RightThigh[0] = -stride * s;
        out.LeftShin[0] = (run ? 40 : 28) * Math.max(0, -s);
        out.RightShin[0] = (run ? 40 : 28) * Math.max(0, s);
        out.LeftArm[0] = -(run ? 33 : 23) * s;
        out.RightArm[0] = (run ? 33 : 23) * s;
        out.WalkRoot[1] = 2.5 * s;
        out.WalkRoot[2] = 2 * c;
        rise = (run ? 0.055 : 0.026) * (1 - Math.cos(phase * 2)) / 2;
    } else if (clipId === 'sit') {
        // Seat at hip height, thighs almost level, shins vertical and feet planted.
        // Keep the pose still so cloth and armour do not pulse at the joints.
        out.LeftThigh[0] = -80;
        out.RightThigh[0] = -80;
        out.LeftShin[0] = 80;
        out.RightShin[0] = 80;
        out.LeftArm[0] = -28;
        out.RightArm[0] = -28;
        out.Chest[0] = 5;
        rise = -0.26;
    } else if (clipId === 'guard') {
        out.LeftThigh[0] = 9;
        out.RightThigh[0] = -11;
        out.LeftArm[0] = -42 + 3 * s;
        out.RightArm[0] = -54 - 3 * s;
        out.LeftArm[2] = -16;
        out.RightArm[2] = 20;
        out.WalkRoot[1] = 5 * s;
        rise = -0.035;
    } else {
        // Idle is planted. Only the new upper-body joints move.
        out.Chest[0] = 0.9 * s;
        out.Head[1] = 1.3 * s;
        out.Head[2] = 1.7 * c;
    }
    return { rotations: out, rise };
}

export function quaternionFromEuler([x, y, z]) {
    const a = x * Math.PI / 360, b = y * Math.PI / 360, c = z * Math.PI / 360;
    const sx = Math.sin(a), cx = Math.cos(a), sy = Math.sin(b), cy = Math.cos(b), sz = Math.sin(c), cz = Math.cos(c);
    return [sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz, cx * cy * cz + sx * sy * sz];
}

export function parseGlb(buffer) {
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    if (view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2 || view.getUint32(8, true) !== bytes.length)
        throw new Error('This file is not a valid GLB 2.0 asset.');
    const jsonLength = view.getUint32(12, true);
    const json = JSON.parse(new TextDecoder().decode(bytes.slice(20, 20 + jsonLength)));
    const binHead = 20 + jsonLength;
    if (view.getUint32(binHead + 4, true) !== 0x004e4942) throw new Error('GLB binary chunk missing.');
    return { json, binary: bytes.slice(binHead + 8, binHead + 8 + view.getUint32(binHead, true)) };
}

function padded(bytes, pad) {
    const out = new Uint8Array(Math.ceil(bytes.length / 4) * 4);
    out.fill(pad);
    out.set(bytes);
    return out;
}

export function packGlb(json, binary) {
    const encoded = padded(new TextEncoder().encode(JSON.stringify(json)), 0x20);
    const bin = padded(binary, 0);
    const output = new ArrayBuffer(28 + encoded.length + bin.length);
    const view = new DataView(output);
    const bytes = new Uint8Array(output);
    view.setUint32(0, 0x46546c67, true); view.setUint32(4, 2, true); view.setUint32(8, bytes.length, true);
    view.setUint32(12, encoded.length, true); view.setUint32(16, 0x4e4f534a, true);
    bytes.set(encoded, 20);
    const offset = 20 + encoded.length;
    view.setUint32(offset, bin.length, true); view.setUint32(offset + 4, 0x004e4942, true);
    bytes.set(bin, offset + 8);
    return output;
}

export function buildCharacterGlb(sourceBuffer, textureBytes, name, dyeId = 'original') {
    const { json, binary } = parseGlb(sourceBuffer);
    let baseBinary = binary;
    if (textureBytes) {
        const baseTexture = json.materials[0].pbrMetallicRoughness.baseColorTexture.index;
        const imageIndex = json.textures[baseTexture].source;
        const image = json.images[imageIndex];
        const order = json.bufferViews.map((view, index) => ({ index, offset: view.byteOffset || 0 }))
            .sort((a, b) => a.offset - b.offset);
        const chunks = [];
        let packedLength = 0;
        for (const { index } of order) {
            const view = json.bufferViews[index];
            const aligned = (packedLength + 3) & ~3;
            if (aligned > packedLength) chunks.push(new Uint8Array(aligned - packedLength));
            packedLength = aligned;
            const payload = index === image.bufferView ? textureBytes :
                binary.slice(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength);
            view.byteOffset = packedLength;
            view.byteLength = payload.length;
            chunks.push(payload);
            packedLength += payload.length;
        }
        baseBinary = new Uint8Array(packedLength);
        let cursor = 0;
        for (const chunk of chunks) { baseBinary.set(chunk, cursor); cursor += chunk.length; }
        json.images[imageIndex] = { bufferView: image.bufferView, mimeType: 'image/jpeg',
            name: `${dyeId} garment palette` };
    }
    const parts = [baseBinary];
    let length = baseBinary.length;
    const append = (bytes) => {
        const aligned = (length + 3) & ~3;
        if (aligned > length) parts.push(new Uint8Array(aligned - length));
        length = aligned;
        const offset = length;
        parts.push(bytes);
        length += bytes.length;
        const index = json.bufferViews.length;
        json.bufferViews.push({ buffer: 0, byteOffset: offset, byteLength: bytes.length });
        return index;
    };
    const accessor = (floats, type, min, max) => {
        const data = new Float32Array(floats);
        const bytes = new Uint8Array(data.buffer);
        const entry = { bufferView: append(bytes), componentType: 5126,
            count: floats.length / (type === 'SCALAR' ? 1 : type === 'VEC3' ? 3 : 4), type };
        if (min) entry.min = min;
        if (max) entry.max = max;
        const index = json.accessors.length;
        json.accessors.push(entry);
        return index;
    };
    const namedNodes = Object.fromEntries(json.nodes.map((node, index) => [node.name, index]));
    for (const joint of JOINTS) if (namedNodes[joint] === undefined) throw new Error(`Missing rig joint: ${joint}`);
    for (const eyelid of EYELIDS) if (namedNodes[eyelid] === undefined) throw new Error(`Missing blink eyelid: ${eyelid}`);
    json.animations = CLIPS.map((clip) => {
        const count = clip.id === 'idle' ? 13 : 17;
        const times = Array.from({ length: count }, (_, i) => clip.duration * i / (count - 1));
        const timeAccessor = accessor(times, 'SCALAR', [0], [clip.duration]);
        const samplers = [], channels = [];
        for (const joint of JOINTS) {
            const values = times.flatMap((t) => quaternionFromEuler(poseAt(clip.id, t).rotations[joint]));
            const output = accessor(values, 'VEC4');
            channels.push({ sampler: samplers.length, target: { node: namedNodes[joint], path: 'rotation' } });
            samplers.push({ input: timeAccessor, output, interpolation: 'LINEAR' });
        }
        const root = json.nodes[namedNodes.WalkRoot];
        const rest = root.translation || [0, 0, 0];
        const offsets = times.flatMap((t) => [rest[0], rest[1] + poseAt(clip.id, t).rise, rest[2]]);
        channels.push({ sampler: samplers.length, target: { node: namedNodes.WalkRoot, path: 'translation' } });
        samplers.push({ input: timeAccessor, output: accessor(offsets, 'VEC3'), interpolation: 'LINEAR' });
        if (clip.id === 'idle') {
            const blinkTimes = [0, 1.1, 1.2, 1.3, clip.duration];
            const blinkInput = accessor(blinkTimes, 'SCALAR', [0], [clip.duration]);
            const scales = blinkTimes.flatMap((time) => [1, blinkAmount(clip.id, time), 1]);
            const blinkOutput = accessor(scales, 'VEC3');
            for (const eyelid of EYELIDS) {
                channels.push({ sampler: samplers.length, target: { node: namedNodes[eyelid], path: 'scale' } });
                samplers.push({ input: blinkInput, output: blinkOutput, interpolation: 'LINEAR' });
            }
        }
        return { name: clip.label, samplers, channels };
    });
    json.asset = { ...json.asset, generator: 'Viking Character Forge' };
    json.scene = json.scene ?? 0;
    json.scenes[json.scene].name = name || 'Viking character';
    json.buffers[0].byteLength = (length + 3) & ~3;
    const output = new Uint8Array(json.buffers[0].byteLength);
    let at = 0;
    for (const part of parts) { output.set(part, at); at += part.length; }
    return packGlb(json, output);
}
