import { WebIO } from '@gltf-transform/core';
import { EXTMeshoptCompression } from '@gltf-transform/extensions';
import { MeshoptEncoder } from 'meshoptimizer';

const io = new WebIO()
    .registerExtensions([EXTMeshoptCompression])
    .registerDependencies({ 'meshopt.encoder': MeshoptEncoder });

// EXT_meshopt_compression preserves the source mesh values and JPEG bytes.
// Do not run glTF Transform's meshopt() transform here: its default pipeline
// also quantizes attributes and would change the high-detail source.
export async function compressGlbLosslessly(buffer) {
    await MeshoptEncoder.ready;
    const document = await io.readBinary(new Uint8Array(buffer));
    document.createExtension(EXTMeshoptCompression).setRequired(true)
        .setEncoderOptions({ method: EXTMeshoptCompression.EncoderMethod.QUANTIZE });
    const compressed = await io.writeBinary(document);
    return compressed.byteOffset === 0 && compressed.byteLength === compressed.buffer.byteLength
        ? compressed.buffer : compressed.slice().buffer;
}
