"""Move the studio knee pivots to the visible knee without changing rest shape.

Run after building the studio tiers, before adding elbows and blink geometry.
The old lower-leg pivot sat 0.41 m below the hip while the rendered thigh ends
near 0.30 m, making Sit lift the boots above the floor. Matching inverse bind
matrices keep the standing mesh identical.
"""
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters'
NAMES = ('Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior')
THIGH_LENGTH = 0.30


def pack(document, binary):
    document['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(document, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    return (b'glTF' + struct.pack('<II', 2, 28 + len(encoded) + len(binary)) +
            struct.pack('<I4s', len(encoded), b'JSON') + encoded +
            struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def align(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    at = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, at)[0]
    binary = bytearray(raw[at + 8:at + 8 + binary_length])
    nodes = document['nodes']
    named = {node.get('name'): index for index, node in enumerate(nodes)}
    skin = document['skins'][0]
    accessor = document['accessors'][skin['inverseBindMatrices']]
    view = document['bufferViews'][accessor['bufferView']]
    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    stride = view.get('byteStride', 64)
    for side in ('Left', 'Right'):
        thigh = nodes[named[f'{side}Thigh']]
        shin_index = named[f'{side}Shin']
        shin = nodes[shin_index]
        shin['translation'][1] = -THIGH_LENGTH
        joint_index = skin['joints'].index(shin_index)
        inverse_y = -thigh['translation'][1] + THIGH_LENGTH
        struct.pack_into('<f', binary, offset + joint_index * stride + 52, inverse_y)
    path.write_bytes(pack(document, binary))
    print(f'{path.name}: knee pivots at {THIGH_LENGTH:.2f} m')


if __name__ == '__main__':
    for tier in ('studio', 'studio-high'):
        for name in NAMES:
            align(ROOT / tier / f'{name}.glb')
