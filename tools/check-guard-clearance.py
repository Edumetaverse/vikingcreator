"""Check Guard forearm clearance from torso and garment mesh vertices."""
import json
import math
import struct
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POSE = json.loads(subprocess.check_output([
    'node', '--input-type=module', '-e',
    "import {poseAt} from './src/character-studio-core.js'; console.log(JSON.stringify(poseAt('guard',Number(process.env.GUARD_TIME||0))))",
], cwd=ROOT, text=True))


def evaluate(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    binary = raw[20 + json_length + 8:]
    nodes = document['nodes']
    parents = {child: parent for parent, node in enumerate(nodes)
               for child in node.get('children', [])}

    def data(index, dtype, width):
        entry = document['accessors'][index]
        view = document['bufferViews'][entry['bufferView']]
        offset = view.get('byteOffset', 0) + entry.get('byteOffset', 0)
        stride = view.get('byteStride', np.dtype(dtype).itemsize * width)
        return np.array([np.frombuffer(binary, dtype=dtype, count=width,
                                       offset=offset + i * stride)
                         for i in range(entry['count'])])

    primitive = document['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    rest = data(attrs['POSITION'], '<f4', 3)
    ids = data(attrs['JOINTS_0'], 'u1', 4)
    weights = data(attrs['WEIGHTS_0'], 'u1', 4) / 255
    skin = document['skins'][0]
    ibm = data(skin['inverseBindMatrices'], '<f4', 16)
    ibm = np.array([entry.reshape((4, 4), order='F') for entry in ibm])
    named = {node.get('name'): i for i, node in enumerate(nodes)}
    joint_slots = {nodes[index]['name']: slot for slot, index in enumerate(skin['joints'])}

    matrices = {}

    def world(index):
        if index in matrices:
            return matrices[index]
        node = nodes[index]
        local = np.eye(4)
        local[:3, 3] = node.get('translation', [0, 0, 0])
        name = node.get('name')
        if name == 'WalkRoot':
            local[1, 3] += POSE['rise']
        x, y, z = (math.radians(v) for v in POSE['rotations'].get(name, [0, 0, 0]))
        cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
        rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        local[:3, :3] = rx @ ry @ rz
        parent = parents.get(index)
        matrices[index] = (world(parent) @ local if parent is not None else local)
        return matrices[index]

    skin_matrices = np.array([world(index) @ ibm[slot]
                              for slot, index in enumerate(skin['joints'])])
    homogeneous = np.c_[rest, np.ones(len(rest))]
    posed = np.zeros((len(rest), 4))
    for slot in range(4):
        posed += weights[:, slot, None] * np.einsum(
            'nij,nj->ni', skin_matrices[ids[:, slot]], homogeneous)
    posed = posed[:, :3]

    torso = (((ids == joint_slots['WalkRoot']) | (ids == joint_slots['Chest'])) * weights).sum(axis=1) > .8
    torso &= (np.abs(rest[:, 0]) < .31) & (rest[:, 1] > -.35) & (rest[:, 1] < .48)
    body = posed[torso]
    arm_influence = (((ids == joint_slots['LeftArm']) | (ids == joint_slots['RightArm']) |
                      (ids == joint_slots['LeftElbow']) | (ids == joint_slots['RightElbow'])) * weights).sum(axis=1)
    garment = (arm_influence < .2) & (rest[:, 1] > -.5) & (rest[:, 1] < .48)
    garment_points = posed[garment]
    print(path.stem, 'torso samples', len(body), end=': ')
    for side in ('Left', 'Right'):
        elbow = joint_slots[f'{side}Elbow']
        forearm = ((ids == elbow) * weights).sum(axis=1) > .65
        forearm &= rest[:, 1] < .17
        arm = posed[forearm]
        if not len(arm):
            print(side, 'no forearm samples', end='; ')
            continue
        clearances = []
        for target in (body, garment_points):
            nearest = []
            for batch in np.array_split(arm, max(1, math.ceil(len(arm) / 100))):
                nearest.extend(np.sqrt(((batch[:, None, :] - target[None, :, :]) ** 2).sum(axis=2)).min(axis=1))
            clearances.append((min(nearest), np.percentile(nearest, 10)))
        print(side, f'torso min/p10 {clearances[0][0]:.3f}/{clearances[0][1]:.3f} m; '
              f'garment min/p10 {clearances[1][0]:.3f}/{clearances[1][1]:.3f} m', end='; ')
        if clearances[1][0] < 0.08:
            raise AssertionError(f'{path.stem} {side} forearm intersects the garment')
    print()


for path in sorted((ROOT / 'assets/models/characters/studio-high').glob('*.glb')):
    evaluate(path)
