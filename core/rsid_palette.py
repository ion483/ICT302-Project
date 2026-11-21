"""Deterministic RSID colours shared by the preview and PDF export."""
import colorsys
import math
import re


def _lab(rgb):
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
    r, g, b = linear
    xyz = ((.4124564*r + .3575761*g + .1804375*b) / .95047,
           .2126729*r + .7151522*g + .0721750*b,
           (.0193339*r + .1191920*g + .9503041*b) / 1.08883)
    x, y, z = [v ** (1/3) if v > .008856 else 7.787*v + 16/116 for v in xyz]
    return 116*y - 16, 500*(x-y), 200*(y-z)


def build_rsid_palette(paragraphs):
    neighbours = {}
    previous = None
    for paragraph in paragraphs:
        for run in paragraph.get('runs', []):
            if not run.get('text'):
                continue
            rsid = (run.get('rsidR') or '').strip().upper()
            if not re.fullmatch(r'[0-9A-F]{8}', rsid) or rsid == '00000000':
                previous = None
                continue
            neighbours.setdefault(rsid, set())
            if previous is not None and previous != rsid:
                neighbours[rsid].add(previous)
                neighbours[previous].add(rsid)
            previous = rsid

    palette, labs = {}, {}
    for index, (rsid, adjacent) in enumerate(neighbours.items()):
        hue = (index * 137.508 + 30) % 360

        def candidate(h, lightness):
            # Quantize once so the PDF and CSS use identical RGB values.
            return tuple(round(v * 255) / 255 for v in colorsys.hls_to_rgb(h / 360, lightness, .70))

        def separation(rgb):
            lab = _lab(rgb)
            return min((math.dist(lab, labs[other]) for other in adjacent if other in labs), default=100)

        rgb = candidate(hue, .82)
        if separation(rgb) < 18:
            choices = [candidate((hue + step * 15) % 360, lightness)
                       for lightness in (.82, .74, .90) for step in range(24)]
            rgb = max(choices, key=separation)
        labs[rsid] = _lab(rgb)
        palette[rsid] = {'colour': '#' + ''.join(f'{round(v * 255):02x}' for v in rgb),
                         'number': index + 1}
    return palette
