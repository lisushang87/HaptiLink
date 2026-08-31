"""Lossless black/white patterns with physical SVG page dimensions."""
from html import escape
import numpy as np


def pattern(image, x, y, width, height):
    """Run-length rectangles preserve exact cells without raster interpolation."""
    rows, cols = image.shape
    parts = [f'<g transform="translate({x} {y}) scale({width / cols} {height / rows})" fill="black" shape-rendering="crispEdges">']
    for row, pixels in enumerate(image):
        edges = np.diff(np.r_[False, pixels < 128, False].astype(int))
        for start, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
            parts.append(f'<path d="M {start},{row} H {end} V {row+1} H {start} Z"/>')
    return '\n'.join(parts) + '</g>'


def page(content, title, width=210, height=297):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" '
            f'viewBox="0 0 {width} {height}"><title>{escape(title)}</title>'
            f'<rect width="{width}" height="{height}" fill="white"/>{content}</svg>')
