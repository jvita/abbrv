import matplotlib.pyplot as plt
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from matplotlib.path import Path
import matplotlib.patches as patches
import os


class MatplotlibPen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.paths = []
        self.current_path = []

    def _moveTo(self, p0):
        if self.current_path:
            self._closePath()
        self.current_path = [(Path.MOVETO, p0)]

    def _lineTo(self, p1):
        self.current_path.append((Path.LINETO, p1))

    def _curveToOne(self, p1, p2, p3):
        self.current_path.append((Path.CURVE4, p1))
        self.current_path.append((Path.CURVE4, p2))
        self.current_path.append((Path.CURVE4, p3))

    def _closePath(self):
        if self.current_path:
            self.paths.append(self.current_path)
            self.current_path = []

    def get_paths(self):
        if self.current_path:
            self._closePath()
        return self.paths


def draw_glyph(ax, glyph, glyphSet, scale=0.001):
    pen = MatplotlibPen(glyphSet)
    glyph.draw(pen)
    for path in pen.get_paths():
        codes, verts = zip(*path)
        verts = [(x * scale, y * scale) for x, y in verts]
        patch = patches.PathPatch(Path(verts, codes), facecolor='black', lw=0)
        ax.add_patch(patch)
    ax.set_aspect('equal')
    ax.axis('off')


def preview_font_glyphs(font_path, output_path="glyphs_preview.png", cols=10):
    font = TTFont(font_path)
    glyphSet = font.getGlyphSet()
    glyph_names = font.getGlyphOrder()

    rows = (len(glyph_names) + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 1.5, rows * 1.5))

    if rows == 1:
        axs = [axs]  # make iterable

    for i, name in enumerate(glyph_names):
        row, col = divmod(i, cols)
        ax = axs[row][col] if rows > 1 else axs[col]
        glyph = glyphSet[name]
        draw_glyph(ax, glyph, glyphSet)
        ax.set_title(name, fontsize=8)

    # Hide unused axes
    for i in range(len(glyph_names), rows * cols):
        row, col = divmod(i, cols)
        ax = axs[row][col] if rows > 1 else axs[col]
        ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"Saved glyph preview to {output_path}")


if __name__ == "__main__":
    preview_font_glyphs("BezierSplineFont.otf")
