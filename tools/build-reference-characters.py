"""Kitbash four rig-compatible Viking presets from the detailed studio meshes.

Accessories are small faceted meshes parented to existing bones. The original
1024px character atlas, skin, and eyelid morphs remain intact, so the studio's
palette controls and four animation clips continue to work on every variant.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'assets/models/characters/studio-high'
VARIANTS = {
    'ElderSeer': 'Farmer',
    'ShieldBearer': 'Sheildmaiden',
    'Blacksmith': 'Farmer',
    'ArmoredJarl': 'Farmer',
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
    'skin': (0.78, 0.55, 0.42, 0.0),
    'skin_light': (0.89, 0.65, 0.52, 0.0),
    'cloth_dark': (0.15, 0.18, 0.17, 0.0),
    'garment': (0.55, 0.35, 0.16, 0.0),
    'garment_light': (0.66, 0.44, 0.23, 0.0),
    'garment_dark': (0.37, 0.23, 0.12, 0.0),
    'hair': (0.68, 0.68, 0.65, 0.0),
    'hair_light': (0.80, 0.79, 0.74, 0.0),
    'hair_dark': (0.43, 0.42, 0.40, 0.0),
}

ROLE_PALETTE = {
    'ElderSeer': {
        'garment': (0.48, 0.36, 0.22),
        'garment_light': (0.59, 0.45, 0.28),
        'garment_dark': (0.32, 0.25, 0.18),
        'hair': (0.69, 0.69, 0.66),
        'hair_light': (0.82, 0.81, 0.77),
        'hair_dark': (0.49, 0.48, 0.46),
    },
    'ShieldBearer': {
        'garment': (0.35, 0.15, 0.18),
        'garment_light': (0.47, 0.22, 0.23),
        'garment_dark': (0.22, 0.10, 0.12),
        'hair': (0.56, 0.22, 0.09),
        'hair_light': (0.72, 0.34, 0.12),
        'hair_dark': (0.35, 0.13, 0.06),
    },
    'Blacksmith': {
        'garment': (0.21, 0.23, 0.22),
        'garment_light': (0.29, 0.30, 0.28),
        'garment_dark': (0.13, 0.15, 0.15),
        'hair': (0.14, 0.12, 0.11),
        'hair_light': (0.25, 0.21, 0.18),
        'hair_dark': (0.08, 0.07, 0.07),
    },
    'ArmoredJarl': {
        'garment': (0.25, 0.29, 0.30),
        'garment_light': (0.34, 0.40, 0.40),
        'garment_dark': (0.15, 0.19, 0.21),
        'steel_dark': (0.30, 0.37, 0.40),
        'steel': (0.46, 0.52, 0.55),
        'steel_light': (0.66, 0.72, 0.74),
        'hair': (0.28, 0.18, 0.13),
        'hair_light': (0.40, 0.28, 0.20),
        'hair_dark': (0.16, 0.10, 0.08),
    }
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

    def surface(self, rows, materials):
        """Connect equally sized curved rows with faceted cloth or armor."""
        for row in range(len(rows) - 1):
            for col in range(len(rows[row]) - 1):
                material = materials[(row + col) % len(materials)]
                a, b = rows[row][col], rows[row][col + 1]
                c, d = rows[row + 1][col + 1], rows[row + 1][col]
                if sum(point[2] for point in (a, b, c, d)) > 0:
                    self.quad(material, a, d, c, b)
                else:
                    self.quad(material, a, b, c, d)

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


def long_beard(head, length):
    rows = [
        [(-.065, -.035, .17), (0, -.05, .205), (.065, -.035, .17)],
        [(-.052, -.12, .185), (0, -.14, .218), (.052, -.12, .185)],
        [(-.009, -length, .18), (0, -length*1.04, .195),
         (.009, -length, .18)],
    ]
    head.surface(rows, ['hair', 'hair_light', 'hair_dark'])


def robe_rows(ys, widths, depths, rear=False):
    rows = []
    for y, width, depth in zip(ys, widths, depths):
        row = []
        for step in range(7):
            u = (step - 3) / 3
            z = depth * math.sqrt(max(0, 1-u*u))
            row.append((width*u, y + .012*abs(u), -z if rear else z))
        rows.append(row)
    return rows


def seer(parts):
    root, head = parts['WalkRoot'], parts['Head']
    # A long, faceted robe gives a different silhouette from the short Settler
    # tunic. The front and back stand clear of the animated legs.
    front = robe_rows([-.18, -.39, -.60, -.78],
                      [.28, .31, .35, .38], [.24, .29, .31, .34])
    rear = robe_rows([-.18, -.39, -.60, -.78],
                     [.28, .31, .35, .38], [.21, .24, .28, .32], True)
    root.surface(front, ['garment', 'garment_light', 'garment_dark'])
    root.surface(rear, ['garment_dark', 'garment', 'garment_light'])
    for rows in (front, rear):
        root.surface([rows[-2], rows[-1]], ['garment_dark', 'garment_light'])
    for side in (-1, 1):
        root.rod('fur_light', (side*.25, -.20, .10),
                 (side*.34, -.77, .03), .012, 5)
    long_beard(head, .24)


def shield_bearer(parts):
    chest, root, head = parts['Chest'], parts['WalkRoot'], parts['Head']
    # Fitted leather breastplate leaves the fur collar and dress visible.
    chest.orb('leather', (0, .10, .18), (.225, .19, .105), 12, 6)
    chest.orb('leather_light', (0, .17, .258), (.16, .035, .022), 10, 3)
    for row in range(3):
        y = .19 - row*.075
        for col in range(5):
            x = (col-2)*.067 + (.03 if row%2 else 0)
            z = .288 - .05*(abs(x)/.23)**2
            chest.tri('steel_dark' if (row+col)%3 else 'bronze',
                      (x-.028,y+.012,z), (x,y-.04,z+.008),
                      (x+.028,y+.012,z))
    for x in (-.19,.19):
        chest.orb('bronze', (x, .14, .25), (.016,.016,.012), 6, 3)
    for side in (-1, 1):
        tasset = [
            [(side*.05, -.16, .27), (side*.13, -.16, .29), (side*.23, -.16, .22)],
            [(side*.05, -.34, .29), (side*.15, -.38, .31), (side*.25, -.35, .23)],
        ]
        root.surface(tasset, ['leather', 'garment_dark'])
        root.tri('bronze', (side*.14, -.33, .32),
                 (side*.20, -.33, .29), (side*.17, -.39, .31))
    # Large shield remains behind one shoulder, but now has timber planks.
    chest.disc('steel_dark', 'wood', (.37, .10), .36, -.23, 14)
    for i in range(6):
        x = .16 + i*.075
        chest.quad('wood_light' if i % 2 else 'wood',
                   (x-.028, -.17, -.197), (x+.028, -.17, -.197),
                   (x+.028, .36, -.197), (x-.028, .36, -.197))
    chest.orb('bronze', (.37, .10, -.17), (.075, .075, .045), 8, 3)
    for angle in (0, math.pi/2, math.pi, 3*math.pi/2):
        chest.orb('bronze', (.37 + .27*math.cos(angle), .10 + .27*math.sin(angle), -.20),
                  (.023, .023, .014), 6, 3)
    chest.rod('leather_light', (-.14, .27, .25), (.13, -.02, .28), .012, 5)


def blacksmith(parts):
    root, chest, head, right = (parts['WalkRoot'], parts['Chest'],
                               parts['Head'], parts['RightElbow'])
    # Narrow bracers and an apron distinguish the forge worker while keeping
    # the original textured arms and face visible.
    for bone in ('LeftArm', 'RightArm'):
        arm = parts[bone]
        arm.orb('leather', (0, -.29, .02), (.095, .035, .10), 8, 3)
    # The apron wraps around the torso and projects forward from the thighs.
    bib = []
    for y, width, depth in ((.15,.125,.25), (.02,.16,.285), (-.14,.19,.30)):
        bib.append([(width*u, y, depth*(1-.17*u*u)) for u in (-1,-.5,0,.5,1)])
    chest.surface(bib, ['garment', 'garment_light', 'garment_dark'])
    skirt = []
    for y, width, depth in ((-.10,.19,.29),(-.27,.22,.32),(-.48,.24,.34)):
        skirt.append([(width*u, y, depth*(1-.2*u*u)) for u in (-1,-.5,0,.5,1)])
    root.surface(skirt, ['garment_dark', 'garment', 'garment_light'])
    for side in (-1, 1):
        chest.rod('leather_light', (side*.125, .15, .25),
                  (side*.17, -.14, .28), .014, 5)
        root.rod('leather_light', (side*.17, -.10, .28),
                 (side*.23, -.47, .30), .010, 5)
    root.quad('leather', (-.19, -.29, .315), (-.07, -.29, .35),
              (-.07, -.44, .36), (-.19, -.44, .32))
    for x in (-.19, .19):
        for y in (-.27, -.46):
            root.orb('bronze', (x, y, .33), (.012, .012, .008), 6, 3)
    # Hammer in the right hand: long wooden haft and broad iron head.
    right.rod('wood', (.01, -.43, .15), (.01, -.08, .15), .025, 7)
    right.box('iron', (.01, -.37, .15), (.25, .12, .12))
    right.box('steel_dark', (-.12, -.37, .15), (.025, .13, .13))
    right.box('steel_dark', (.14, -.37, .15), (.025, .13, .13))


def armored_jarl(parts):
    chest, root, head, left = (parts['Chest'], parts['WalkRoot'],
                              parts['Head'], parts['LeftElbow'])
    # The mail follows the front of the torso, with a waist edge rather than
    # a protruding oval that reads as a shield strapped over the tunic.
    mail_rows = []
    for y, width, depth in ((.33,.17,.25),(.19,.22,.27),(.02,.235,.28),(-.15,.21,.27)):
        mail_rows.append([(width*u, y, depth-.055*u*u) for u in (-1,-.66,-.33,0,.33,.66,1)])
    chest.surface(mail_rows, ['steel_dark', 'steel', 'steel_dark'])
    for row in range(5):
        y = .28 - row*.075
        for col in range(6):
            x = (col-2.5)*.066 + (.023 if row % 2 else 0)
            if abs(x) > .18:
                continue
            depth = .273 - .055*(x/.235)**2
            chest.tri('steel_light' if (row+col)%4 == 0 else 'steel',
                      (x-.028,y+.01,depth), (x,y-.045,depth+.008),
                      (x+.028,y+.01,depth))
    chest.rod('leather_light', (-.13,.30,.255), (.13,-.06,.29), .013, 6)
    for side in (-1,1):
        elbow=parts['LeftElbow' if side < 0 else 'RightElbow']
        elbow.orb('steel_dark', (0,-.13,.015), (.085,.105,.08), 8, 3)
        tasset=[[(side*.04,-.18,.25),(side*.14,-.18,.28),(side*.26,-.18,.21)],
                [(side*.04,-.37,.27),(side*.16,-.39,.30),(side*.26,-.37,.22)]]
        root.surface(tasset,['steel_dark','steel'])
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
        if material_name in ROLE_PALETTE[name]:
            r, g, b = ROLE_PALETTE[name][material_name]
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
