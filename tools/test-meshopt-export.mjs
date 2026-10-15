import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { NodeIO } from '@gltf-transform/core';
import { EXTMeshoptCompression } from '@gltf-transform/extensions';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import { buildCharacterGlb } from '../src/character-studio-core.js';

const io = new NodeIO().registerExtensions([EXTMeshoptCompression])
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
await MeshoptEncoder.ready;
await MeshoptDecoder.ready;

for (const name of ['Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior',
    'ElderSeer', 'ShieldBearer', 'Blacksmith', 'ArmoredJarl']) {
    const source = readFileSync(`assets/models/characters/studio-high/${name}.glb`);
    const input = source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength);
    const raw = buildCharacterGlb(input, null, name);
    const before = await io.readBinary(new Uint8Array(raw));
    const document = await io.readBinary(new Uint8Array(raw));
    document.createExtension(EXTMeshoptCompression).setRequired(true)
        .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
    const packed = await io.writeBinary(document);
    const restored = await io.readBinary(packed);
    const oldRoot = before.getRoot(), newRoot = restored.getRoot();
    assert.deepEqual(newRoot.listAnimations().map((a) => a.getName()),
        oldRoot.listAnimations().map((a) => a.getName()));
    assert.equal(newRoot.listMeshes().length, oldRoot.listMeshes().length);
    for (let i = 0; i < oldRoot.listAnimations().length; i++) {
        const oldSamplers = oldRoot.listAnimations()[i].listSamplers();
        const newSamplers = newRoot.listAnimations()[i].listSamplers();
        assert.equal(newSamplers.length, oldSamplers.length);
        for (let j = 0; j < oldSamplers.length; j++) {
            assert.deepEqual(newSamplers[j].getInput().getArray(), oldSamplers[j].getInput().getArray());
            assert.deepEqual(newSamplers[j].getOutput().getArray(), oldSamplers[j].getOutput().getArray());
        }
    }
    for (let i = 0; i < oldRoot.listSkins().length; i++) {
        assert.deepEqual(newRoot.listSkins()[i].getInverseBindMatrices().getArray(),
            oldRoot.listSkins()[i].getInverseBindMatrices().getArray());
    }
    for (let i = 0; i < oldRoot.listMeshes().length; i++) {
        const oldPrims = oldRoot.listMeshes()[i].listPrimitives();
        const newPrims = newRoot.listMeshes()[i].listPrimitives();
        assert.equal(newPrims.length, oldPrims.length);
        for (let j = 0; j < oldPrims.length; j++) {
            const oldPrim = oldPrims[j], newPrim = newPrims[j];
            for (const key of oldPrim.listSemantics()) {
                const a = oldPrim.getAttribute(key).getArray();
                const b = newPrim.getAttribute(key).getArray();
                assert.deepEqual(b, a, `${name} ${key} changed`);
            }
            if (oldPrim.getIndices()) {
                const a = oldPrim.getIndices().getArray(), b = newPrim.getIndices().getArray();
                assert.equal(b.length, a.length);
                for (let k = 0; k < a.length; k += 3) {
                    const triangle = [a[k], a[k + 1], a[k + 2]];
                    assert.ok([0, 1, 2].some((turn) =>
                        b[k] === triangle[turn] && b[k + 1] === triangle[(turn + 1) % 3] &&
                        b[k + 2] === triangle[(turn + 2) % 3]), `${name} triangle ${k / 3} changed`);
                }
            }
        }
    }
    const oldImages = oldRoot.listTextures().map((t) => t.getImage());
    const newImages = newRoot.listTextures().map((t) => t.getImage());
    assert.equal(newImages.length, oldImages.length);
    for (let i = 0; i < oldImages.length; i++) assert.deepEqual(newImages[i], oldImages[i]);
    assert.ok(packed.byteLength < raw.byteLength);
    console.log(`${name}: ${raw.byteLength} -> ${packed.byteLength} bytes (${(100 * (1 - packed.byteLength / raw.byteLength)).toFixed(1)}% smaller)`);
}
