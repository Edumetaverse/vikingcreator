"""Apply the hand-tuned skirt skin weights used by the seated animation.

Run after rebuilding studio and studio-high assets, before adding eyelids. The
patches cover only the Trader and Shieldmaiden skirts. They preserve the source
mesh and textures while anchoring fabric that should not rotate with the legs.
"""
import gzip
import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCHES = Path(__file__).with_name('sit-skin-weights.json.gz')


def accessor_location(document, attribute):
    primitive = document['meshes'][0]['primitives'][0]
    accessor = document['accessors'][primitive['attributes'][attribute]]
    view = document['bufferViews'][accessor['bufferView']]
    stride = view.get('byteStride', 12 if attribute == 'POSITION' else 4)
    return view['byteOffset'] + accessor.get('byteOffset', 0), stride, accessor['count']


def apply(relative_path, patch):
    path = ROOT / relative_path
    raw = bytearray(path.read_bytes())
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    binary_start = 20 + json_length + 8
    positions_at, positions_stride, count = accessor_location(document, 'POSITION')
    digest = hashlib.sha256()
    for i in range(count):
        at = binary_start + positions_at + i * positions_stride
        digest.update(raw[at:at + 12])
    if count != patch['count'] or digest.hexdigest() != patch['positions_sha256']:
        raise ValueError(f'{relative_path}: vertex layout changed; skirt weights need retuning')

    joints_at, joints_stride, _ = accessor_location(document, 'JOINTS_0')
    weights_at, weights_stride, _ = accessor_location(document, 'WEIGHTS_0')
    for index, j0, j1, j2, j3, w0, w1, w2, w3 in patch['vertices']:
        j = binary_start + joints_at + index * joints_stride
        w = binary_start + weights_at + index * weights_stride
        raw[j:j + 4] = bytes((j0, j1, j2, j3))
        raw[w:w + 4] = bytes((w0, w1, w2, w3))
    path.write_bytes(raw)
    print(f'{relative_path}: tuned {len(patch["vertices"])} skirt vertices')


if __name__ == '__main__':
    with gzip.open(PATCHES, 'rt', encoding='utf-8') as source:
        patches = json.load(source)
    for relative_path, patch in patches.items():
        apply(relative_path, patch)
