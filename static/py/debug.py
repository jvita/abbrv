from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen

units_per_em = 1000
ascender = 800
descender = -200

glyph_order = [".notdef", "A"]
fb = FontBuilder(units_per_em, isTTF=False)
fb.setupGlyphOrder(glyph_order)
fb.setupCharacterMap({ord("A"): "A"})
fb.setupHorizontalMetrics({g: (500, 0) for g in glyph_order})
fb.setupHorizontalHeader(ascent=ascender, descent=descender)
fb.setupOS2(sTypoAscender=ascender, sTypoDescender=descender)
fb.setupNameTable({
    "familyName": "MinimalFont",
    "styleName": "Regular",
    "fullName": "MinimalFont Regular",
    "psName": "MinimalFont-Regular"
})
fb.setupPost()
fb.setupMaxp()

# Create minimal glyphs
glyphs = {}

# .notdef box
pen = T2CharStringPen(glyph_order, None)
pen._width = 500
pen.moveTo((0, 0))
pen.lineTo((500, 0))
pen.lineTo((500, 500))
pen.lineTo((0, 500))
pen.closePath()
glyphs[".notdef"] = pen.getCharString(private=None, globalSubrs=None)

# "A" as a triangle
pen = T2CharStringPen(glyph_order, None)
pen._width = 500
pen.moveTo((100, 0))
pen.lineTo((250, 700))
pen.lineTo((400, 0))
pen.closePath()
glyphs["A"] = pen.getCharString(private=None, globalSubrs=None)

# Build font
fb.setupCFF("MinimalFont", {}, glyphs, {})
fb.save("MinimalFont.otf")
print("✅ MinimalFont.otf saved")
