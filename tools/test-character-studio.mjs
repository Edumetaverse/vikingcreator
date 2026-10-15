import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildCharacterGlb, parseGlb, CLIPS, JOINTS, EYELIDS, poseAt, blinkAmount } from '../src/character-studio-core.js';

const names = ['Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior'];
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
    assert.equal(json.animations[0].channels.length, JOINTS.length + 1 + EYELIDS.length);
    for (const eyelid of EYELIDS) assert.ok(json.nodes.some((node) => node.name === eyelid));
    assert.ok(json.extensionsRequired.includes('KHR_mesh_quantization'));
    for (const animation of json.animations) {
        for (const sampler of animation.samplers) {
            const times = json.accessors[sampler.input];
            const values = json.accessors[sampler.output];
            assert.equal(times.count, values.count);
            assert.ok(times.count >= (animation.name === 'Idle' ? 5 : 13));
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

const idleA = poseAt('idle', 0), idleB = poseAt('idle', 0.61);
assert.equal(idleA.rise, 0);
assert.equal(idleB.rise, 0);
for (const joint of ['WalkRoot', 'LeftThigh', 'RightThigh', 'LeftShin', 'RightShin', 'LeftArm', 'RightArm'])
    assert.deepEqual(idleA.rotations[joint], idleB.rotations[joint], `${joint} must remain planted at idle`);
assert.notDeepEqual(idleA.rotations.Head, idleB.rotations.Head);
assert.notDeepEqual(idleA.rotations.Chest, idleB.rotations.Chest);
assert.ok(blinkAmount('idle', 1.2) > 0.84);
assert.equal(blinkAmount('idle', 0), 0.001);
assert.equal(blinkAmount('sit', 1.2), 0.001);
const seatedA = poseAt('sit', 0), seatedB = poseAt('sit', 1);
assert.deepEqual(seatedA, seatedB, 'Seated pose must not wobble');
for (const side of ['Left', 'Right']) {
    assert.ok(seatedA.rotations[`${side}Thigh`][0] < -80, 'Knees must bend forwards');
    assert.equal(seatedA.rotations[`${side}Thigh`][0] + seatedA.rotations[`${side}Shin`][0], 0,
        'Shins must hang down from the knees');
}
