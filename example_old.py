#!/usr/bin/env python3

import math
import itertools
import textwrap

import click
from reedmuller import reedmuller


class Tag:
    """ Helper class to ease creation of SVG. All API functions that create SVG allow you to substitute this with your
    own implementation by passing a ``tag`` parameter. """

    def __init__(self, name, children=None, root=False, **attrs):
        if (fill := attrs.get('fill')) and isinstance(fill, tuple):
            attrs['fill'], attrs['fill-opacity'] = fill
        if (stroke := attrs.get('stroke')) and isinstance(stroke, tuple):
            attrs['stroke'], attrs['stroke-opacity'] = stroke
        self.name, self.attrs = name, attrs
        self.children = children or []
        self.root = root

    def __str__(self):
        prefix = '<?xml version="1.0" encoding="utf-8"?>\n' if self.root else ''
        opening = ' '.join([self.name] + [f'{key.replace("__", ":").replace("_", "-")}="{value}"' for key, value in self.attrs.items()])
        if self.children:
            children = '\n'.join(textwrap.indent(str(c), '  ') for c in self.children)
            return f'{prefix}<{opening}>\n{children}\n</{self.name}>'
        else:
            return f'{prefix}<{opening}/>'


    @classmethod
    def setup_svg(kls, tags, bounds, margin=0, unit='mm', pagecolor='white'):
        (min_x, min_y), (max_x, max_y) = bounds

        if margin:
            min_x -= margin
            min_y -= margin
            max_x += margin
            max_y += margin

        w, h = max_x - min_x, max_y - min_y
        w = 1.0 if math.isclose(w, 0.0) else w
        h = 1.0 if math.isclose(h, 0.0) else h

        namespaces = dict(
            xmlns="http://www.w3.org/2000/svg",
            xmlns__xlink="http://www.w3.org/1999/xlink")

        return kls('svg', tags,
                width=f'{w}{unit}', height=f'{h}{unit}',
                viewBox=f'{min_x} {min_y} {w} {h}',
                style=f'background-color:{pagecolor}',
                **namespaces,
                root=True)


@click.command()
@click.option('-h', '--height', type=float, default=20, help='Bar height in mm')
@click.option('-t/-n', '--text/--no-text', default=True, help='Whether to add text containing the data under the bar code')
@click.option('-f', '--font', default='sans-serif', help='Font for the text underneath the bar code')
@click.option('-s', '--font-size', type=float, default=12, help='Font size for the text underneath the bar code in points (pt)')
@click.option('-b', '--bar-width', type=float, default=1.0, help='Bar width in mm')
@click.option('-m', '--margin', type=float, default=3.0, help='Margin around bar code in mm')
@click.option('-c', '--color', default='black', help='SVG color for the bar code')
@click.option('--text-color', default=None, help='SVG color for the text (defaults to the bar code\'s color)')
@click.option('--dpi', type=float, default=96, help='DPI value to assume for internal SVG unit conversions')
@click.argument('data')
@click.argument('outfile', type=click.File('w'), default='-')
def cli(data, outfile, height, text, font, font_size, bar_width, margin, color, text_color, dpi):
    data = int(data, 16)
    text_color = text_color or color

    NUM_BITS = 26

    data_bits = [bool(data & (1<<i)) for i in range(NUM_BITS)]
    data_encoded = itertools.chain(*[
        (a, not a) for a in data_bits
        ])
    data_encoded = [True, False, True, False, *data_encoded, False, True, True, False, True]

    width = len(data_encoded) * bar_width
    # 1 px = 0.75 pt
    pt_to_mm = lambda pt: pt / 0.75 /dpi * 25.4
    font_size = pt_to_mm(font_size)
    total_height = height + font_size*2

    tags = []
    for key, group in itertools.groupby(enumerate(data_encoded), key=lambda x: x[1]):
        if key:
            group = list(group)
            x0, _key = group[0]
            w = len(group)
            tags.append(Tag('path', stroke=color, stroke_width=w, d=f'M {(x0 + w/2)*bar_width} 0 l 0 {height}'))
    
    if text:
        tags.append(Tag('text', children=[f'{data:07x}'],
                        x=width/2, y=height + 0.5*font_size,
                        font_family=font, font_size=f'{font_size:.3f}px',
                        text_anchor='middle', dominant_baseline='hanging',
                        fill=text_color))

    outfile.write(str(Tag.setup_svg(tags, bounds=((0, 0), (width, total_height)), margin=margin)))


if __name__ == '__main__':
    cli()
