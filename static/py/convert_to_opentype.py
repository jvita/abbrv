import json
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
import skia
from tqdm import tqdm
from fontTools.ttLib import getTableClass
from fontTools.ttLib.tables import otTables
from fontTools.misc.psCharStrings import T2CharString

units_per_em = 1000
ascender = 800
descender = -200
stroke_width = 20

# Load glyph data
with open("bezier_glyphs_orthic.json") as f:
    glyph_data = json.load(f)

def cubic_bezier(p0, c1, c2, p1, t):
    mt = 1 - t
    return (
        mt**3 * p0 +
        3 * mt**2 * t * c1 +
        3 * mt * t**2 * c2 +
        t**3 * p1
    )

def get_bounds_from_splines(splines, scale=units_per_em, samples=20):
    xs, ys = [], []
    for spline in splines:
        if not spline:
            continue
        p0 = spline[0]["p0"]
        for segment in spline:
            cp1 = segment["cp1"]
            cp2 = segment["cp2"]
            p1 = segment["p1"]
            for i in range(samples + 1):
                t = i / samples
                x = cubic_bezier(p0[0], cp1[0], cp2[0], p1[0], t) * scale
                y = cubic_bezier(p0[1], cp1[1], cp2[1], p1[1], t) * scale
                xs.append(x)
                ys.append(y)
            p0 = p1
    return (min(xs), min(ys), max(xs), max(ys)) if xs and ys else (0, 0, 0, 0)

def glyph_to_stroked_path(splines, scale=units_per_em, width=stroke_width):
    path = skia.Path()
    for spline in splines:
        if not spline:
            continue
        first = spline[0]
        p0 = skia.Point(first["p0"][0] * scale, first["p0"][1] * scale)
        path.moveTo(p0)
        for seg in spline:
            cp1 = skia.Point(seg["cp1"][0] * scale, seg["cp1"][1] * scale)
            cp2 = skia.Point(seg["cp2"][0] * scale, seg["cp2"][1] * scale)
            p1 = skia.Point(seg["p1"][0] * scale, seg["p1"][1] * scale)
            path.cubicTo(cp1, cp2, p1)
    paint = skia.Paint(Style=skia.Paint.kStroke_Style)
    paint.setStrokeWidth(width)
    paint.setStrokeCap(skia.Paint.kButt_Cap)
    paint.setStrokeJoin(skia.Paint.kBevel_Join)
    dst = skia.Path()
    paint.getFillPath(path, dst)
    return dst

def draw_skia_path_to_pen(skia_path, pen):
    iter = skia.Path.RawIter(skia_path)
    while True:
        verb, pts = iter.next()
        if verb == 6:  # Done
            break
        elif verb == 0:  # Move
            pen.moveTo((pts[0].x(), pts[0].y()))
        elif verb == 1:  # Line
            pen.lineTo((pts[1].x(), pts[1].y()))
        elif verb == 2:  # Quad
            p0, p1, p2 = pts[0], pts[1], pts[2]
            c1 = (
                p0.x() + 2/3 * (p1.x() - p0.x()),
                p0.y() + 2/3 * (p1.y() - p0.y())
            )
            c2 = (
                p2.x() + 2/3 * (p1.x() - p2.x()),
                p2.y() + 2/3 * (p1.y() - p2.y())
            )
            pen.curveTo(c1, c2, (p2.x(), p2.y()))
        elif verb == 4:  # Cubic
            pen.curveTo(
                (pts[1].x(), pts[1].y()),
                (pts[2].x(), pts[2].y()),
                (pts[3].x(), pts[3].y()),
            )
        elif verb == 5:  # Close
            pen.closePath()
    pen.endPath()

glyph_order = [".notdef"] + list(glyph_data.keys())
fb = FontBuilder(units_per_em, isTTF=False)
fb.setupGlyphOrder(glyph_order)

# Character map: only single-character names get mapped directly
cmap = {ord(name): name for name in glyph_data if len(name) == 1}
fb.setupCharacterMap(cmap)

# Prepare glyphs and widths
glyphs = {}
advance_widths = {}
bbox_data = {}
for name in tqdm(glyph_order, desc="Building glyphs"):
    if name == ".notdef":
        pen = T2CharStringPen(glyph_order, None)
        pen._width = 100
        pen.moveTo((0, 0))
        pen.lineTo((100, 0))
        pen.lineTo((100, 100))
        pen.lineTo((0, 100))
        pen.closePath()
        glyphs[name] = pen.getCharString(private=None, globalSubrs=None)
        advance_widths[name] = (100, 0)
        bbox_data[name] = (0, 0, 100, 100)
        continue

    splines = glyph_data[name]
    x_min, y_min, x_max, y_max = get_bounds_from_splines(splines)
    width = max(1, int(x_max - x_min))
    advance_widths[name] = (width, 0)
    bbox_data[name] = (int(x_min), int(y_min), int(x_max), int(y_max))

    pen = T2CharStringPen(glyph_order, None)
    pen._width = float(width)
    stroked = glyph_to_stroked_path(splines)
    draw_skia_path_to_pen(stroked, pen)
    if pen._commands:
        charstring = pen.getCharString(private=None, globalSubrs=None)
        charstring.bbox = (int(x_min), int(y_min), int(x_max), int(y_max))
        glyphs[name] = charstring

fb.setupHorizontalMetrics(advance_widths)
fb.setupHorizontalHeader(ascent=ascender, descent=descender)
fb.setupOS2(sTypoAscender=ascender, sTypoDescender=descender)
fb.setupNameTable({
    "familyName": "BezierSplineFont",
    "styleName": "Regular",
    "fullName": "BezierSplineFont Regular",
    "psName": "BezierSplineFont-Regular"
})
fb.setupPost()
fb.setupMaxp()

# Compute global font bounding box
all_xmin = min(b[0] for b in bbox_data.values())
all_ymin = min(b[1] for b in bbox_data.values())
all_xmax = max(b[2] for b in bbox_data.values())
all_ymax = max(b[3] for b in bbox_data.values())
font_bbox = [int(all_xmin), int(all_ymin), int(all_xmax), int(all_ymax)]

# Set up CFF with FontBBox
fb.setupCFF("BezierSplineFont", {}, glyphs, {"FontBBox": font_bbox})
fb.save("BezierSplineFont.otf")
print("\u2705 Saved BezierSplineFont.otf with bounding boxes and advance widths")