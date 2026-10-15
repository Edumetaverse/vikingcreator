"""Add two front garment joints for the seated pose without changing the rest mesh.

The existing leg joints cannot also move a long skirt across the lap: their
rotation stretches fabric into the knees. These joints bend front garment
vertices around separate hip and knee pivots, while the back hangs from the
torso. Run after the eleven-joint and eyelid steps on both studio tiers.
"""
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters'
NAMES = ('Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior')


def smooth(start, end, value):
    t = max(0.0, min(1.0, (value - start) / (end - start)))
    return t * t * (3 - 2 * t)


def location(document, index, default_stride):
    entry = document['accessors'][index]
    view = document['bufferViews'][entry['bufferView']]
    return (view.get('byteOffset', 0) + entry.get('byteOffset', 0),
            view.get('byteStride', default_stride), entry['count'])


def pack(document, binary):
    binary.extend(b'\0' * (-len(binary) % 4))
    document['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(document, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    return (b'glTF' + struct.pack('<II', 2, 28 + len(encoded) + len(binary)) +
            struct.pack('<I4s', len(encoded), b'JSON') + encoded +
            struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def add(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    at = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, at)[0]
    binary = bytearray(raw[at + 8:at + 8 + binary_length])
    nodes = document['nodes']
    named = {node.get('name'): i for i, node in enumerate(nodes)}
    if 'FrontGarment' in named:
        raise ValueError(f'{path}: FrontGarment is already present')
    skin = document['skins'][0]
    assert len(skin['joints']) == 11, (path, len(skin['joints']))
    root = named['WalkRoot']
    garment_node = len(nodes)
    garment_bone = len(skin['joints'])
    nodes.append({'name': 'FrontGarment', 'translation': [0, -0.28, 0.15]})
    nodes[root].setdefault('children', []).append(garment_node)
    skin['joints'].append(garment_node)
    hem_node = len(nodes)
    hem_bone = len(skin['joints'])
    nodes.append({'name': 'FrontHem', 'translation': [0, -0.30, 0]})
    nodes[garment_node]['children'] = [hem_node]
    skin['joints'].append(hem_node)

    primitive = document['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    pos_at, pos_stride, count = location(document, attrs['POSITION'], 12)
    joints_at, joints_stride, _ = location(document, attrs['JOINTS_0'], 4)
    weights_at, weights_stride, _ = location(document, attrs['WEIGHTS_0'], 4)
    changed = 0
    long_skirt = path.stem in ('FemaleTrader', 'Sheildmaiden')
    max_share = 0.65 if long_skirt else 0.25
    for i in range(count):
        x, y, z = struct.unpack_from('<3f', binary, pos_at + i * pos_stride)
        if y >= -0.12:
            continue
        ids = list(binary[joints_at + i * joints_stride:joints_at + i * joints_stride + 4])
        weights = list(binary[weights_at + i * weights_stride:
                              weights_at + i * weights_stride + 4])
        influences = {}
        for bone, weight in zip(ids, weights):
            influences[bone] = influences.get(bone, 0) + weight
        leg = sum(influences.get(bone, 0) for bone in (1, 2, 3, 4)) / 255
        arm = sum(influences.get(bone, 0) for bone in (5, 6, 9, 10)) / 255
        down = smooth(0.12, 0.65, -y)
        front = smooth(-0.08, 0.20, z)
        side = 1 - smooth(0.42, 0.72, abs(x))
        cloth = (1 - smooth(0.08, 0.82, leg)) * (1 - smooth(0.05, 0.75, arm))
        share = max_share * down * front * side * cloth
        if share < 0.025:
            continue
        for bone in list(influences):
            influences[bone] *= 1 - share
        lower = smooth(0.40, 0.64, -y) if long_skirt else 0
        influences[garment_bone] = 255 * share * (1 - lower)
        influences[hem_bone] = 255 * share * lower
        chosen = sorted(influences.items(), key=lambda item: item[1], reverse=True)[:4]
        total = sum(weight for _, weight in chosen)
        values = [round(255 * weight / total) for _, weight in chosen]
        values[0] += 255 - sum(values)
        for slot in range(4):
            binary[joints_at + i * joints_stride + slot] = chosen[slot][0] if slot < len(chosen) else 0
            binary[weights_at + i * weights_stride + slot] = values[slot] if slot < len(values) else 0
        changed += 1

    bind_index = skin['inverseBindMatrices']
    bind_at, bind_stride, bind_count = location(document, bind_index, 64)
    assert bind_count == 11
    matrices = bytearray()
    for i in range(bind_count):
        matrices.extend(binary[bind_at + i * bind_stride:bind_at + i * bind_stride + 64])
    matrices.extend(struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0,
                                0, 0, 1, 0, 0, 0.28, -0.15, 1))
    matrices.extend(struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0,
                                0, 0, 1, 0, 0, 0.58, -0.15, 1))
    binary.extend(b'\0' * (-len(binary) % 4))
    view_index = len(document['bufferViews'])
    document['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary),
                                    'byteLength': len(matrices)})
    binary.extend(matrices)
    document['accessors'][bind_index]['bufferView'] = view_index
    document['accessors'][bind_index]['byteOffset'] = 0
    document['accessors'][bind_index]['count'] = 13
    path.write_bytes(pack(document, binary))
    print(f'{path.parent.name}/{path.name}: {changed} garment vertices')


if __name__ == '__main__':
    for tier in ('studio', 'studio-high'):
        for name in NAMES:
            add(ROOT / tier / f'{name}.glb')
