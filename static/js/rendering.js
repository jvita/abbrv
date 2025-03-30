/**
 * Computes cumulative arc-length parameter values for a set of 2D points.
 *
 * This provides a smooth parametric `t` array (e.g., [0, 1.2, 3.0, ...])
 * representing the total distance traveled along the path defined by the points.
 *
 * @param {Array<[number, number]>} points - Array of [x, y] points
 * @returns {Array<number>} - Cumulative arc length values for each point
 */
function computeArcLengthParam(points) {
    const t = [0];
    for (let i = 1; i < points.length; i++) {
        const dx = points[i][0] - points[i - 1][0];
        const dy = points[i][1] - points[i - 1][1];
        t.push(t[i - 1] + Math.hypot(dx, dy));
    }
    return t;
}

/**
 * Generates cubic Bézier segments that interpolate the given points
 * with C¹ continuity (matching tangents).
 *
 * Pure function: does not mutate `points` or return shared references.
 *
 * @param {Array<[number, number]>} points - Array of anchor points
 * @returns {Array<{ p0, cp1, cp2, p1 }>} - Array of cubic Bézier segments
 */
function computeBezierThroughPoints(points) {
    const n = points.length - 1;
    if (n < 1) return [];

    // ✅ Special case for exactly two points — create a straight cubic Bézier
    if (n === 1) {
        const [p0, p1] = points;
        const cp1 = [
            p0[0] + (p1[0] - p0[0]) / 3,
            p0[1] + (p1[1] - p0[1]) / 3,
        ];
        const cp2 = [
            p0[0] + 2 * (p1[0] - p0[0]) / 3,
            p0[1] + 2 * (p1[1] - p0[1]) / 3,
        ];
        return [{ p0, cp1, cp2, p1 }];
    }

    const a = new Array(n).fill(0);
    const b = new Array(n).fill(0);
    const c = new Array(n).fill(0);
    const rx = new Array(n).fill(0);
    const ry = new Array(n).fill(0);

    // Set up the tridiagonal system
    for (let i = 0; i < n; i++) {
        const [x0, y0] = points[i];
        const [x1, y1] = points[i + 1];

        if (i === 0) {
            a[i] = 0;
            b[i] = 2;
            c[i] = 1;
            rx[i] = x0 + 2 * x1;
            ry[i] = y0 + 2 * y1;
        } else if (i === n - 1) {
            a[i] = 2;
            b[i] = 7;
            c[i] = 0;
            rx[i] = 8 * x0 + x1;
            ry[i] = 8 * y0 + y1;
        } else {
            a[i] = 1;
            b[i] = 4;
            c[i] = 1;
            rx[i] = 4 * x0 + 2 * x1;
            ry[i] = 4 * y0 + 2 * y1;
        }
    }

    // Solve the tridiagonal system using Thomas algorithm
    for (let i = 1; i < n; i++) {
        const m = a[i] / b[i - 1];
        b[i] -= m * c[i - 1];
        rx[i] -= m * rx[i - 1];
        ry[i] -= m * ry[i - 1];
    }

    const cp1x = new Array(n);
    const cp1y = new Array(n);
    cp1x[n - 1] = rx[n - 1] / b[n - 1];
    cp1y[n - 1] = ry[n - 1] / b[n - 1];

    for (let i = n - 2; i >= 0; i--) {
        cp1x[i] = (rx[i] - c[i] * cp1x[i + 1]) / b[i];
        cp1y[i] = (ry[i] - c[i] * cp1y[i + 1]) / b[i];
    }

    // Build segments with copies of input values
    const segments = [];
    for (let i = 0; i < n; i++) {
        const [x0, y0] = points[i];
        const [x1, y1] = points[i + 1];

        const cp1 = [cp1x[i], cp1y[i]];
        const cp2 = i < n - 1
            ? [2 * x1 - cp1x[i + 1], 2 * y1 - cp1y[i + 1]]
            : [(x1 + cp1x[i]) / 2, (y1 + cp1y[i]) / 2];

        segments.push({
            p0: [x0, y0],
            cp1,
            cp2,
            p1: [x1, y1]
        });
    }

    return segments;
}

/**
 * Evaluates a cubic Bézier curve segment at a normalized parameter t ∈ [0, 1].
 *
 * @param {[number, number]} p0 - Starting anchor point
 * @param {[number, number]} cp1 - First control point
 * @param {[number, number]} cp2 - Second control point
 * @param {[number, number]} p3 - Ending anchor point
 * @param {number} t - Normalized parameter value ∈ [0, 1]
 * @returns {[number, number]} - Interpolated [x, y] point on the curve
 */
function evaluateCubicBezierSegment(p0, cp1, cp2, p3, t) {
    const u = 1 - t;

    const x =
        u ** 3 * p0[0] +
        3 * u ** 2 * t * cp1[0] +
        3 * u * t ** 2 * cp2[0] +
        t ** 3 * p3[0];

    const y =
        u ** 3 * p0[1] +
        3 * u ** 2 * t * cp1[1] +
        3 * u * t ** 2 * cp2[1] +
        t ** 3 * p3[1];

    return [x, y];
}

/**
 * Samples a series of Bézier segments at specific global t values.
 *
 * For each value in `tDense`, the corresponding segment is located and the curve
 * is evaluated using the correct normalized parameter.
 *
 * @param {Array<Object>} segments - Array of Bézier segments from catmullRomToBezier
 * @param {Array<number>} tDense - Array of parameter values to evaluate (usually dense)
 * @returns {Array<[number, number]>} - Interpolated [x, y] values at each tDense
 */
function sampleBezierSegments(segments, tDense) {
    return tDense.map(ti => {
        // Find the appropriate segment for this ti
        let seg = segments.find(s => ti >= s.t1 && ti <= s.t2);
        if (!seg) {
            if (ti <= segments[0].t1) return segments[0].p0;
            if (ti >= segments[segments.length - 1].t2) return segments[segments.length - 1].p3;
            seg = segments[segments.length - 1];
        }

        const { t1, t2, p0, cp1, cp2, p3 } = seg;
        const localT = (t2 - t1 === 0) ? 0 : (ti - t1) / (t2 - t1);

        return evaluateCubicBezierSegment(p0, cp1, cp2, p3, localT);
    });
}

/**
 * High-level utility that generates a dense sequence of interpolated points from
 * a raw array of 2D data using smooth, piecewise cubic Bézier interpolation.
 *
 * Internally:
 * - Computes arc-length parameterization
 * - Converts points into Bézier segments
 * - Evaluates the curve at evenly spaced global t values
 *
 * @param {Array<[number, number]>} points - Input 2D points to interpolate
 * @param {number} numSamples - Number of evenly spaced samples (default: 200)
 * @returns {Array<[number, number]>} - Smooth interpolated dense [x, y] points
 */
function bezierInterpolate2D_Dense(points, numSamples = 200) {
    if (points.length < 2) return [];

    const t = computeArcLengthParam(points);
    const totalLength = t[t.length - 1];

    if (totalLength === 0) {
        return Array(numSamples).fill([...points[0]]);
    }

    const tDense = Array.from({ length: numSamples }, (_, i) => totalLength * i / (numSamples - 1));
    // const segments = catmullRomToBezier(points, t);
    const segments = computeBezierThroughPoints(points);
    const densePoints = sampleBezierSegments(segments, tDense);

    return densePoints;
}

/**
 * Preprocesses the raw spline glyph data into cubic Bézier segments
 * that can be exported to JSON and consumed by the font builder.
 *
 * @param {Object<string, Array<Array<[number, number]>>>} glyphs
 * @returns {Object<string, Array<Array<{p0, cp1, cp2, p1}>>>}
 */
function preprocessGlyphSplines(glyphs) {
    const processed = {};

    for (const [glyphName, splines] of Object.entries(glyphs)) {
        processed[glyphName] = splines.map(points => computeBezierThroughPoints(points));
    }

    return processed;
}
