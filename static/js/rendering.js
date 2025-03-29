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
 * Converts a sequence of 2D points into a set of cubic Bézier segments using
 * Catmull-Rom spline logic to estimate smooth control points.
 *
 * Each segment is an object containing the Bézier control points and the
 * corresponding parameter interval [t1, t2].
 *
 * @param {Array<[number, number]>} points - Input points [x, y]
 * @param {Array<number>} t - Corresponding parameter values (e.g., from arc length)
 * @returns {Array<Object>} - Array of Bézier segment objects with p0, cp1, cp2, p3, t1, t2
 */
function catmullRomToBezier(points, t) {
    const segments = [];

    for (let i = 0; i < points.length - 1; i++) {
        const p0 = points[Math.max(i - 1, 0)];
        const p1 = points[i];
        const p2 = points[i + 1];
        const p3 = points[Math.min(i + 2, points.length - 1)];

        // Control points from Catmull-Rom to Bézier formula
        const cp1 = [
            p1[0] + (p2[0] - p0[0]) / 6,
            p1[1] + (p2[1] - p0[1]) / 6
        ];
        const cp2 = [
            p2[0] - (p3[0] - p1[0]) / 6,
            p2[1] - (p3[1] - p1[1]) / 6
        ];

        segments.push({
            t1: t[i],
            t2: t[i + 1],
            p0: p1,
            cp1,
            cp2,
            p3: p2
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
    const segments = catmullRomToBezier(points, t);
    const densePoints = sampleBezierSegments(segments, tDense);

    return densePoints;
}
