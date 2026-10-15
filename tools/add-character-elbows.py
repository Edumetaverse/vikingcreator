"""Add deforming elbow joints to both studio tiers for the seated pose.

Run after constructing the nine-joint studio meshes and before adding blink
meshes. The bind pose stays unchanged; only forearm vertices gain elbow weight.
"""
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters'
NAMES = ('Chief', 'Farmer', 'FemaleTrader', 'Sheildmaiden', 'Warrior')


def smooth(a, b, value):
    t = min(1.0, max(0.0, (value - a) / (b - a)))
    return t * t * (3 - 2 * t)


def pack(document, binary):
    document['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(document, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    binary += b'\0' * (-len(binary) % 4)
    return (b'glTF' + struct.pack('<II', 2, 28 + len(encoded) + len(binary)) +
            struct.pack('<I4s', len(encoded), b'JSON') + encoded +
            struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def accessor_location(document, index, element_size):
    accessor = document['accessors'][index]
    view = document['bufferViews'][accessor['bufferView']]
    return (view.get('byteOffset', 0) + accessor.get('byteOffset', 0),
            view.get('byteStride', element_size), accessor['count'])


def add_elbows(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    at = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, at)[0]
    binary = bytearray(raw[at + 8:at + 8 + binary_length])
    nodes = document['nodes']
    named = {node.get('name'): index for index, node in enumerate(nodes)}
    skin = document['skins'][0]
    old_count = len(skin['joints'])
    assert old_count in (9, 11), (path, old_count)
    arm_ids = {side: skin['joints'].index(named[f'{side}Arm'])
               for side in ('Left', 'Right')}
    elbow_ids = {}
    for side in ('Left', 'Right'):
        if f'{side}Elbow' in named:
            index = named[f'{side}Elbow']
            nodes[index]['translation'] = [0, -0.31, 0]
            elbow_ids[side] = skin['joints'].index(index)
        else:
            elbow_ids[side] = len(skin['joints'])
            index = len(nodes)
            nodes.append({'name': f'{side}Elbow', 'translation': [0, -0.31, 0]})
            nodes[named[f'{side}Arm']].setdefault('children', []).append(index)
            skin['joints'].append(index)

    primitive = document['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    pos_at, pos_stride, count = accessor_location(document, attrs['POSITION'], 12)
    joints_at, joints_stride, _ = accessor_location(document, attrs['JOINTS_0'], 4)
    weights_at, weights_stride, _ = accessor_location(document, attrs['WEIGHTS_0'], 4)
    changed = 0
    for i in range(count):
        y = struct.unpack_from('<f', binary, pos_at + i * pos_stride + 4)[0]
        elbow_share = 1 - smooth(-0.06, 0.09, y)
        if elbow_share <= 0:
            continue
        ids = list(binary[joints_at + i * joints_stride:
                          joints_at + i * joints_stride + 4])
        weights = list(binary[weights_at + i * weights_stride:
                              weights_at + i * weights_stride + 4])
        influences = {}
        for bone, weight in zip(ids, weights):
            influences[bone] = influences.get(bone, 0.0) + weight
        for side in ('Left', 'Right'):
            arm = arm_ids[side]
            elbow = elbow_ids[side]
            total_arm = influences.get(arm, 0) + influences.get(elbow, 0)
            if total_arm:
                influences[arm] = total_arm * (1 - elbow_share)
                influences[elbow] = total_arm * elbow_share
        if not any(influences.get(elbow, 0) for elbow in elbow_ids.values()):
            continue
        chosen = sorted(influences.items(), key=lambda item: item[1], reverse=True)[:4]
        total = sum(weight for _, weight in chosen)
        values = [round(255 * weight / total) for _, weight in chosen]
        values[0] += 255 - sum(values)
        for slot in range(4):
            binary[joints_at + i * joints_stride + slot] = chosen[slot][0] if slot < len(chosen) else 0
            binary[weights_at + i * weights_stride + slot] = values[slot] if slot < len(values) else 0
        changed += 1

    bind_index = skin['inverseBindMatrices']
    bind_at, bind_stride, bind_count = accessor_location(document, bind_index, 64)
    if bind_count == 11:
        for side in ('Left', 'Right'):
            inverse_x = 0.31 if side == 'Left' else -0.31
            struct.pack_into('<2f', binary, bind_at + elbow_ids[side] * bind_stride + 48,
                             inverse_x, -0.01)
    else:
        assert bind_count == 9
        matrices = bytearray()
        for i in range(bind_count):
            matrices.extend(binary[bind_at + i * bind_stride:bind_at + i * bind_stride + 64])
        for side in ('Left', 'Right'):
            inverse_x = 0.31 if side == 'Left' else -0.31
            matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0,
                      inverse_x, -0.01, 0, 1]
            matrices.extend(struct.pack('<16f', *matrix))
        binary.extend(b'\0' * (-len(binary) % 4))
        view_index = len(document['bufferViews'])
        document['bufferViews'].append({
            'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(matrices)
        })
        binary.extend(matrices)
        document['accessors'][bind_index]['bufferView'] = view_index
        document['accessors'][bind_index]['byteOffset'] = 0
        document['accessors'][bind_index]['count'] = len(skin['joints'])
    path.write_bytes(pack(document, binary))
    print(f'{path.name}: {changed} forearm vertices, {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    for tier in ('studio', 'studio-high'):
        for name in NAMES:
            add_elbows(ROOT / tier / f'{name}.glb')
