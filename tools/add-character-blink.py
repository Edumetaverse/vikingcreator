"""Add a tiny animated eyelid mesh to each studio GLB.

Run after rebuilding the compact and high-detail character assets. The eyelids
are children of the existing Head joint, so exported Idle clips can animate
their scale without changing skin weights or the character texture atlas.
"""
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters'
EYES = {
    # centre x, half-spacing, upper eye line y, face depth, eyelid tint
    'Chief': (0.023, 0.032, 0.164, 0.230, (0.94, 0.38, 0.22, 1)),
    'Farmer': (0.005, 0.041, 0.166, 0.185, (0.94, 0.40, 0.24, 1)),
    'FemaleTrader': (0.007, 0.038, 0.170, 0.135, (1, 0.45, 0.32, 1)),
    'Sheildmaiden': (0.022, 0.038, 0.161, 0.247, (1, 0.45, 0.32, 1)),
    'Warrior': (0.007, 0.047, 0.165, 0.155, (0.96, 0.40, 0.23, 1)),
}

# The upper edge stays at the lash line; the lower edge travels over the eye.
# This asymmetric shape closes the painted iris and sclera without growing up
# into the eyebrow.
LID_POSITIONS = [
    -0.022, -0.010, 0, 0, -0.023, 0.003, 0.022, -0.010, 0,
    -0.022, 0.001, 0, 0, 0.004, 0.003, 0.022, 0.001, 0,
]


def pack(document, binary):
    document['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(document, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    output = bytearray(b'glTF')
    output += struct.pack('<II', 2, 28 + len(encoded) + len(binary))
    output += struct.pack('<I4s', len(encoded), b'JSON') + encoded
    output += struct.pack('<I4s', len(binary), b'BIN\0') + binary
    return output


def add_blink(path, centre, spacing, height, depth, color):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    binary_start = 20 + json_length + 8
    binary_length = struct.unpack_from('<I', raw, 20 + json_length)[0]
    binary = bytearray(raw[binary_start:binary_start + binary_length])
    existing = {node.get('name'): node for node in document['nodes']
                if node.get('name') in ('BlinkLeft', 'BlinkRight')}
    if len(existing) == 2:
        existing['BlinkLeft']['translation'] = [centre - spacing, height, depth]
        existing['BlinkRight']['translation'] = [centre + spacing, height, depth]
        mesh = document['meshes'][existing['BlinkLeft']['mesh']]
        material = document['materials'][mesh['primitives'][0]['material']]
        material['pbrMetallicRoughness']['baseColorFactor'] = list(color)
        position = document['accessors'][mesh['primitives'][0]['attributes']['POSITION']]
        view = document['bufferViews'][position['bufferView']]
        offset = view.get('byteOffset', 0) + position.get('byteOffset', 0)
        struct.pack_into('<18f', binary, offset, *LID_POSITIONS)
        position['min'] = [-0.022, -0.023, 0]
        position['max'] = [0.022, 0.004, 0.003]
        path.write_bytes(pack(document, binary))
        print(f'{path.name}: realigned blink ({path.stat().st_size:,} bytes)')
        return

    def accessor(payload, component_type, count, kind, minimum=None, maximum=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        view_index = len(document['bufferViews'])
        document['bufferViews'].append({
            'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(payload)
        })
        binary.extend(payload)
        entry = {
            'bufferView': view_index, 'componentType': component_type,
            'count': count, 'type': kind
        }
        if minimum is not None:
            entry['min'] = minimum
        if maximum is not None:
            entry['max'] = maximum
        index = len(document['accessors'])
        document['accessors'].append(entry)
        return index

    # Two shallow triangles form each closed lid. Only their height scales for
    # the blink; at rest they collapse to a fine line along the upper lash.
    positions = LID_POSITIONS
    normals = [0, 0, 1] * 6
    indices = [0, 1, 2, 3, 4, 1, 1, 4, 5, 1, 5, 2]
    position_accessor = accessor(struct.pack('<18f', *positions), 5126, 6, 'VEC3',
                                 [-0.022, -0.023, 0], [0.022, 0.004, 0.003])
    normal_accessor = accessor(struct.pack('<18f', *normals), 5126, 6, 'VEC3')
    index_accessor = accessor(struct.pack('<12H', *indices), 5123, 12, 'SCALAR')
    material_index = len(document['materials'])
    document['materials'].append({
        'name': 'Blink eyelids', 'doubleSided': True,
        'pbrMetallicRoughness': {
            'baseColorFactor': list(color), 'metallicFactor': 0,
            'roughnessFactor': 1,
        },
    })
    mesh_index = len(document['meshes'])
    document['meshes'].append({
        'name': 'Blink eyelid pair',
        'primitives': [{
            'attributes': {'POSITION': position_accessor, 'NORMAL': normal_accessor},
            'indices': index_accessor, 'material': material_index,
        }],
    })
    head = next(i for i, node in enumerate(document['nodes']) if node.get('name') == 'Head')
    for name, side in [('BlinkLeft', -1), ('BlinkRight', 1)]:
        index = len(document['nodes'])
        document['nodes'].append({
            'name': name, 'mesh': mesh_index,
            'translation': [centre + side * spacing, height, depth],
            'scale': [1, 0.001, 1],
        })
        document['nodes'][head].setdefault('children', []).append(index)

    path.write_bytes(pack(document, binary))
    print(f'{path.name}: {path.stat().st_size:,} bytes with blink')


if __name__ == '__main__':
    for tier in ('studio', 'studio-high'):
        for name, (centre, spacing, height, depth, color) in EYES.items():
            add_blink(ROOT / tier / f'{name}.glb', centre, spacing, height, depth, color)
