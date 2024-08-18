// import CubicSpline from 'cubic-spline';

let characters = {};
let joins = {};

document.getElementById('text').addEventListener('input', generateSplines);
document.getElementById('separate_splines').addEventListener('change', generateSplines);
document.getElementById('show_knot_points').addEventListener('change', generateSplines);

async function generateSplines() {
    const text = document.getElementById('text-input').value || 'a b c d e f g h i j k l m n o p q r s t u v w x y z';
    const separateSplines = document.getElementById('separate-splines').checked;
    const showKnotPoints = document.getElementById('show-knot-points').checked;

    let splines, redDotPoints;
    if (separateSplines) {
        ({ splines, redDotPoints } = textToSeparateSplines(text));
    } else {
        ({ splines, redDotPoints } = textToSplines(text)); // Implement textToSplines similar to textToSeparateSplines
    }

    const svgContainer = document.getElementById('svg-container');
    svgContainer.innerHTML = generateSvg(splines, redDotPoints, showKnotPoints);
}

function generateSvg(splines, redDotPoints, showKnotPoints) {
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('width', '1500');
    svg.setAttribute('height', '300');
    svg.setAttribute('viewBox', '-15 -15 30 30'); // Adjust viewBox to match your coordinate system

    splines.forEach(spline => {
        const path = document.createElementNS(svgNS, 'path');
        const d = spline.x.map((x, i) => `${i === 0 ? 'M' : 'L'} ${x},${spline.y[i]}`).join(' ');
        path.setAttribute('d', d);
        path.setAttribute('stroke', 'black');
        path.setAttribute('stroke-width', '0.1'); // Adjust stroke width if needed
        path.setAttribute('fill', 'none');
        svg.appendChild(path);
    });

    if (showKnotPoints) {
        redDotPoints.forEach(points => {
            points.forEach(point => {
                const circle = document.createElementNS(svgNS, 'circle');
                circle.setAttribute('cx', point[0]);
                circle.setAttribute('cy', point[1]);
                circle.setAttribute('r', '0.3'); // Adjust radius if needed
                circle.setAttribute('fill', 'red');
                svg.appendChild(circle);
            });
        });
    }

    return svg.outerHTML;
}

async function loadJsonFile(url) {
    const response = await fetch(url);
    return response.json();
}

async function getData() {
    characters = await loadJsonFile('static/data/characters.json');
    joins = await loadJsonFile('static/data/joins.json');
}

function interpolatePoints(points, numPoints = 100) {
    if (points.length < 2) {
        return { x: [], y: [] };
    }

    const x = points.map(p => p[0]);
    const y = points.map(p => p[1]);
    const t = Array.from({ length: points.length }, (_, i) => i / (points.length - 1));

    const xSpline = new CubicSpline(t, x);
    const ySpline = new CubicSpline(t, y);

    const tNew = Array.from({ length: numPoints }, (_, i) => i / (numPoints - 1));
    const xInterpolated = tNew.map(ti => xSpline.at(ti));
    const yInterpolated = tNew.map(ti => ySpline.at(ti));

    return { x: xInterpolated, y: yInterpolated };
}

function joinToSpline(char, cursorPos, prev = null) {
    let joinPoints = characters[char].slice();

    if (prev === null) {  // first character in word
        // shift to properly respect spaces b/w words
        const minX = Math.min(...joinPoints.map(p => p[0]));
        joinPoints = joinPoints.map(p => [p[0] + Math.abs(minX), p[1]]);
    } else {
        if (joins[char] && joins[char][prev]) {
            // replace with modified version for the join
            joinPoints = joins[char][prev].slice();
        }
        // shift to align with cursor position
        const shiftX = joinPoints[0][0];
        joinPoints = joinPoints.map(p => [p[0] - shiftX, p[1]]);
    }

    // move to cursor position
    joinPoints = joinPoints.map(p => [p[0] + cursorPos[0], p[1] + cursorPos[1]]);

    // record positions of knot points for plotting
    const { x: xSpline, y: ySpline } = interpolatePoints(joinPoints);
    const redDotPoints = joinPoints;

    // move cursor and word endpoint tracker
    const rightmostX = Math.max(...joinPoints.map(p => p[0]));
    cursorPos = joinPoints[joinPoints.length - 1].slice();

    return { splines: { x: xSpline, y: ySpline }, redDotPoints, rightmostX, cursorPos };
}

function textToSeparateSplines(text) {
    const lines = text.split('\n');
    let splines = [];
    let redDotPoints = [];
    const wordSpace = 0.1;
    let cursorPos = [0, 0];
    let rightmostX = 0;  // for adding spaces between words
    let yOffset = 0;  // for adding newlines
    const lineHeight = 2;

    lines.forEach(line => {
        const words = line.split(' ');
        words.forEach(word => {
            if (word) {
                let join = '';
                let prev = null;

                for (const char of word) {
                    const testJoin = join + char;
                    if (characters[testJoin]) {
                        join = testJoin;
                    } else {
                        if (join) {  // a completed join, with no other additions available
                            const { splines: spline, redDotPoints: dots, rightmostX: rX, cursorPos: cPos } = joinToSpline(join, cursorPos, prev);
                            splines.push(spline);
                            redDotPoints.push(dots);
                            rightmostX = rX;
                            cursorPos = cPos;
                            prev = join;
                        }
                        join = char;
                        // if (!characters[char]) {
                        //     const { splines: spline, redDotPoints: dots, rightmostX: rX, cursorPos: cPos } = joinToSpline(join, cursorPos, prev);
                        //     splines.push(spline);
                        //     redDotPoints.push(dots);
                        //     rightmostX = rX;
                        //     cursorPos = cPos;
                        //     prev = join;
                        // }
                    }
                }

                if (join) {  // plot the last character
                    const { splines: spline, redDotPoints: dots, rightmostX: rX, cursorPos: cPos } = joinToSpline(join, cursorPos, prev);
                    splines.push(spline);
                    redDotPoints.push(dots);
                    rightmostX = rX;
                    cursorPos = cPos;
                }

                cursorPos[0] = rightmostX + wordSpace;
                cursorPos[1] = 0;
            }
        });
        yOffset -= lineHeight;
    });

    return { splines, redDotPoints };
}

// Call the function to load data
getData().then(() => {
    // You can now call textToSeparateSplines with the loaded data
    const result = textToSeparateSplines('your text here');
    console.log(result);
});
