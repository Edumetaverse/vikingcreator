"""Print seated foot clearance for the current studio meshes (diagnostic)."""
import json
import math
import struct
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / 'assets/models/characters/studio-high'
ANGLES = {'LeftThigh': -75, 'RightThigh': -75, 'LeftShin': 75, 'RightShin': 75,
          'LeftArm': -30, 'RightArm': -30, 'LeftElbow': -45, 'RightElbow': -45,
          'Chest': 7, 'Head': -2, 'FrontGarment': -65, 'FrontHem': 50}


def evaluate(path):
    raw = path.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    binary = raw[20 + json_length + 8:]
    nodes = document['nodes']
    parents = {}
    for parent, node in enumerate(nodes):
        for child in node.get('children', []):
            parents[child] = parent
    names = {node.get('name'): i for i, node in enumerate(nodes)}

    def data(accessor_index, dtype, width):
        accessor = document['accessors'][accessor_index]
        view = document['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', np.dtype(dtype).itemsize * width)
        return np.array([np.frombuffer(binary, dtype=dtype, count=width,
                                       offset=offset + i * stride)
                         for i in range(accessor['count'])])

    primitive = document['meshes'][0]['primitives'][0]
    attrs = primitive['attributes']
    pos = data(attrs['POSITION'], '<f4', 3)
    ids = data(attrs['JOINTS_0'], 'u1', 4)
    weights = data(attrs['WEIGHTS_0'], 'u1', 4) / 255
    skin = document['skins'][0]
    ibm = data(skin['inverseBindMatrices'], '<f4', 16)
    ibm = np.array([matrix.reshape((4, 4), order='F') for matrix in ibm])

    transforms = {}

    def global_matrix(index):
        if index in transforms:
            return transforms[index]
        node = nodes[index]
        local = np.eye(4)
        local[:3, 3] = node.get('translation', [0, 0, 0])
        if node.get('name') == 'WalkRoot':
            local[1, 3] = -0.24
        angle = math.radians(ANGLES.get(node.get('name'), 0))
        c, s = math.cos(angle), math.sin(angle)
        rotation = np.array([[1, 0, 0, 0], [0, c, -s, 0],
                             [0, s, c, 0], [0, 0, 0, 1]])
        local = local @ rotation
        parent = parents.get(index)
        transforms[index] = (global_matrix(parent) @ local if parent is not None else local)
        return transforms[index]

    skin_matrices = np.array([global_matrix(index) @ ibm[i]
                              for i, index in enumerate(skin['joints'])])
    rest = np.c_[pos, np.ones(len(pos))]
    posed = np.zeros((len(pos), 4))
    for slot in range(4):
        transformed = np.einsum('nij,nj->ni', skin_matrices[ids[:, slot]], rest)
        posed += weights[:, slot, None] * transformed
    posed[:, 1] += 0.96
    boots = pos[:, 1] < -0.72
    print(path.stem, 'boot min/max Y', posed[boots, 1].min(), posed[boots, 1].max(),
          'boot median', np.median(posed[boots, 1]))


if __name__ == '__main__':
    for file in ROOT.glob('*.glb'):
        evaluate(file)
