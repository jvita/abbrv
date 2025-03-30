import json
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib.tables import otTables
import skia
from tqdm import tqdm

units_per_em = 3040
ascender = 800
descender = -200
stroke_width = 30

# Load glyph data
with open("bezier_glyphs_orthic.json") as f:
    glyph_data = json.load(f)

# Split into regular characters and ligatures
base_chars = [name for name in glyph_data if len(name) == 1]
ligatures = {name: list(name) for name in glyph_data if len(name) > 1}

glyph_order = [".notdef"] + base_chars + list(ligatures.keys())

fb = FontBuilder(units_per_em, isTTF=False)
fb.setupGlyphOrder(glyph_order)

# Create cmap for base characters only
cmap = {ord(name): name for name in base_chars}
fb.setupCharacterMap(cmap)

fb.setupHorizontalMetrics({name: (240, 0) for name in glyph_order})
fb.setupHorizontalHeader(ascent=ascender, descent=descender)
fb.setupOS2(sTypoAscender=ascender, sTypoDescender=descender)
fb.setupNameTable({
    "familyName": "OrthicFont",
    "styleName": "Regular",
    "fullName": "Orthic Regular",
    "psName": "Orthic-Regular"
})
fb.setupPost()
fb.setupMaxp()

# Stroke + convert glyph paths
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
                p0.x() + 2 / 3 * (p1.x() - p0.x()),
                p0.y() + 2 / 3 * (p1.y() - p0.y())
            )
            c2 = (
                p2.x() + 2 / 3 * (p1.x() - p2.x()),
                p2.y() + 2 / 3 * (p1.y() - p2.y())
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

# Build stroked glyph outlines
glyphs = {}
for name in tqdm(glyph_order, desc='Building glyphs'):
    pen = T2CharStringPen(glyph_order, None)
    pen._width = 240

    if name == ".notdef":
        pen.moveTo((0, 0))
        pen.lineTo((240, 0))
        pen.lineTo((240, 240))
        pen.lineTo((0, 240))
        pen.closePath()
        glyphs[name] = pen.getCharString(private=None, globalSubrs=None)
        continue

    stroked = glyph_to_stroked_path(glyph_data[name])
    draw_skia_path_to_pen(stroked, pen)
    if pen._commands:  # Only store if it has content
        glyphs[name] = pen.getCharString(private=None, globalSubrs=None)

fb.setupCFF("BezierSplineFont", {}, glyphs, {})

# from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
# from fontTools.otlLib.builder import (
#     buildLigatureSubstSubtable,
#     buildLookup,
#     buildFeatureList,
#     buildScriptList
# )

from fontTools.ttLib.tables import otTables

def build_ligature_gsub_raw(ligatures):
    # Format: {first_glyph: [(remaining_components, ligature_name), ...]}
    ligature_sets = {}
    for lig_glyph, sequence in ligatures.items():
        if len(sequence) < 2:
            continue
        first = sequence[0]
        rest = sequence[1:]

        lig = otTables.Ligature()
        lig.Component = rest
        lig.LigGlyph = lig_glyph
        ligature_sets.setdefault(first, []).append(lig)

    # Build LigatureSet for each prefix
    ligature_subst = otTables.LigatureSubst()
    ligature_subst.Format = 1
    ligature_subst.LigatureSetCount = len(ligature_sets)
    ligature_subst.Coverage = otTables.Coverage()
    ligature_subst.Coverage.glyphs = list(ligature_sets.keys())
    ligature_subst.LigatureSet = []
    for glyph in ligature_subst.Coverage.glyphs:
        lig_set = otTables.LigatureSet()
        lig_set.Ligature = ligature_sets[glyph]
        ligature_subst.LigatureSet.append(lig_set)

    # Wrap it in a Lookup
    lookup = otTables.Lookup()
    lookup.LookupType = 4  # Ligature Substitution
    lookup.LookupFlag = 0
    lookup.SubTableCount = 1
    lookup.SubTable = [ligature_subst]

    # Feature: liga
    feature = otTables.Feature()
    feature.FeatureParams = None
    feature.LookupListIndex = [0]
    feature.LookupCount = 1

    # FeatureRecord
    feature_record = otTables.FeatureRecord()
    feature_record.FeatureTag = "liga"
    feature_record.Feature = feature

    # FeatureList
    feature_list = otTables.FeatureList()
    feature_list.FeatureCount = 1
    feature_list.FeatureRecord = [feature_record]

    # ScriptList
    script_list = otTables.ScriptList()
    script_record = otTables.ScriptRecord()
    script_record.ScriptTag = "latn"
    script = otTables.Script()
    langsys = otTables.LangSys()
    langsys.LookupOrder = None
    langsys.ReqFeatureIndex = 0xFFFF
    langsys.FeatureIndex = [0]
    langsys.FeatureCount = 1
    script.DefaultLangSys = langsys
    script.LangSysRecord = []
    script_record.Script = script
    script_list.ScriptCount = 1
    script_list.ScriptRecord = [script_record]

    # Assemble GSUB table
    gsub = otTables.GSUB()
    gsub.Version = 0x00010000
    gsub.ScriptList = script_list
    gsub.FeatureList = feature_list
    gsub.LookupList = otTables.LookupList()
    gsub.LookupList.Lookup = [lookup]
    gsub.LookupList.LookupCount = 1

    return gsub


from fontTools.ttLib import getTableClass

# gsub = build_ligature_gsub_raw(ligatures)
# GSUBClass = getTableClass("GSUB")
# gsub_table = GSUBClass()
# gsub_table.table = gsub
# fb.font["GSUB"] = gsub_table

fb.save("orthic.otf")
print("✅ Saved BezierSplineFont.otf with ligature substitutions")
