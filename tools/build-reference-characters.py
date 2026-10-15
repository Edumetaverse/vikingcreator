"""Kitbash four rig-compatible Viking presets from the detailed studio meshes.

Accessories are small faceted meshes parented to existing bones. The original
1024px character atlas, skin, and eyelid morphs remain intact, so the studio's
palette controls and four animation clips continue to work on every variant.
"""
from __future__ import annotations

import copy
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'assets/models/characters/studio-high'
VARIANTS = {
    'ElderSeer': 'Chief',
    'ShieldBearer': 'Sheildmaiden',
    'Blacksmith': 'Farmer',
    'ArmoredJarl': 'Warrior',
}

PALETTE = {
    'wood': (0.32, 0.17, 0.08, 0.02),
    'wood_light': (0.47, 0.28, 0.13, 0.02),
    'leather': (0.22, 0.12, 0.08, 0.02),
    'leather_light': (0.41, 0.25, 0.16, 0.02),
    'fur': (0.24, 0.20, 0.17, 0.0),
    'fur_light': (0.42, 0.36, 0.28, 0.0),
    'steel': (0.48, 0.57, 0.63, 0.74),
    'steel_light': (0.67, 0.73, 0.73, 0.72),
    'blade': (0.78, 0.82, 0.79, 0.24),
    'steel_dark': (0.20, 0.29, 0.34, 0.65),
    'iron': (0.24, 0.27, 0.26, 0.72),
    'bronze': (0.61, 0.39, 0.17, 0.67),
    'bone': (0.77, 0.71, 0.53, 0.0),
    'rune': (0.28, 0.62, 0.59, 0.22),
    'skin': (0.70, 0.48, 0.35, 0.0),
    'cloth_dark': (0.15, 0.18, 0.17, 0.0),
}


def vec(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


class Geometry:
    def __init__(self):
        self.parts: dict[str, tuple[list[float], list[float]]] = {}

    def tri(self, material, a, b, c):
        positions, normals = self.parts.setdefault(material, ([], []))
        normal = cross(vec(b, a), vec(c, a))
        length = math.sqrt(sum(value * value for value in normal)) or 1
        normal = tuple(value / length for value in normal)
        for point in (a, b, c):
            positions.extend(point)
            normals.extend(normal)

    def quad(self, material, a, b, c, d):
        self.tri(material, a, b, c)
        self.tri(material, a, c, d)

    def box(self, material, center, size):
        x, y, z = center
        dx, dy, dz = (value / 2 for value in size)
        p = [(x + sx * dx, y + sy * dy, z + sz * dz)
             for sx, sy, sz in [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                                (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]]
        for face in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 4, 7, 3),
                     (1, 2, 6, 5), (3, 7, 6, 2), (0, 1, 5, 4)]:
            self.quad(material, *(p[i] for i in face))

    def rod(self, material, start, end, radius, sides=7):
        direction = vec(end, start)
        axis = (0, 0, 1) if abs(direction[2]) < 0.8 * math.sqrt(sum(v*v for v in direction)) else (1, 0, 0)
        u = cross(direction, axis)
        length = math.sqrt(sum(v*v for v in u)) or 1
        u = tuple(v * radius / length for v in u)
        v = cross(direction, u)
        length = math.sqrt(sum(q*q for q in v)) or 1
        v = tuple(q * radius / length for q in v)
        def ring(point):
            return [tuple(point[k] + math.cos(2*math.pi*i/sides)*u[k] +
                          math.sin(2*math.pi*i/sides)*v[k] for k in range(3))
                    for i in range(sides)]
        lower, upper = ring(start), ring(end)
        for i in range(sides):
            j = (i+1) % sides
            self.quad(material, lower[i], lower[j], upper[j], upper[i])
            self.tri(material, start, lower[j], lower[i])
            self.tri(material, end, upper[i], upper[j])

    def orb(self, material, center, radii, sides=8, bands=4):
        x, y, z = center
        rx, ry, rz = radii
        rings = []
        for j in range(bands + 1):
            phi = math.pi * j / bands
            rings.append([(x + rx * math.sin(phi) * math.cos(2*math.pi*i/sides),
                           y + ry * math.cos(phi),
                           z + rz * math.sin(phi) * math.sin(2*math.pi*i/sides))
                          for i in range(sides)])
        for j in range(bands):
            for i in range(sides):
                k = (i+1) % sides
                self.quad(material, rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i])

    def disc(self, outer, inner, center, radius, z, sides=12):
        x, y = center
        for i in range(sides):
            a = 2*math.pi*i/sides
            b = 2*math.pi*(i+1)/sides
            p = (x + radius*math.cos(a), y + radius*math.sin(a), z)
            q = (x + radius*math.cos(b), y + radius*math.sin(b), z)
            pi = (x + radius*.84*math.cos(a), y + radius*.84*math.sin(a), z + .012)
            qi = (x + radius*.84*math.cos(b), y + radius*.84*math.sin(b), z + .012)
            self.quad(outer, p, q, qi, pi)
            self.tri(inner, (x, y, z + .016), pi, qi)


def seer(parts):
    chest, hand, root = parts['Chest'], parts['LeftElbow'], parts['WalkRoot']
    # Split, ragged over-robe and fur shoulders.
    for side in (-1, 1):
        x = side * .22
        chest.quad('leather', (x-side*.15, .27, -.16), (x+side*.15, .27, -.16),
                   (x+side*.18, -.72, -.25), (x-side*.07, -.69, -.22))
        chest.quad('fur', (x-side*.20, .33, .02), (x+side*.19, .31, .01),
                   (x+side*.24, .15, .06), (x-side*.14, .15, .08))
    # Staff rises above the head, and its fork is unmistakable in silhouette.
    hand.rod('wood', (.07, -.94, .16), (.07, .68, .16), .038, 7)
    hand.rod('wood_light', (.07, .63, .16), (-.08, .91, .17), .027, 6)
    hand.rod('wood_light', (.07, .63, .16), (.22, .91, .17), .027, 6)
    hand.rod('bronze', (.07, -.28, .16), (.07, -.20, .16), .045)
    hand.orb('rune', (.065, .73, .175), (.04, .055, .025), 7, 3)
    for offset in (-.12, 0, .12):
        root.orb('bone', (offset, .15, .27), (.035, .065, .03), 7, 3)


def shield_bearer(parts):
    chest, root = parts['Chest'], parts['WalkRoot']
    # A broad round shield sits behind one shoulder, like the reference.
    chest.disc('steel_dark', 'wood', (.37, .10), .36, -.23, 14)
    chest.orb('bronze', (.37, .10, -.19), (.075, .075, .045), 8, 3)
    for angle in (0, math.pi/2, math.pi, 3*math.pi/2):
        chest.orb('bronze', (.37 + .27*math.cos(angle), .10 + .27*math.sin(angle), -.20),
                  (.023, .023, .014), 6, 3)
    # Narrow harness and small plates preserve the detailed underlying outfit.
    chest.quad('leather_light', (-.22, .27, .24), (-.18, .27, .24),
               (.18, -.13, .265), (.22, -.13, .265))
    for side in (-1, 1):
        for row in range(3):
            x = side * (.14 + .045*(row % 2))
            y = .12 - .09*row
            chest.tri('steel_dark', (x-.035, y+.022, .268), (x+.035, y+.022, .268),
                      (x, y-.04, .275))
    # The belt and original garment supply enough small detail; a second sword
    # would hover away from the animated thigh in walking clips.


def blacksmith(parts):
    root, right = parts['WalkRoot'], parts['RightElbow']
    # Curved, faceted apron follows the tunic instead of masking the torso.
    top = [(-.17, .14, .24), (0, .14, .275), (.17, .14, .24)]
    middle = [(-.20, -.16, .285), (0, -.16, .31), (.20, -.16, .285)]
    bottom = [(-.22, -.48, .31), (0, -.52, .35), (.22, -.48, .31)]
    for row, next_row in ((top, middle), (middle, bottom)):
        for col in range(2):
            root.quad('cloth_dark' if (col + (row is middle)) % 2 else 'leather',
                      row[col], row[col+1], next_row[col+1], next_row[col])
    # Small irregular patches read as worn leather without wide flat straps.
    root.tri('leather_light', (-.16, .105, .267), (-.025, .085, .300),
             (-.11, -.04, .310))
    root.tri('fur', (.055, .085, .298), (.16, .035, .271),
             (.11, -.055, .301))
    root.tri('leather_light', (.015, -.105, .328), (.18, -.09, .292),
             (.10, -.19, .322))
    root.tri('leather_light', (-.16, -.18, .296), (-.05, -.19, .318),
             (-.11, -.32, .331))
    root.tri('fur', (.08, -.27, .327), (.17, -.32, .303), (.13, -.42, .317))
    root.quad('leather', (-.20, -.31, .32), (-.08, -.31, .34),
              (-.08, -.47, .35), (-.20, -.47, .32))
    for x in (-.20, .20):
        for y in (-.26, -.47):
            root.orb('bronze', (x, y, .32), (.012, .012, .008), 6, 3)
    # Narrow bracers follow the arms without covering the original skin mesh.
    for bone in ('LeftArm', 'RightArm'):
        arm = parts[bone]
        arm.box('leather', (0, -.29, .02), (.15, .07, .13))
    # Hammer in the right hand: long wooden haft and broad iron head.
    right.rod('wood', (.01, -.43, .15), (.01, -.08, .15), .025, 7)
    right.box('iron', (.01, -.37, .15), (.25, .12, .12))
    right.box('steel_dark', (-.12, -.37, .15), (.025, .13, .13))
    right.box('steel_dark', (.14, -.37, .15), (.025, .13, .13))


def armored_jarl(parts):
    head, chest, left = parts['Head'], parts['Chest'], parts['LeftElbow']
    # Open-faced helm: a short faceted dome, thin brow, and nose guard.
    sides = 10
    for i in range(sides):
        a = 2*math.pi*i/sides
        b = 2*math.pi*(i+1)/sides
        lower_a = (.175*math.cos(a), .29, .145*math.sin(a))
        lower_b = (.175*math.cos(b), .29, .145*math.sin(b))
        upper_a = (.10*math.cos(a), .38, .085*math.sin(a))
        upper_b = (.10*math.cos(b), .38, .085*math.sin(b))
        head.quad('steel_dark' if i % 2 else 'steel', lower_a, lower_b, upper_b, upper_a)
        head.tri('steel_light', upper_a, upper_b, (0, .43, 0))
    head.box('steel_light', (0, .29, .08), (.32, .025, .035))
    for x in (-.17, .17):
        head.box('steel_dark', (x, .16, .015), (.025, .10, .06))
        head.orb('bronze', (x, .29, .08), (.015, .015, .012), 6, 3)
    # Small scale details reveal the original tunic and preserve the face.
    for row in range(4):
        y = .17 - row * .08
        for col in range(5):
            x = (col - 2) * .085 + (.04 if row % 2 else 0)
            if abs(x) > .22:
                continue
            chest.tri('steel_light' if (row+col) % 3 == 0 else 'steel',
                      (x-.035, y+.025, .245), (x+.035, y+.025, .245), (x, y-.04, .26))
    chest.quad('leather_light', (-.23, .17, .265), (-.20, .18, .265),
               (.20, -.13, .275), (.23, -.14, .275))
    # Broad battle axe with a readable blade silhouette.
    left.rod('wood', (0, -.44, .16), (0, .03, .16), .027, 7)
    left.box('bronze', (0, -.33, .16), (.07, .055, .07))
    left.box('steel', (-.055, -.34, .17), (.14, .15, .07))
    left.quad('blade', (-.025, -.27, .26), (-.17, -.21, .26),
              (-.24, -.34, .16), (-.17, -.45, .16))
    left.quad('blade', (-.17, -.21, .26), (-.27, -.25, .26),
              (-.30, -.34, .16), (-.24, -.34, .16))
    left.quad('steel_light', (-.24, -.34, .16), (-.30, -.34, .16),
              (-.27, -.43, .16), (-.17, -.45, .16))


DESIGNS = {
    'ElderSeer': seer,
    'ShieldBearer': shield_bearer,
    'Blacksmith': blacksmith,
    'ArmoredJarl': armored_jarl,
}


def build(name, base):
    raw = (MODELS / f'{base}.glb').read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + json_length])
    at = 20 + json_length
    binary_length = struct.unpack_from('<I', raw, at)[0]
    binary = bytearray(raw[at + 8:at + 8 + binary_length])
    named = {node.get('name'): i for i, node in enumerate(doc['nodes'])}
    parts = {bone: Geometry() for bone in ('WalkRoot', 'Chest', 'Head', 'LeftArm',
                                            'RightArm', 'LeftElbow', 'RightElbow')}
    DESIGNS[name](parts)
    materials = {}
    for material_name, (r, g, b, metalness) in PALETTE.items():
        materials[material_name] = len(doc['materials'])
        doc['materials'].append({'name': f'Accessory {material_name}', 'doubleSided': True,
                                 'pbrMetallicRoughness': {'baseColorFactor': [r, g, b, 1],
                                                           'metallicFactor': metalness,
                                                           'roughnessFactor': .8 if metalness < .1 else .45}})

    def append(payload):
        binary.extend(b'\0' * (-len(binary) % 4))
        offset = len(binary)
        binary.extend(payload)
        index = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(payload)})
        return index

    def accessor(values, kind, bounds=False):
        payload = struct.pack('<' + 'f' * len(values), *values)
        entry = {'bufferView': append(payload), 'componentType': 5126,
                 'count': len(values) // 3, 'type': kind}
        if bounds:
            entry['min'] = [min(values[k::3]) for k in range(3)]
            entry['max'] = [max(values[k::3]) for k in range(3)]
        index = len(doc['accessors'])
        doc['accessors'].append(entry)
        return index

    for bone, geometry in parts.items():
        if not geometry.parts:
            continue
        primitives = []
        for material_name, (positions, normals) in geometry.parts.items():
            primitives.append({'attributes': {'POSITION': accessor(positions, 'VEC3', True),
                                              'NORMAL': accessor(normals, 'VEC3')},
                               'material': materials[material_name], 'mode': 4})
        mesh = len(doc['meshes'])
        doc['meshes'].append({'name': f'{name} {bone} accessories', 'primitives': primitives})
        node = len(doc['nodes'])
        doc['nodes'].append({'name': f'Accessory_{name}_{bone}', 'mesh': mesh})
        doc['nodes'][named[bone]].setdefault('children', []).append(node)
    doc['scenes'][doc.get('scene', 0)]['name'] = name
    doc['asset']['generator'] = 'Viking Character Forge reference variants'
    binary.extend(b'\0' * (-len(binary) % 4))
    doc['buffers'][0]['byteLength'] = len(binary)
    encoded = json.dumps(doc, separators=(',', ':')).encode('utf-8')
    encoded += b' ' * (-len(encoded) % 4)
    result = (b'glTF' + struct.pack('<II', 2, 28 + len(encoded) + len(binary)) +
              struct.pack('<I4s', len(encoded), b'JSON') + encoded +
              struct.pack('<I4s', len(binary), b'BIN\0') + binary)
    target = MODELS / f'{name}.glb'
    target.write_bytes(result)
    print(f'{name}: {len(result):,} bytes, {len(doc["meshes"])} meshes')


if __name__ == '__main__':
    for name, base in VARIANTS.items():
        build(name, base)
