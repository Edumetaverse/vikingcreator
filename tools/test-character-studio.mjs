import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildCharacterGlb, parseGlb, PRESETS, CLIPS, JOINTS, EYELIDS, poseAt, blinkAmount, blinkKeyframes } from '../src/character-studio-core.js';

const names = ['Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior'];
const newNames = ['ElderSeer', 'ShieldBearer', 'Blacksmith', 'ArmoredJarl'];
assert.equal(PRESETS.length, 9);
assert.deepEqual(PRESETS.slice(5).map((preset) => preset.id), newNames);
assert.deepEqual(CLIPS.map((clip) => clip.label), ['Idle', 'Blink', 'Walk', 'Run']);
for (const name of names) {
    const file = readFileSync(`assets/models/characters/studio/${name}.glb`);
    const input = file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength);
    const original = parseGlb(input);
    const output = buildCharacterGlb(input, null, name);
    assert.ok(output.byteLength < 200_000, `${name} must export under 200 KB`);
    const { json, binary } = parseGlb(output);
    assert.equal(json.buffers[0].byteLength, binary.length);
    assert.deepEqual(json.animations.map((clip) => clip.name), CLIPS.map((clip) => clip.label));
    assert.equal(json.skins[0].joints.length, JOINTS.length);
    assert.equal(json.accessors[json.skins[0].inverseBindMatrices].count, JOINTS.length);
    assert.equal(json.animations[0].channels.filter((channel) => channel.target.path === 'weights').length, EYELIDS.length);
    for (const eyelid of EYELIDS) assert.ok(json.nodes.some((node) => node.name === eyelid));
    const readFloats = (index) => {
        const entry = json.accessors[index];
        const view = json.bufferViews[entry.bufferView];
        const offset = (view.byteOffset || 0) + (entry.byteOffset || 0);
        const bytes = new DataView(binary.buffer, binary.byteOffset, binary.byteLength);
        return Array.from({ length: entry.count }, (_, i) => bytes.getFloat32(offset + i * 4, true));
    };
    for (const clipId of ['idle', 'blink']) {
        const index = CLIPS.findIndex((clip) => clip.id === clipId);
        const animation = json.animations[index];
        const lidIndex = json.nodes.findIndex((node) => node.name === 'BlinkLeft');
        const channel = animation.channels.find((item) => item.target.node === lidIndex && item.target.path === 'weights');
        assert.ok(channel, `${clipId} must animate the eyelid mesh`);
        const sampler = animation.samplers[channel.sampler];
        const times = readFloats(sampler.input);
        const values = readFloats(sampler.output);
        const expected = blinkKeyframes(clipId);
        assert.equal(times.length, expected.length);
        for (let i = 0; i < times.length; i++) {
            assert.ok(Math.abs(times[i] - expected[i]) < 1e-5, `${clipId} blink time ${i} must export`);
            assert.ok(Math.abs(values[i] - blinkAmount(clipId, expected[i])) < 1e-5,
                `${clipId} blink weight ${i} must match the preview`);
        }
    }
    const leftArm = json.nodes.find((node) => node.name === 'LeftArm');
    const rightArm = json.nodes.find((node) => node.name === 'RightArm');
    assert.ok(leftArm.children.some((index) => json.nodes[index].name === 'LeftElbow'));
    assert.ok(rightArm.children.some((index) => json.nodes[index].name === 'RightElbow'));
    for (const side of ['Left', 'Right']) {
        const lidNode = json.nodes.find((node) => node.name === `Blink${side}`);
        const lidMesh = json.meshes[lidNode.mesh];
        assert.equal(lidMesh.primitives[0].targets.length, 1, 'Eyelids must morph on the mesh');
        const target = json.accessors[lidMesh.primitives[0].targets[0].POSITION];
        assert.equal(target.count, 6);
        const blinkChannel = json.animations[0].channels.find((channel) =>
            channel.target.node === json.nodes.indexOf(lidNode) && channel.target.path === 'weights');
        assert.ok(blinkChannel, 'Idle must animate the actual eyelid morph');
    }
    assert.ok(json.extensionsRequired.includes('KHR_mesh_quantization'));
    for (const animation of json.animations) {
        for (const sampler of animation.samplers) {
            const times = json.accessors[sampler.input];
            const values = json.accessors[sampler.output];
            assert.equal(times.count, values.count);
            assert.ok(times.count >= (animation.name === 'Blink' ? 2 : animation.name === 'Idle' ? 30 : 13));
            assert.equal(sampler.interpolation, 'LINEAR');
        }
    }
    const imageIndex = json.textures[json.materials[0].pbrMetallicRoughness.baseColorTexture.index].source;
    const view = original.json.bufferViews[original.json.images[imageIndex].bufferView];
    const image = original.binary.slice(view.byteOffset, view.byteOffset + view.byteLength);
    const dyed = buildCharacterGlb(input, image, `${name} recolored`, 'fjord');
    assert.ok(dyed.byteLength < 200_000, `${name} replacement texture must fit`);
    const replacement = parseGlb(dyed);
    assert.equal(replacement.json.images[imageIndex].mimeType, 'image/jpeg');
    assert.equal(replacement.json.buffers[0].byteLength, replacement.binary.length);
    console.log(`${name}: ${output.byteLength.toLocaleString()} bytes, ${CLIPS.length} clips, ${JOINTS.length} joints`);

    const highFile = readFileSync(`assets/models/characters/studio-high/${name}.glb`);
    const highInput = highFile.buffer.slice(highFile.byteOffset, highFile.byteOffset + highFile.byteLength);
    const highSource = parseGlb(highInput);
    const highOutput = buildCharacterGlb(highInput, null, `${name} high detail`);
    const high = parseGlb(highOutput);
    assert.ok(highOutput.byteLength > output.byteLength, `${name} high detail must retain more data`);
    assert.ok(high.json.accessors[high.json.meshes[0].primitives[0].attributes.POSITION].count > 7000);
    assert.equal(high.json.images.length, 3, 'High detail retains color, normal and surface maps');
    assert.equal(high.json.skins[0].joints.length, JOINTS.length);
    assert.equal(high.json.accessors[high.json.skins[0].inverseBindMatrices].count, JOINTS.length);
    assert.deepEqual(high.json.animations.map((clip) => clip.name), CLIPS.map((clip) => clip.label));
    const highTexture = highSource.json.materials[0].pbrMetallicRoughness.baseColorTexture.index;
    const highImage = highSource.json.images[highSource.json.textures[highTexture].source];
    const highView = highSource.json.bufferViews[highImage.bufferView];
    const highBytes = highSource.binary.slice(highView.byteOffset, highView.byteOffset + highView.byteLength);
    const highDyed = parseGlb(buildCharacterGlb(highInput, highBytes, `${name} recolored`, 'fjord'));
    assert.equal(highDyed.json.images[highSource.json.textures[highTexture].source].mimeType, 'image/jpeg');
    assert.equal(highDyed.json.buffers[0].byteLength, highDyed.binary.length);
    console.log(`${name} high detail: ${highOutput.byteLength.toLocaleString()} bytes`);
}

for (const name of newNames) {
    const file = readFileSync(`assets/models/characters/studio-high/${name}.glb`);
    const input = file.buffer.slice(file.byteOffset, file.byteOffset + file.byteLength);
    const source = parseGlb(input);
    const exported = parseGlb(buildCharacterGlb(input, null, name));
    const { json } = exported;
    assert.deepEqual(json.animations.map((clip) => clip.name), CLIPS.map((clip) => clip.label));
    assert.equal(json.skins[0].joints.length, JOINTS.length);
    assert.equal(json.images.length, 3);
    assert.ok(json.accessors[json.meshes[0].primitives[0].attributes.POSITION].count > 7000);
    assert.ok(json.nodes.some((node) => node.name?.startsWith(`Accessory_${name}_`)));
    assert.ok(json.meshes.length > 3);
    for (const lid of EYELIDS) assert.ok(json.nodes.some((node) => node.name === lid));
    const textureIndex = source.json.materials[0].pbrMetallicRoughness.baseColorTexture.index;
    const imageIndex = source.json.textures[textureIndex].source;
    const view = source.json.bufferViews[source.json.images[imageIndex].bufferView];
    const image = source.binary.slice(view.byteOffset, view.byteOffset + view.byteLength);
    const dyed = parseGlb(buildCharacterGlb(input, image, `${name} recolored`, 'oxblood'));
    assert.equal(dyed.json.images[imageIndex].mimeType, 'image/jpeg');
    assert.equal(dyed.json.meshes.length, json.meshes.length);
    assert.equal(dyed.json.materials.length, json.materials.length);
    console.log(`${name} high detail: ${exported.binary.byteLength.toLocaleString()} binary bytes`);
}

const idleA = poseAt('idle', 0), idleB = poseAt('idle', 0.61);
assert.equal(idleA.rise, 0);
assert.equal(idleB.rise, 0);
for (const joint of ['WalkRoot', 'LeftThigh', 'RightThigh', 'LeftShin', 'RightShin', 'LeftArm', 'RightArm'])
    assert.deepEqual(idleA.rotations[joint], idleB.rotations[joint], `${joint} must remain planted at idle`);
assert.notDeepEqual(idleA.rotations.Head, idleB.rotations.Head);
assert.notDeepEqual(idleA.rotations.Chest, idleB.rotations.Chest);
const idleBlinkStart = blinkKeyframes('idle')[1];
const soloBlinkStart = blinkKeyframes('blink')[1];
assert.ok(Math.abs(blinkAmount('idle', idleBlinkStart + 0.14) - 1) < 1e-9);
assert.ok(Math.abs(blinkAmount('blink', soloBlinkStart + 0.14) - 1) < 1e-9);
assert.equal(blinkAmount('blink', 0), 0);
assert.equal(blinkAmount('idle', 0), 0);
assert.equal(blinkAmount('idle', idleBlinkStart + 0.5), 0, 'A blink must finish before the next one');
assert.equal(blinkAmount('idle', 28.8), 0, 'Idle morph must have an open-eye loop boundary');
assert.ok(Array.from({ length: 2880 }, (_, i) => blinkAmount('idle', 28.8 + i / 100))
    .some((amount) => amount > 0.95), 'Later Idle cycles must also blink');
assert.equal(blinkKeyframes('idle').length, 30, 'Idle exports seven irregular blinks');
assert.equal(blinkKeyframes('blink').length, 18, 'Blink exports four irregular blinks');
const starts = blinkKeyframes('blink').slice(1, -1).filter((_, index) => index % 4 === 0);
const gaps = starts.slice(1).map((time, index) => time - starts[index]);
assert.ok(Math.max(...gaps) - Math.min(...gaps) > 1, 'Blink spacing must vary');
const walkContact = poseAt('walk', 0);
const walkOpposite = poseAt('walk', CLIPS.find((clip) => clip.id === 'walk').duration / 2);
assert.equal(walkContact.rotations.WalkRoot[1], 0, 'Walk must not yaw the pelvis');
assert.equal(walkContact.rotations.WalkRoot[2], 0, 'Walk must not roll the pelvis');
assert.equal(walkContact.rotations.LeftThigh[0], walkOpposite.rotations.RightThigh[0]);
assert.ok(poseAt('walk', 0.78).rotations.LeftShin[0] > 30, 'Swing leg must lift to clear the ground');
