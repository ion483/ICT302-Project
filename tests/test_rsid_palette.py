import colorsys
import math

from core.rsid_palette import build_rsid_palette, _lab
from core.report_generator import _colour_map_rows


def test_similar_adjacent_groups_are_reassigned_consistently():
    ids = [f'{index + 1:08X}' for index in range(34)]
    # Groups 34 and 13 were near-identical in the original golden-angle palette.
    paragraphs = [{'runs': [{'rsidR': rsid, 'text': 'Example '}
                            for rsid in ids + [ids[12], ids[33]]]}]
    palette = build_rsid_palette(paragraphs)
    assert palette == build_rsid_palette(paragraphs)
    assert [palette[rsid]['number'] for rsid in ids] == list(range(1, 35))

    def rgb(hex_colour):
        return tuple(int(hex_colour[i:i+2], 16) / 255 for i in (1, 3, 5))

    original = [colorsys.hls_to_rgb(((index * 137.508 + 30) % 360) / 360, .82, .70)
                for index in (12, 33)]
    assert math.dist(*map(_lab, original)) < 18
    assert math.dist(_lab(rgb(palette[ids[12]]['colour'])),
                     _lab(rgb(palette[ids[33]]['colour']))) >= 18
    for row in _colour_map_rows(paragraphs, 200):
        for _, colour, number in row.segments:
            assert colour.hexval()[2:].lower() == palette[ids[number - 1]]['colour'][1:]


def test_invalid_identifiers_do_not_receive_numbers():
    palette = build_rsid_palette([{'runs': [
        {'text': 'Unknown', 'rsidR': '00000000'},
        {'text': 'Known', 'rsidR': '00abcdef'},
        {'text': 'Known again', 'rsidR': '00ABCDEF'},
    ]}])
    assert list(palette) == ['00ABCDEF']
    assert palette['00ABCDEF']['number'] == 1
