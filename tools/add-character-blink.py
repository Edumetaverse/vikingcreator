"""Fit morphing eyelid meshes directly to each studio character's face.

Run after rebuilding the compact and high-detail assets. Eye centres and lash
heights are art-directed, while the depth of every eyelid vertex is sampled
from the rendered head mesh. The closed shape is a glTF morph target, so the
Idle blink works in exported GLBs as well as the studio preview.
"""
import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters'
EYES = {
    # centre x, half-spacing, upper eye line above Head joint, extra closure
    'Chief': (-0.005, 0.041, 0.176, 0.007),
    'Farmer': (0.005, 0.041, 0.170, 0.004),
    'FemaleTrader': (0.004, 0.041, 0.176, 0.003),
    'Sheildmaiden': (0.008, 0.043, 0.168, 0.003),
    'Warrior': (0.002, 0.042, 0.172, 0),
}

X_OFFSETS = (-0.023, 0, 0.023)
UPPER_Y = (0.003, 0.004, 0.003)
LOWER_CLOSED_Y = (-0.013, -0.017, -0.013)
CLEARANCE = 0.0025


def unpack(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    at = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, at)[0]
    return document, bytearray(raw[at + 8:at + 8 + binary_length])


def pack(document, binary):
    document['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(document, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    return (b'glTF' + struct.pack('<II', 2, 28 + len(encoded) + len(binary)) +
            struct.pack('<I4s', len(encoded), b'JSON') + encoded +
            struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def read_accessor(document, binary, index):
    entry = document['accessors'][index]
    view = document['bufferViews'][entry['bufferView']]
    count = entry['count']
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[entry['type']]
    fmt = {5123: 'H', 5125: 'I', 5126: 'f'}[entry['componentType']]
    item_size = struct.calcsize('<' + fmt * width)
    start = view.get('byteOffset', 0) + entry.get('byteOffset', 0)
    stride = view.get('byteStride', item_size)
    values = [struct.unpack_from('<' + fmt * width, binary, start + i * stride)
              for i in range(count)]
    if entry.get('normalized') and entry['componentType'] == 5123:
        return [tuple(value / 65535 for value in row) for row in values]
    return values


def front_sample(vertices, triangles, uvs, x, y):
    front = -math.inf
    front_uv = None
    for i, j, k in triangles:
        a, b, c = vertices[i], vertices[j], vertices[k]
        if x < min(a[0], b[0], c[0]) or x > max(a[0], b[0], c[0]):
            continue
        if y < min(a[1], b[1], c[1]) or y > max(a[1], b[1], c[1]):
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-10:
            continue
        u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
        v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
        if u < -1e-5 or v < -1e-5 or u + v > 1.00001:
            continue
        z = u * a[2] + v * b[2] + (1 - u - v) * c[2]
        if z > front:
            front = z
            front_uv = (u * uvs[i][0] + v * uvs[j][0] + (1-u-v) * uvs[k][0],
                        u * uvs[i][1] + v * uvs[j][1] + (1-u-v) * uvs[k][1])
    if not math.isfinite(front):
        raise ValueError(f'No face triangle at eye sample ({x:.4f}, {y:.4f})')
    return front + CLEARANCE, front_uv


def strip_previous_blink(document, binary):
    old = next((i for i, mesh in enumerate(document['meshes'])
                if mesh.get('name') in ('Blink eyelid pair', 'Blink Left eyelid')), None)
    if old is None:
        return binary
    primitive = document['meshes'][old]['primitives'][0]
    first_material = primitive['material']
    document['meshes'] = document['meshes'][:old]
    if first_material:
        document['materials'] = document['materials'][:first_material]
    # Keep the old accessor and buffer slots. The elbow script appended inverse
    # bind matrices after the original lids, so truncating the binary here
    # would silently corrupt the skin. Unreferenced eyelid bytes are harmless.
    return binary


def add_blink(path, centre, spacing, height, extra_close):
    document, binary = unpack(path)
    binary = strip_previous_blink(document, binary)
    main = document['meshes'][0]['primitives'][0]
    vertices = read_accessor(document, binary, main['attributes']['POSITION'])
    uvs = read_accessor(document, binary, main['attributes']['TEXCOORD_0'])
    indices = read_accessor(document, binary, main['indices'])
    triangles = [tuple(index[0] for index in indices[i:i + 3])
                 for i in range(0, len(indices), 3)]
    nodes = document['nodes']
    head_index = next(i for i, node in enumerate(nodes) if node.get('name') == 'Head')
    head_height = nodes[head_index]['translation'][1] + next(
        node['translation'][1] for node in nodes if node.get('name') == 'Chest')

    def accessor(payload, component, count, kind, minimum=None, maximum=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        view_index = len(document['bufferViews'])
        document['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload)})
        binary.extend(payload)
        entry = {'bufferView': view_index, 'componentType': component, 'count': count, 'type': kind}
        if minimum is not None:
            entry['min'] = minimum
        if maximum is not None:
            entry['max'] = maximum
        index = len(document['accessors'])
        document['accessors'].append(entry)
        return index

    normals = accessor(struct.pack('<18f', *([0, 0, 1] * 6)), 5126, 6, 'VEC3')
    indices = accessor(struct.pack('<12H', 0, 3, 1, 1, 3, 4, 1, 4, 2, 2, 4, 5), 5123, 12, 'SCALAR')
    # Sample skin on the bridge of the nose from the character's own texture. Using the
    # face material avoids a flat tint that mismatches each textured complexion.
    skin_uv = front_sample(vertices, triangles, uvs, 0, head_height + height - 0.038)[1]
    uv_accessor = accessor(struct.pack('<12f', *(skin_uv * 6)), 5126, 6, 'VEC2')
    for side, name in [(-1, 'BlinkLeft'), (1, 'BlinkRight')]:
        eye_x = centre + side * spacing
        rest = []
        delta = []
        for row in (0, 1):
            for local_x, top_y, closed_y in zip(X_OFFSETS, UPPER_Y, LOWER_CLOSED_Y):
                open_y = top_y if row == 0 else top_y - 0.001
                final_y = top_y if row == 0 else closed_y - extra_close
                open_z = front_sample(vertices, triangles, uvs, eye_x + local_x, head_height + height + open_y)[0]
                final_z = front_sample(vertices, triangles, uvs, eye_x + local_x, head_height + height + final_y)[0]
                rest.extend((local_x, open_y, open_z))
                delta.extend((0, final_y - open_y, final_z - open_z))
        position = accessor(struct.pack('<18f', *rest), 5126, 6, 'VEC3',
                            [min(rest[::3]), min(rest[1::3]), min(rest[2::3])],
                            [max(rest[::3]), max(rest[1::3]), max(rest[2::3])])
        target = accessor(struct.pack('<18f', *delta), 5126, 6, 'VEC3')
        mesh_index = len(document['meshes'])
        document['meshes'].append({
            'name': f'Blink {"Left" if side < 0 else "Right"} eyelid',
            'weights': [0], 'extras': {'targetNames': ['Blink']},
            'primitives': [{
                'attributes': {'POSITION': position, 'NORMAL': normals, 'TEXCOORD_0': uv_accessor},
                'indices': indices, 'material': main['material'],
                'targets': [{'POSITION': target}],
            }],
        })
        existing = next((node for node in nodes if node.get('name') == name), None)
        if existing is None:
            existing = {'name': name}
            nodes.append(existing)
            nodes[head_index].setdefault('children', []).append(len(nodes) - 1)
        existing.update({'mesh': mesh_index, 'translation': [eye_x, height, 0], 'weights': [0]})
        existing.pop('scale', None)

    path.write_bytes(pack(document, binary))
    print(f'{path.name}: eyelids conformed to face ({path.stat().st_size:,} bytes)')


if __name__ == '__main__':
    for tier in ('studio', 'studio-high'):
        for name, parameters in EYES.items():
            add_blink(ROOT / tier / f'{name}.glb', *parameters)
