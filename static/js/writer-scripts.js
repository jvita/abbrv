$(document).ready(function() {
    let options = {};

    // Function to retrieve the checkbox states and set variables accordingly
    function updateOptions() {
        options = {
            abbrv_words: document.getElementById('abbrv_words').checked,
            show_baselines: document.getElementById('show_baselines').checked,
            show_dots: document.getElementById('show_dots').checked,
            show_knot_points: document.getElementById('show_knot_points').checked
        };

        // Use the options object as needed in your code
        return options;
    }

    // Add event listeners only to specific predefined checkboxes
    const predefinedCheckboxes = ['abbrv_words', 'show_baselines', 'show_dots', 'show_knot_points'];
    predefinedCheckboxes.forEach(id => {
        const checkbox = document.getElementById(id);
        if (checkbox) {
            checkbox.addEventListener('change', updateOptions);
        }
    });

    updateOptions();

    function downloadSVG() {
        const svgElement = document.getElementById('output');

        // Ensure namespace is present
        if (!svgElement.hasAttribute("xmlns")) {
            svgElement.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        }
        if (!svgElement.hasAttribute("xmlns:xlink")) {
            svgElement.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
        }

        // Get the outerHTML with correct formatting
        const svgData = `<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
            ${svgElement.outerHTML}
        `.trim();

        // Create a Blob and trigger download
        const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "generated_splines.svg";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    document.getElementById('downloadButton').addEventListener('click', downloadSVG);

    // Function to escape special characters for HTML
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")   // Escape ampersand
            .replace(/</g, "&lt;")    // Escape less-than
            .replace(/>/g, "&gt;")     // Escape greater-than
            .replace(/"/g, "&quot;")   // Escape double quote
            .replace(/'/g, "&#039;");   // Escape single quote
    }

    const rulesDropdownItems = document.getElementById('rulesDropdownItems');

    // Check if there are any rules
    rules = selectedSystem ? systems[selectedSystem]['rules'] : []

    if (rules.length === 0) {
        rulesDropdownItems.innerHTML = '<li class="dropdown-item">No additional rules available</li>';
    } else {
        // Create dropdown items dynamically
        rules.forEach(rule => {
            const listItem = document.createElement('li');
            listItem.className = 'dropdown-item d-flex align-items-center text-nowrap';

            const escapedName = escapeHtml(rule.name);  // Escape the rule name

            listItem.innerHTML = `
                <input class="form-check-input me-2" type="checkbox" id="rule_${escapedName}" name="rules" value="${escapedName}" style="width: 5px; height: 5px;" checked>
                <label class="form-check-label mb-1" for="rule_${escapedName}">${escapedName}</label>
            `;

            rulesDropdownItems.appendChild(listItem);
        });
    }

    // Select the multi-select dropdown or checkboxes
    const rulesCheckboxes = document.querySelectorAll('input[name="rules"]');

    // Add change event listener to each checkbox
    rulesCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            updatePlot();
        });
    });

    const modesDropdownItems = document.getElementById('modesDropdownItems');

    // Check if there are any rules
    modes = selectedSystem ? systems[selectedSystem]['modes'] : []

    if (modes.length === 0) {
        modesDropdownItems.innerHTML = '<li class="dropdown-item">No additional rules available</li>';
    } else {
        // Create dropdown items dynamically
        for (const [mode, modeDict] of Object.entries(modes)) {
            const listItem = document.createElement('li');
            listItem.className = 'dropdown-item d-flex align-items-center text-nowrap';

            const escapedName = escapeHtml(mode);  // Escape the rule name

            listItem.innerHTML = `
                <input class="form-check-input me-2" type="checkbox" id="mode_${escapedName}" name="modes" value="${escapedName}" style="width: 5px; height: 5px;" checked>
                <label class="form-check-label mb-1" for="mode_${escapedName}">${escapedName}</label>
            `;

            modesDropdownItems.appendChild(listItem);
        }
    }

    // Select the multi-select dropdown or checkboxes
    const modeCheckboxes = document.querySelectorAll('input[name="modes"]');

    // Add change event listener to each checkbox
    modeCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            updatePlot();
        });
    });

    let debounceTimeout;

    function processTextAndPlot(text, system, activeModes, activeRules, multiWordTokens) {
        /**
        * Processes a string of text by splitting it into lines, tokenizing each line,
        * merging word splines, and sending the tokenized results to a backend using AJAX.
        */
        const [processedText, multiWordMatches] = processText(text, activeRules, selectedSystem);

        // Split the text into lines
        const lines = processedText.split('\n').map(line => line.trim()).filter(line => line !== '');

        // Tokenize each line and merge word splines
        const tokenizedResults = lines.map(line => {
            if (line.length > 0) {
                const tokenizedLine = tokenizeWithMultiWords(line, system, activeModes, multiWordTokens, multiWordMatches);
                return mergeWordSplines(tokenizedLine);
            }
        });

        generateSplines(tokenizedResults)
    }

    function mergeWordSplines(textSplines) {
        /**
        * Merges word splines by concatenating points for each word and adjusting shifts.
        */
        const words = [];

        textSplines.forEach(wordSplines => {
            const currentWord = [];
            let currentShift = [0, 0];

            wordSplines.forEach((glyphSplines, gi) => {
                glyphSplines.forEach(points => {
                    const shiftedPoints = points.map(point => [...point]); // Clone points

                    if (gi !== 0) {
                        const shiftDelta = glyphSplines[0][0];
                        for (let i = 0; i < shiftedPoints.length; i++) {
                            shiftedPoints[i][0] -= shiftDelta[0];
                            shiftedPoints[i][1] -= shiftDelta[1];
                        }
                    }

                    shiftedPoints.forEach(point => {
                        point[0] += currentShift[0];
                        point[1] += currentShift[1];
                    });

                    currentWord.push(shiftedPoints);
                });

                // Update the shift to the last point of the last array in the current glyph
                currentShift = currentWord[currentWord.length - 1][currentWord[currentWord.length - 1].length - 1];
            });

            words.push(currentWord);
        });

        return words;
    }

    const scalingFactor = 6.0;
    const plottedPoints = new Set(); // Persistent set of plotted points

    function generateSplines(tokenizedSplines) {
        /**
        * Generates and plots splines for tokenized text. Handles line breaks and adjustments.
        */

        plottedPoints.clear()  // reset on each redraw

        const spaceBetweenWords = 0.2*scalingFactor;
        const lineSpacing = 0.2*scalingFactor;

        const showDots = document.getElementById('show_dots').checked;
        const showKnots = document.getElementById('show_knot_points').checked;
        const showBaselines = document.getElementById('show_baselines').checked;

        const svgContainer = document.getElementById('output');
        svgContainer.innerHTML = ''; // Clear any existing SVG

        let currentVerticalOffset = 0;
        let rightMostPoint = 0;
        let leftMostPoint = 0;
        let lowestPoint = 0;
        let highestPoint = 0;
        const linePositions = [];

        tokenizedSplines.forEach(wordSplines => {
            let currentShift = [0, 0]
            let lineXPos = 0;
            const splinesToPlot = [];

            wordSplines.forEach(word => {
                const shiftedPointsFirst = word[0].map(([x, y]) => [x*scalingFactor, y*scalingFactor]); // Clone points
                const xmin = shiftedPointsFirst.reduce((minX, point) => Math.min(minX, point[0]), Infinity);

                word.forEach((points, index) => {
                    // Skip plotting the first set of points if it contains only one point
                    if (index === 0 && points.length === 1) {
                        return;
                    }
                    // scale to avoid numerical issues in spline for small shapes
                    const shiftedPoints = points.map(([x, y]) => [x*scalingFactor, y*scalingFactor]); // Clone points

                    for (let i = 0; i < shiftedPoints.length; i++) {
                        shiftedPoints[i][0] -= xmin;
                        shiftedPoints[i][0] += currentShift[0];
                        shiftedPoints[i][1] += currentShift[1];
                    }

                    const xmax = shiftedPoints.reduce((maxX, point) => Math.max(maxX, point[0]), -Infinity);
                    lineXPos = Math.max(lineXPos, xmax);
                    rightMostPoint = Math.max(rightMostPoint, shiftedPoints[shiftedPoints.length - 1][0]);
                    leftMostPoint = Math.min(leftMostPoint, shiftedPoints[0][0]);

                    splinesToPlot.push(shiftedPoints);
                });

                currentShift = [lineXPos + spaceBetweenWords, 0];
            });

            const highestPointCurrentLine = Math.max(...splinesToPlot.flat().map(([x, y]) => y));
            const lowestPointCurrentLine = Math.min(...splinesToPlot.flat().map(([x, y]) => y));

            currentVerticalOffset -= highestPointCurrentLine;

            highestPoint = Math.max(highestPoint, highestPointCurrentLine + currentVerticalOffset)
            lowestPoint = Math.min(lowestPoint, lowestPointCurrentLine + currentVerticalOffset)

            splinesToPlot.forEach(points => {
                // multiply by 6 to handle numerical issues with small shapes
                const adjustedPoints = points.map(([x, y]) => [x, y + currentVerticalOffset]);
                plotSpline(adjustedPoints, showDots, showKnots);
            });

            linePositions.push(currentVerticalOffset);
            currentVerticalOffset += lowestPointCurrentLine - lineSpacing;
        });

        if (showBaselines) {
            plotBaselines(linePositions, [leftMostPoint - spaceBetweenWords, rightMostPoint + spaceBetweenWords]);
        }

        finalizePlot(leftMostPoint, rightMostPoint, highestPoint, lowestPoint, lineSpacing, spaceBetweenWords);
    }

    function plotSpline(points, showDots = true, showKnots = false) {
        /**
         * Plots individual splines.
         * @param {Array} points - Array of points where each point is [x, y].
         * @param {boolean} showDots - Whether to show dots (only if a single unique point exists).
         * @param {boolean} showKnots - Whether to show knots.
         */

        const svgElement = document.getElementById('output');

        if (points.length === 1 && showDots) {
            const key = `${points[0][0]},${points[0][1]}`;
            // if ((!plottedPoints.has(key)) && (plottedPoints.size > 0)) {
            if (!plottedPoints.has(key)) {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', points[0][0]);
                circle.setAttribute('cy', points[0][1]);
                circle.setAttribute('r', 0.01 * scalingFactor);
                circle.setAttribute('fill', 'black');
                svgElement.appendChild(circle);
                plottedPoints.add(key);
            }
        } else {
            points.forEach(([px, py]) => {
                const key = `${px},${py}`;
                if (!plottedPoints.has(key)) {
                    plottedPoints.add(key);
                }
            });

            const { x, y } = interpolatePoints(points);
            const pathData = x.map((xi, i) => `${i === 0 ? 'M' : 'L'} ${xi} ${y[i]}`).join(' ');

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', pathData);
            path.setAttribute('stroke', 'black');
            path.setAttribute('stroke-width', 0.01 * scalingFactor);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke-linecap', 'round');
            svgElement.appendChild(path);
        }

        if (showKnots) {
            points.forEach(([px, py]) => {
                const knot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');

                knot.setAttribute('cx', px);
                knot.setAttribute('cy', py);
                knot.setAttribute('r', 0.01 * scalingFactor);
                knot.setAttribute('fill', 'red');
                svgElement.appendChild(knot);
            });
        }
    }

    function interpolatePoints(points, numPoints = 100) {
        /**
         * Interpolates points using a cubic spline.
         * @param {Array} points - Array of points where each point is [x, y].
         * @param {number} numPoints - Number of points for interpolation.
         * @returns {Object} x, y - Arrays of interpolated x and y coordinates.
         */

        if (points.length < 2) {
            return { x: points.map(p => p[0]), y: points.map(p => p[1]) };
        }

        const x = points.map(p => p[0]);
        const y = points.map(p => p[1]);
        const t = linspace(0, 1, points.length);

        const xSpline = cubicSpline(t, x, linspace(0, 1, numPoints));
        const ySpline = cubicSpline(t, y, linspace(0, 1, numPoints));

        return { x: xSpline, y: ySpline };
    }

    function linspace(start, stop, num) {
        /**
         * Creates an array of evenly spaced numbers over a specified interval.
         * @param {number} start - Start of the interval.
         * @param {number} stop - End of the interval.
         * @param {number} num - Number of points.
         * @returns {Array} - Array of evenly spaced numbers.
         */
        const step = (stop - start) / (num - 1);
        return Array.from({ length: num }, (_, i) => start + step * i);
    }

    function cubicSpline(t, values, newT) {
        /**
         * Generates cubic spline interpolation for the given values.
         * @param {Array} t - Array of original parameter values.
         * @param {Array} values - Array of original data values.
         * @param {Array} newT - Array of new parameter values for interpolation.
         * @returns {Array} - Interpolated values.
         */
        const n = t.length - 1;
        const h = Array.from({ length: n }, (_, i) => t[i + 1] - t[i]);

        const alpha = Array.from({ length: n }, (_, i) => {
            if (i === 0) return 0;
            return (3 / h[i]) * (values[i + 1] - values[i]) - (3 / h[i - 1]) * (values[i] - values[i - 1]);
        });

        const l = new Array(n + 1).fill(0);
        const mu = new Array(n + 1).fill(0);
        const z = new Array(n + 1).fill(0);

        l[0] = 1;
        for (let i = 1; i < n; i++) {
            l[i] = 2 * (t[i + 1] - t[i - 1]) - h[i - 1] * mu[i - 1];
            mu[i] = h[i] / l[i];
            z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i];
        }
        l[n] = 1;

        const c = new Array(n + 1).fill(0);
        const b = new Array(n).fill(0);
        const d = new Array(n).fill(0);

        for (let j = n - 1; j >= 0; j--) {
            c[j] = z[j] - mu[j] * c[j + 1];
            b[j] = (values[j + 1] - values[j]) / h[j] - h[j] * (c[j + 1] + 2 * c[j]) / 3;
            d[j] = (c[j + 1] - c[j]) / (3 * h[j]);
        }

        return newT.map(ti => {
            let i = t.findIndex((_, idx) => t[idx] <= ti && ti <= t[idx + 1]);
            if (i === -1) i = t.length - 2; // Boundary case
            const deltaT = ti - t[i];
            return values[i] + b[i] * deltaT + c[i] * Math.pow(deltaT, 2) + d[i] * Math.pow(deltaT, 3);
        });
    }


    function plotBaselines(positions, xlims) {
        /**
        * Plots baselines for the lines.
        */
        const svg = document.getElementById('output');
        positions.forEach(y => {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', xlims[0]);
            line.setAttribute('x2', xlims[1]);
            line.setAttribute('y1', y);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', 'grey');
            line.setAttribute('stroke-dasharray', `${0.02*scalingFactor}, ${0.02*scalingFactor}`);
            line.setAttribute('stroke-width', 0.005*scalingFactor);

            // Prepend the line to the SVG element to ensure it is below other elements
            svg.insertBefore(line, svg.firstChild);
        });
    }

    function finalizePlot(leftMostPoint, rightMostPoint, highestPoint, lowestPoint, lineSpacing, spaceBetweenWords) {
        const svg = document.getElementById('output');
        svg.setAttribute('viewBox', `${leftMostPoint - 2 * spaceBetweenWords} -${Math.abs(lowestPoint - lineSpacing)} ${rightMostPoint + 4 * spaceBetweenWords} ${highestPoint - lowestPoint + 2 * lineSpacing}`); // Normalize viewBox
        // svg.setAttribute('viewBox', `0 ${highestPoint - lineSpacing} ${rightMostPoint} ${Math.abs(highestPoint - lowestPoint) + 2 * lineSpacing}`); // Normalize viewBox
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet'); // Scale uniformly
        // Get the height of the SVG
        const svgHeight = svg.getAttribute('height') || svg.viewBox.baseVal.height;

        // Apply the transformation
        svg.setAttribute('transform', `scale(1, -1) translate(0, -${svgHeight})`);
    }

    function updatePlot() {
        const svg = document.getElementById('output');

        if (!selectedSystem || !systems[selectedSystem]) {
            svg.innerHTML = ''; // Clear previous contents
            svg.setAttribute('viewBox', '0 0 100 20'); // Wider + better vertical centering
            svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', '50');
            text.setAttribute('y', '10');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.setAttribute('fill', '#6c757d'); // Bootstrap's text-muted color
            text.setAttribute('font-size', '3');  // Smaller size to fit better
            text.setAttribute('font-family', 'sans-serif');
            text.textContent = 'Please select a system first';
            svg.appendChild(text);
            return;
        }

        const form = document.getElementById('text-form');
        const formData = new FormData(form);
        const text = formData.get('text');
        const activeRules = formData.getAll('rules');
        const activeModes = formData.getAll('modes');

        processTextAndPlot(text, systems[selectedSystem], activeModes, activeRules, systems[selectedSystem].phrases);
    }


    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Debounce the plot update to avoid too many requests
    const debouncedUpdatePlot = debounce(updatePlot, 300);

    // Bind the input event on textarea and change event on checkboxes
    $('#text').on('input', function() {
        debouncedUpdatePlot();
    });

    $('#show_knot_points, #show_dots, #show_baselines, #abbrv_words').on('change', function() {
        updatePlot();  // Call updatePlot immediately when checkboxes are modified
    });

    // Initial plot update
    updatePlot();

    document.getElementById('text').focus();

    function processText(text, appliedRules, system) {
        // Convert text to lowercase
        text = text.toLowerCase();

        // Remove unsupported punctuation
        for (let p of ["'"]) {
            text = text.replaceAll(p, '');
        }
        for (let p of ['/', '\\', '-']) {
            text = text.replaceAll(p, ' ');
        }

        text = addSpacesAroundPunctuation(text);

        // Add placeholders for phrases
        let multiWordMatches = [];

        if (options['abbrv_words']) {
            ({ text, multiWordMatches } = findMultiWordTokens(text, systems[selectedSystem].phrases));
        }

        // Apply all user-defined rules
        for (let rule of systems[system].rules) {
            if (!appliedRules.includes(rule.name)) continue;

            const regex = new RegExp(rule.regex, 'g');
            text = text.replace(regex, rule.replacement);
        }

        return [ text, multiWordMatches];
    }

    function addSpacesAroundPunctuation(text) {
        // Define a regex pattern to match punctuation and digits
        const pattern = /([\d!"#$%&'()*+,-./:;<=>?@[\\\]^_`{|}~])/g;

        // Substitute with spaces before and after the matched characters
        const spacedText = text.replace(pattern, ' $1 ');

        // Return the modified text, stripping any extra spaces at the ends
        return spacedText.trim();
    }

    function tokenizeString(word, system, activeModes) {
        const regexDict = Object.fromEntries(Object.entries(system.glyphs));

        const cleanRegexDict = {};
        for (const key in regexDict) {
            const cleanPattern = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            cleanRegexDict[cleanPattern] = regexDict[key];
        }

        const modeRegexDict = {};
        Object.entries(system.modes).filter(([key, _]) => activeModes.includes(key)).forEach(([key, value]) => {
            modeRegexDict[value.pattern] = value.points;
        });

        const regexList = [
            ...Object.entries(modeRegexDict).map(([pattern, value]) => ({ pattern: new RegExp(`${pattern}`, 'gu'), value, isMode: true })),
            ...Object.entries(cleanRegexDict).map(([pattern, value]) => ({ pattern: new RegExp(`${pattern}`, 'gu'), value, isMode: false }))
        ];

        const memo = {};

        function compareTokenizations(a, b) {
            if (a.modeCount !== b.modeCount) {
                return a.modeCount > b.modeCount;
            }
            if (a.count !== b.count) {
                return a.count < b.count;
            }
            if (a.longestToken !== b.longestToken) {
                return a.longestToken > b.longestToken;
            }
            return false;
        }

        function isValidWordBoundary(start, matchLength) {
            return (start === 0) || (start + matchLength === word.length);
        }

        function findBestTokenization(start) {
            if (start === word.length) {
                return { tokens: [], count: 0, longestToken: 0, regexList: [], modeCount: 0 };
            }

            if (memo[start]) return memo[start];

            let bestTokenization = null;

            for (const { pattern, value, isMode } of regexList) {
                pattern.lastIndex = start;
                const match = pattern.exec(word);
                if (match && match.index === start) {
                    const matchLength = match[0].length;
                    const remaining = findBestTokenization(start + matchLength);

                    if (!remaining) {
                        continue;
                    }

                    const currentTokenization = {
                        tokens: [value, ...remaining.tokens],
                        count: 1 + remaining.count,
                        longestToken: Math.max(matchLength, remaining.longestToken),
                        regexList: [pattern.source, ...remaining.regexList],
                        modeCount: (isMode ? 1 : 0) + remaining.modeCount
                    };

                    if (!bestTokenization || compareTokenizations(currentTokenization, bestTokenization)) {
                        bestTokenization = currentTokenization;
                    }
                }
            }

            memo[start] = bestTokenization || { tokens: [], count: 0, longestToken: 0, regexList: [], modeCount: 0 };
            return memo[start];
        }

        const result = findBestTokenization(0);
        console.log('Final token regex patterns:', result.regexList);
        return result.tokens;
    }

    function tokenizeWithMultiWords(textWithPlaceholders, system, activeModes, multiWordTokens, multiWordMatches) {
        /**
        * Tokenizes the text by first finding multi-word tokens, then tokenizing the remaining words.
        */

        const remainingWords = textWithPlaceholders.split(/\s+/);
        const allTokens = [];

        for (const word of remainingWords) {
            if (word === '§') {
                allTokens.push([multiWordTokens[multiWordMatches.shift()]]);
            } else {
                allTokens.push(tokenizeString(word, system, activeModes));
            }
        }

        return allTokens;
    }

    function findMultiWordTokens(text, multiWordTokens) {
        /**
        * Finds and extracts multi-word tokens from the text.
        */
        const matches = [];

        // Check if multiWordTokens is an object
        if (typeof multiWordTokens === 'object' && !Array.isArray(multiWordTokens)) {
            // Convert object keys to an array
            multiWordTokens = Object.keys(multiWordTokens);
        }

        // Validate that multiWordTokens is now an array
        if (!Array.isArray(multiWordTokens)) {
            throw new Error('multiWordTokens must be an array or an object with keys as tokens.');
        }

        if (multiWordTokens.length == 0) {
            return { text: text, multiWordMatches: matches };
        }

        const escapedTokens = multiWordTokens.map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
        const sortedTokens = escapedTokens.sort((a, b) => b.length - a.length);
        const multiWordPattern = new RegExp(`\\b(${sortedTokens.join('|')})\\b`, 'g');

        const newText = text.replace(multiWordPattern, (match) => {
            matches.push(match);
            return '§';
        });

        return { text: newText, multiWordMatches: matches };
    }

});