// All of these will be loaded in index.html, since they may need to be accessible globally
let glyphSplineData = selectedSystem ? systems[selectedSystem]['glyphs'] : {}
let phraseSplineData = selectedSystem ? systems[selectedSystem]['phrases'] : {}
let modeSplineData = selectedSystem ? systems[selectedSystem]['modes']: {}

const viewport= document.querySelector('.grid-container');
const gridCanvas = document.getElementById('gridCanvas');
const gridCtx = gridCanvas.getContext('2d');
const splineCanvas = document.getElementById('splineCanvas');
const splineCtx = splineCanvas.getContext('2d');
const characterField = document.getElementById('character');
const saveButton = document.getElementById('saveButton');
const saveDropdown = document.getElementById('saveDropdown');
const saveDropdownOptions = document.getElementById('saveDropdownOptions');
const saveMode = document.getElementById('saveMode');
const savePhrase = document.getElementById('savePhrase');
const confirmSaveMode = document.getElementById('confirmSaveMode');
const modeName = document.getElementById('modeName');
const modePattern = document.getElementById('modePattern');
const clearButton = document.getElementById('clearButton');
const deleteButton = document.getElementById('deleteButton');
const deleteDropdown = document.getElementById('deleteDropdown');
const deleteMode = document.getElementById('deleteMode');
const freezeButton = document.getElementById('freezeButton');
const glyphsTitle = document.getElementById('glyphsTitle');
const glyphsList = document.getElementById('glyphsList');
const phrasesTitle = document.getElementById('phrasesTitle');
const phrasesList = document.getElementById('phrasesList');
const modesTitle = document.getElementById('modesTitle');
const modesList = document.getElementById('modesList');
// const centerButton = document.getElementById('centerButton');

const rootStyles = getComputedStyle(document.documentElement);
const colorInk = rootStyles.getPropertyValue('--ink-color').trim()
const colorSelected = rootStyles.getPropertyValue('--selected-color').trim()
const colorDarkSelected = rootStyles.getPropertyValue('--dark-selected-color').trim()
const colorFreeze = rootStyles.getPropertyValue('--freeze-color').trim()
const colorFrozen = rootStyles.getPropertyValue('--frozen-color').trim()
const colorDisabled = rootStyles.getPropertyValue('--disabled-color').trim()

let selectedPoints = [];
let selectedGlyphs = [];
let numPerSelected = [];
let frozenPoints = [];
let numSplinesPerGlyph = [];
const gridSize = 152;
let cellSize = 20;
let unitsPerEm = 1000;
const centerOffset = Math.floor(gridSize / 2) * cellSize;

let zoomLevel = 1;
const zoomStep = 0.1;
let baseWidth = 3040;
let baseHeight = 3040;
const minZoom = Math.min(viewport.clientWidth / baseWidth, viewport.clientHeight / baseHeight);
const maxZoom = 1;

const zoomWrapper = document.getElementById('zoomWrapper');

function resizeCanvases() {
  const scaledWidth = baseWidth * zoomLevel;
  const scaledHeight = baseHeight * zoomLevel;

  for (const canvas of [gridCanvas, splineCanvas]) {
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;
    canvas.style.width = scaledWidth + 'px';
    canvas.style.height = scaledHeight + 'px';
  }
}

function zoomAtCursor(newZoomLevel, cursorX, cursorY) {
    const rect = viewport.getBoundingClientRect();

    // Clamp the new zoom level
    newZoomLevel = Math.max(minZoom, Math.min(maxZoom, newZoomLevel));

    const offsetX = cursorX - rect.left + viewport.scrollLeft;
    const offsetY = cursorY - rect.top + viewport.scrollTop;

    const relX = offsetX / zoomLevel;
    const relY = offsetY / zoomLevel;

    zoomLevel = newZoomLevel;
    resizeCanvases();
    updatePointsField();

    const newOffsetX = relX * zoomLevel;
    const newOffsetY = relY * zoomLevel;

    const scrollLeft = newOffsetX - (cursorX - rect.left);
    const scrollTop = newOffsetY - (cursorY - rect.top);

    // Clamp scroll to canvas bounds
    viewport.scrollLeft = Math.max(0, Math.min(scrollLeft, gridCanvas.width - viewport.clientWidth));
    viewport.scrollTop = Math.max(0, Math.min(scrollTop, gridCanvas.height - viewport.clientHeight));
}

viewport.addEventListener('wheel', (e) => {
  if (e.ctrlKey) {
    e.preventDefault();

    const scaleFactor = 1.1;
    const newZoom = e.deltaY < 0 ? zoomLevel * scaleFactor : zoomLevel / scaleFactor;
    const clampedZoom = Math.min(Math.max(newZoom, 0.1), 10.0);

    zoomAtCursor(clampedZoom, e.clientX, e.clientY);
  }
}, { passive: false });

// Initial setup
resizeCanvases();
updatePointsField();

function drawGrid() {
    gridCtx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);

    const canvasWidth = gridCanvas.width;
    const canvasHeight = gridCanvas.height;

    const centerX = centerOffset * zoomLevel;
    const centerY = centerOffset * zoomLevel;

    const cellStep = cellSize * zoomLevel;
    const emStep = unitsPerEm * zoomLevel;
    const maxOffsetX = Math.max(centerX, canvasWidth - centerX);
    const maxOffsetY = Math.max(centerY, canvasHeight - centerY);

    // Grid lines (merged light/dark for X and Y)
    for (let axis of ['x', 'y']) {
        const isX = axis === 'x';
        const center = isX ? centerX : centerY;
        const maxOffset = isX ? maxOffsetX : maxOffsetY;
        const canvasLimit = isX ? canvasWidth : canvasHeight;

        for (let d = 0; d <= maxOffset; d += cellStep) {
            const pos1 = center + d;
            const pos2 = center - d;

            for (let pos of [pos1, pos2]) {
                if (pos < 0 || pos > canvasLimit) continue;

                const distanceFromCenter = Math.abs(pos - center);
                const isDark = distanceFromCenter % emStep < 0.5 || emStep - (distanceFromCenter % emStep) < 0.5;

                gridCtx.beginPath();
                gridCtx.strokeStyle = isDark ? 'rgba(0, 0, 0, 0.7)' : 'rgba(0, 0, 0, 0.1)';
                gridCtx.lineWidth = isDark? 2 : 1;

                if (isX) {
                    gridCtx.moveTo(pos, 0);
                    gridCtx.lineTo(pos, canvasHeight);
                } else {
                    gridCtx.moveTo(0, pos);
                    gridCtx.lineTo(canvasWidth, pos);
                }

                gridCtx.stroke();
            }
        }
    }

    // Center cross lines
    gridCtx.beginPath();
    gridCtx.strokeStyle = '#000';
    gridCtx.lineWidth = 1;
    gridCtx.moveTo(centerX, 0);
    gridCtx.lineTo(centerX, canvasHeight);
    gridCtx.moveTo(0, centerY);
    gridCtx.lineTo(canvasWidth, centerY);
    gridCtx.stroke();

    // Circle at center
    gridCtx.beginPath();
    gridCtx.arc(centerX, centerY, 20 * zoomLevel, 0, 2 * Math.PI);
    gridCtx.lineWidth = 2;
    gridCtx.stroke();
}

function drawPoints(points = null, color = colorSelected) {
    splineCtx.fillStyle = color;

    const sourcePoints = points || selectedPoints;

    sourcePoints.forEach(([x, y]) => {
        splineCtx.beginPath();
        splineCtx.arc(
            (centerOffset + x * cellSize) * zoomLevel,
            (centerOffset - y * cellSize) * zoomLevel,
            6 * zoomLevel, // scale point radius
            0,
            Math.PI * 2
        );
        splineCtx.fill();
    });
}

function updatePointsField() {
    // Handle zooming both canvases
    gridCtx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
    gridCtx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);
    // gridCtx.setTransform(zoomLevel, 0, 0, zoomLevel, 0, 0);

    splineCtx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
    splineCtx.clearRect(0, 0, splineCanvas.width, splineCanvas.height);
    // splineCtx.setTransform(zoomLevel, 0, 0, zoomLevel, 0, 0); // Apply zoom

    drawGrid(); // Redraw the grid
    splineCtx.clearRect(0, 0, splineCanvas.width, splineCanvas.height); // Clear spline visualization

    // Paint frozen stuff first; this is only ever a single spline
    if (frozenPoints) {
        frozenPoints.forEach((points) => {
            plotSpline(points, colorDisabled, null);
            drawPoints(points, colorDisabled); // Enforce drawing NOW so subsequent drawings will appear above it
        })
    }

    // Exit if no characters are selected
    if (selectedPoints.length === 0) return;

    // Shift all splines prior to the last one
    selectedPoints.forEach((points, splineIndex) => {
        if (points.length > 1){
            plotSpline(points, colorInk, () => {
                // Only draw points for the last spline
                if (splineIndex === selectedPoints.length - 1) {
                    // drawPoints(selectedPoints[splineIndex]);
                    drawPoints(points);
                }
            });
        } else {  // only a single point, so no need to draw a spline
            drawPoints(points, (splineIndex === selectedPoints.length-1) ? colorSelected : colorInk)
        }
    });
}

function plotSpline(points, color = colorInk, callback = null) {
    if (points.length > 1) {

        function bezierInterpolate2D_Dense(points, numSamples = 200) {
            const n = points.length;
            if (n < 2) return [];

            // Step 1: Parameterize by arc length
            const t = [0];
            for (let i = 1; i < n; i++) {
                const dx = points[i].x - points[i - 1].x;
                const dy = points[i].y - points[i - 1].y;
                const dist = Math.hypot(dx, dy);
                t.push(t[i - 1] + dist);
            }

            const totalT = t[n - 1];
            if (totalT === 0) {
                // All points are the same
                return Array(numSamples).fill({ ...points[0] });
            }

            // Step 2: Create dense parameter samples
            const tDense = Array.from({ length: numSamples }, (_, i) => totalT * (i / (numSamples - 1)));

            // Step 3: Build Bézier segments using Catmull-Rom-to-Bézier
            const segments = [];
            for (let i = 0; i < n - 1; i++) {
                const p0 = points[Math.max(i - 1, 0)];
                const p1 = points[i];
                const p2 = points[i + 1];
                const p3 = points[Math.min(i + 2, n - 1)];

                const cp1 = {
                    x: p1.x + (p2.x - p0.x) / 6,
                    y: p1.y + (p2.y - p0.y) / 6,
                };
                const cp2 = {
                    x: p2.x - (p3.x - p1.x) / 6,
                    y: p2.y - (p3.y - p1.y) / 6,
                };

                segments.push({
                    t1: t[i],
                    t2: t[i + 1],
                    p0: p1,
                    cp1,
                    cp2,
                    p3: p2,
                });
            }

            // Step 4: Evaluate Bézier curve at each dense t
            return tDense.map((ti) => {
                // Find which segment ti belongs to
                let seg = segments.find(s => ti >= s.t1 && ti <= s.t2);
                if (!seg) {
                    // Clamp to first or last
                    if (ti <= t[0]) return { ...points[0] };
                    if (ti >= t[n - 1]) return { ...points[n - 1] };
                    seg = segments[segments.length - 1];
                }

                const { t1, t2, p0, cp1, cp2, p3 } = seg;
                const denom = t2 - t1;
                const localT = denom === 0 ? 0 : (ti - t1) / denom;
                const u = 1 - localT;

                const x =
                    u ** 3 * p0.x +
                    3 * u ** 2 * localT * cp1.x +
                    3 * u * localT ** 2 * cp2.x +
                    localT ** 3 * p3.x;

                const y =
                    u ** 3 * p0.y +
                    3 * u ** 2 * localT * cp1.y +
                    3 * u * localT ** 2 * cp2.y +
                    localT ** 3 * p3.y;

                return { x, y };
            });
        }

        const pointObjects = points.map(([x, y]) => ({ x, y }));
        const densePoints = bezierInterpolate2D_Dense(pointObjects);

        densePoints.forEach((pt, i) => {
            const plotX = (pt.x * cellSize + centerOffset) * zoomLevel;
            const plotY = (centerOffset - pt.y * cellSize) * zoomLevel;

            if (i === 0) {
                splineCtx.beginPath();
                splineCtx.lineWidth = 5 * zoomLevel;
                splineCtx.strokeStyle = color;
                splineCtx.lineCap = 'round';

                splineCtx.moveTo(plotX, plotY);
            } else {
                splineCtx.lineTo(plotX, plotY);
            }
        });
        splineCtx.stroke();

    }

    if (callback) callback();
}

gridCanvas.addEventListener('click', (event) => {
    const rect = gridCanvas.getBoundingClientRect();

    // Convert from screen coordinates to logical canvas coordinates
    const canvasX = (event.clientX - rect.left) / zoomLevel;
    const canvasY = (event.clientY - rect.top) / zoomLevel;

    const x = canvasX - centerOffset;
    const y = centerOffset - canvasY;

    const gridX = Math.round(x / cellSize);
    const gridY = Math.round(y / cellSize);

    const isCtrlPressed = event.ctrlKey;

    if (isCtrlPressed || selectedPoints.length === 0) {
        selectedPoints.push([[gridX, gridY]]);
        selectedGlyphs.push('');
        numPerSelected.push(1);
    } else {
        selectedPoints[selectedPoints.length - 1].push([gridX, gridY]);
    }

    updatePointsField();
    refreshButtons();
});

gridCanvas.addEventListener('contextmenu', (event) => {
    event.preventDefault();

    const rect = gridCanvas.getBoundingClientRect();

    const canvasX = (event.clientX - rect.left) / zoomLevel;
    const canvasY = (event.clientY - rect.top) / zoomLevel;

    const x = canvasX - centerOffset;
    const y = centerOffset - canvasY;

    const gridX = Math.round(x / cellSize);
    const gridY = Math.round(y / cellSize);

    const currentSpline = selectedPoints[selectedPoints.length - 1];

    const pointIndex = currentSpline.findLastIndex(
        ([px, py]) => Math.round(px) === gridX && Math.round(py) === gridY
    );

    if (pointIndex !== -1) {
        currentSpline.splice(pointIndex, 1);

        if (currentSpline.length === 0) {
            selectedPoints.pop();
            numPerSelected[numPerSelected.length - 1] -= 1;

            if (numPerSelected[numPerSelected.length - 1] === 0) {
                numPerSelected.pop();
                selectedGlyphs.pop();
            }
        }
    }

    updatePointsField();
    refreshButtons();
});

function handleGlyphSelect(glyph, glyphPoints = null, append = false) {
    if (glyph === null) {
        // deselect everything
        selectedPoints = []
        numPerSelected = []
        selectedGlyphs = []
    }

    if (glyph !== null) {
        // selecting un-selected character
        const newPoints = glyphPoints ? glyphPoints : (glyph in glyphSplineData ? glyphSplineData[glyph] : [])

        // glyphSplineData is assumed to be relative to the origin (0, 0).
        // since the center of the grid is (0.5, 0.5), glyphSplineData has to be shifted when plotting
        const shiftedNewPoints = newPoints.map(spline =>
            spline.map(([x, y]) => [x * gridSize, y * gridSize])
            );

        if (!append) {
            const numToRemove = numPerSelected.pop()
            selectedPoints.splice(-numToRemove, numToRemove)
            selectedGlyphs.pop()
        }

        let shiftedAppendPoints = shiftedNewPoints
        if ((selectedPoints.length > 0) && (selectedPoints[selectedPoints.length - 1].length > 0)) {
            // shift by last point
            const lastSpline = selectedPoints[selectedPoints.length - 1]
            const lastPoint = lastSpline[lastSpline.length - 1]
            const firstPoint = shiftedAppendPoints[0][0]
            shiftedAppendPoints = shiftedAppendPoints.map(spline =>
                spline.map(([x, y]) => [x - firstPoint[0] + lastPoint[0], y - firstPoint[1] + lastPoint[1]])
                );
        }

        selectedPoints = selectedPoints.concat(shiftedAppendPoints)

        selectedGlyphs.push(glyph)
        numPerSelected.push(numSplinesPerGlyph[glyph])
    } else {  // not allowed to select the same character multiple times

    }
}

function refreshButtons() {
    refreshDeleteButton();
    refreshFreezeButton();
    refreshSaveButton();

    // update coloring of spline list
    document.querySelectorAll('.char-list-item').forEach(item => {
        item.classList.remove('selected');
        item.classList.remove('joining');

        if (selectedGlyphs.includes(item.textContent)) {
            if (item.textContent === selectedGlyphs[selectedGlyphs.length - 1]) {
                // most recently-selected glyph
                item.classList.add('selected');
            } else {
                // preceding glyph
                item.classList.add('joining');
            }
        }
    });

    // update coloring of spline list
    document.querySelectorAll('.char-list-item').forEach(item => {
        item.classList.remove('selected');
        item.classList.remove('joining');

        if (selectedGlyphs.includes(item.textContent)) {
            if (item.textContent === selectedGlyphs[selectedGlyphs.length - 1]) {
                // most recently-selected glyph
                item.classList.add('selected');
            } else {
                // preceding glyph
                item.classList.add('joining');
            }
        }
    });
}

function refreshSaveButton() {
    // can't do things if no points selected, or character of selected points is not specified
    saveButton.disabled = (selectedPoints.length === 0) || (characterField.value === '')

    // for hiding dropdown options; have to use 'show' tag
    if (!saveButton.disabled) {
        saveDropdown.disabled = false;              // Enable the dropdown button
        saveDropdownOptions.classList.remove('show');  // Ensure menu is hidden
    } else {
        saveDropdown.disabled = true;               // Disable the dropdown button
        saveDropdownOptions.classList.remove('show');  // Hide the dropdown menu
    }

    const noneSelected = (selectedPoints.length === 0) || (selectedPoints[selectedPoints.length - 1].length === 0)
    clearButton.disabled = noneSelected
}

function refreshFreezeButton() {
    freezeButton.textContent = frozenPoints.length ? 'Unfreeze' : 'Freeze';
    freezeButton.disabled = (frozenPoints.length === 0) && ((selectedPoints.length === 0) || (selectedPoints[selectedPoints.length - 1].length === 0))
}

function refreshDeleteButton() {
    deleteButton.disabled = (characterField.value.length === 0)
    deleteDropdown.disabled = deleteButton.disabled
}

function scrollIfNeeded(item) {
    // Smarter scrollIntoView which accounts for the size of the item and its parent
    const rect = item.getBoundingClientRect();
    const parentRect = item.parentNode.getBoundingClientRect();

    // Check if item is fully visible within its parent
    const isFullyVisible = rect.top >= parentRect.top && rect.bottom <= parentRect.bottom;

    // Scroll into view only if the item is not fully visible
    if (!isFullyVisible) {
        item.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function rebuildGlyphList() {
    glyphsList.innerHTML = '';
    glyphsTitle.childNodes[0].textContent = 'Glyphs (' + Object.keys(glyphSplineData).length + ')'

    for (const [glyph, points] of Object.entries(glyphSplineData)) {
        numSplinesPerGlyph[glyph] = points.length  // used during de-selection

        const listItem = document.createElement('div');
        listItem.className = 'char-list-item';
        listItem.textContent = glyph;

        listItem.addEventListener('click', (event) => {
            characterField.focus()
            characterField.value = ''
            handleGlyphSelect(glyph, null, event.ctrlKey)
            refreshButtons();
            updatePointsField();
            // scrollIfNeeded(listItem)
        });
        glyphsList.appendChild(listItem);
    }
}

function rebuildPhrasesList() {
    phrasesList.innerHTML = '';
    phrasesTitle.childNodes[0].textContent = 'Phrases (' + Object.keys(phraseSplineData).length + ')'

    for (const [phrase, points] of Object.entries(phraseSplineData)) {
        numSplinesPerGlyph[phrase] = points.length  // used during de-selection

        const listItem = document.createElement('div');
        listItem.className = 'char-list-item';
        listItem.textContent = phrase;

        listItem.addEventListener('click', (event) => {
            characterField.focus()
            characterField.value = phrase
            handleGlyphSelect(phrase, points, event.ctrlKey)
            refreshButtons();
            updatePointsField();
        });
        phrasesList.appendChild(listItem);
    }
}

function rebuildModesList() {
    modesList.innerHTML = '';
    modesTitle.childNodes[0].textContent = 'Modes (' + Object.keys(modeSplineData).length + ')'

    for (const [mode, valuesDict] of Object.entries(modeSplineData)) {
        points = valuesDict['points']

        numSplinesPerGlyph[mode] = points.length  // used during de-selection

        const listItem = document.createElement('div');
        listItem.className = 'char-list-item';
        listItem.textContent = mode;

        listItem.addEventListener('click', (event) => {
            characterField.focus()
            characterField.value = mode
            handleGlyphSelect(mode, modeSplineData[mode]['points'], event.ctrlKey)
            refreshButtons();
            updatePointsField();

            modeName.value = mode
            modePattern.value = valuesDict['pattern']
        });
        modesList.appendChild(listItem);
    }
}

saveButton.addEventListener('click', () => {
    if (selectedPoints.length) {
        const newName = characterField.value.trim()

        // points have to be rescaled to [0, 1], then shifted by [0.5, 0.5]
        const newPoints = selectedPoints.map(spline =>
                spline.map(([x, y]) => [x / gridSize, y / gridSize])
                )

        glyphSplineData[newName] = newPoints
        saveSystems();  // from index.html

        rebuildGlyphList();
        handleGlyphSelect(null);
        refreshButtons();
        updatePointsField();
        characterField.value = '';
        characterField.focus();
    }

});

// Function to reset mode name and pattern fields
function resetModeFields() {
    modeName.value = '';
    modePattern.value = '';
    confirmSaveMode.disabled = true; // Optionally disable the button again
}

// Enable/Disable the save button based on the input fields
function validateFields() {
    if (modeName.value.trim() && modePattern.value.trim()) {
        confirmSaveMode.disabled = false;
    } else {
        confirmSaveMode.disabled = true;
    }
}

// Add input event listeners to both fields
modeName.addEventListener('input', validateFields);
modePattern.addEventListener('input', validateFields);

// Add event listener to the "Cancel" button
document.querySelector('.modal-footer .btn-secondary').addEventListener('click', resetModeFields);

confirmSaveMode.addEventListener('click', () => {
    if (!modeName.value.trim() || !modePattern.value.trim()) {
        alert("Both 'Name' and 'Pattern' fields are required.");
    } else {
        if (selectedPoints.length) {

            const newPoints = selectedPoints.map(spline =>
                    spline.map(([x, y]) => [x / gridSize, y / gridSize])
                    )
            modeSplineData[modeName.value.trim()] = {points: newPoints, pattern: modePattern.value.trim()}
            saveSystems()

            rebuildModesList();
            handleGlyphSelect(null);
            refreshButtons();
            updatePointsField();
            characterField.value = '';
            characterField.focus();

        }
    }
    // Hide the modal after saving
    const saveModeModal = bootstrap.Modal.getInstance(document.getElementById('saveModeModal'));
    saveModeModal.hide();
});

saveMode.addEventListener('click', () => {
    // Open the modal when saveMode is clicked
    const saveModeModal = new bootstrap.Modal(document.getElementById('saveModeModal'));

    modeName.value = characterField.value.trim(),
    saveModeModal.show();
});

savePhrase.addEventListener('click', () => {
    if (selectedPoints.length) {

        const newPoints = selectedPoints.map(spline =>
                spline.map(([x, y]) => [x / gridSize, y / gridSize])
                )
        phraseSplineData[characterField.value.trim()] = newPoints
        saveSystems()

        rebuildPhrasesList();
        handleGlyphSelect(null);
        refreshButtons();
        updatePointsField();
        characterField.value = '';
        characterField.focus();
    }
});


clearButton.addEventListener('click', () => {
    selectedPoints.pop()
    numPerSelected[numPerSelected.length - 1] -= 1

    if (numPerSelected[numPerSelected.length - 1] === 0) {
        selectedGlyphs.pop()
        numPerSelected.pop()
    }
    updatePointsField();
    refreshButtons();
});

deleteButton.addEventListener('click', () => {
    if (selectedPoints) {
        delete glyphSplineData[characterField.value.trim()]
        saveSystems();
        rebuildGlyphList();
        handleGlyphSelect(null);
        refreshButtons();
        updatePointsField();
        characterField.value = '';
        characterField.focus();
    }
});

deleteMode.addEventListener('click', () => {
    delete modeSplineData[characterField.value.trim()]
    saveSystems();
    rebuildModesList();
    handleGlyphSelect(null);
    refreshButtons();
    updatePointsField();
    characterField.value = '';
    characterField.focus();
});

deletePhrase.addEventListener('click', () => {
    delete phraseSplineData[characterField.value.trim()]
    saveSystems();
    rebuildPhrasesList();
    handleGlyphSelect(null);
    refreshButtons();
    updatePointsField();
    characterField.value = '';
    characterField.focus();
});

freezeButton.addEventListener('click', () => {
    splineCtx.clearRect(0, 0, splineCanvas.width, splineCanvas.height);

    if (freezeButton.textContent === 'Freeze') { // freeze
        frozenPoints = selectedPoints.map(point => point.slice())
        selectedPoints = []
        selectedGlyphs = []

        refreshButtons();

    } else {  // unfreeze
        frozenPoints = [];
        refreshFreezeButton();
    }

    updatePointsField();
    characterField.focus();
});

// to avoid too-fast updates when typing into char field
let debounceTimeout;
function debounce(func, delay) {
    return function(...args) {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => func.apply(this, args), delay);
    };
}

// Debounce the plot update to avoid too many requests
const debouncedKeyCheck = debounce(keyCheck, 100);  // ms?

function keyCheck(event) {
    sortAndDisplayList();
}

// Bind the input event on textarea and change event on checkboxes
characterField.addEventListener('keyup', function(event) {
    if (event.key !== 'Control') {
        debouncedKeyCheck(event);
        refreshButtons();
    }
})

function sortAndDisplayList() {
    sortOneList(glyphsList);
    glyphsList.scrollTop = glyphsList.scrollHeight

    sortOneList(phrasesList);
    phrasesList.scrollTop = phrasesList.scrollHeight

    sortOneList(modesList);
    modesList.scrollTop = modesList.scrollHeight
}

function sortOneList(listToSort) {
    // Get the value from the character input field
    const searchTerm = document.getElementById('character').value.toLowerCase();

    // Get current list items
    let listItems = Array.from(listToSort.children);

    // Function to check if an item contains the search term
    const containsSearchTerm = text => text.toLowerCase().includes(searchTerm);
    const startsWithSearchTerm = text => text.toLowerCase().startsWith(searchTerm);

    // Separate items into those that start with the search term, those that contain it elsewhere, and those that do not contain it
    let startsWithItems = listItems.filter(item => startsWithSearchTerm(item.textContent));
    let containsItems = listItems.filter(item => containsSearchTerm(item.textContent) && !startsWithSearchTerm(item.textContent));
    let nonMatchingItems = listItems.filter(item => !containsSearchTerm(item.textContent));

    // Sort each array alphabetically
    startsWithItems.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
    containsItems.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));
    nonMatchingItems.sort((a, b) => a.textContent.toLowerCase().localeCompare(b.textContent.toLowerCase()));

    // Combine the arrays: items starting with the search term first, then items containing it elsewhere, then non-matching items
    let sortedItems = startsWithItems.concat(containsItems, nonMatchingItems);

    // Clear the current list and re-append sorted items
    listToSort.innerHTML = '';
    sortedItems.slice().reverse().forEach(item => {
        listToSort.appendChild(item);
    });
}

refreshButtons();
drawGrid();
rebuildGlyphList();
rebuildPhrasesList();
rebuildModesList();

function centerGridView() {
    const gridContainer = document.querySelector('.grid-container');

    const containerWidth = gridContainer.clientWidth;
    const containerHeight = gridContainer.clientHeight;

    const gridWidth = gridCanvas.width * zoomLevel;
    const gridHeight = gridCanvas.height * zoomLevel;

    const centerX = (gridWidth - containerWidth) / 2;
    const centerY = (gridHeight - containerHeight) / 2;

    gridContainer.scrollLeft = centerX;
    gridContainer.scrollTop = centerY;
}

document.addEventListener("DOMContentLoaded", function() {
    centerGridView()
});

// centerButton.addEventListener('click', centerGridView)

characterField.focus();

document.getElementById('saveSettingsButton').addEventListener('click', () => {
    const newCellSize = parseInt(document.getElementById('cellSize').value, 10);
    const newUnitsPerEm = parseInt(document.getElementById('unitsPerEm').value, 10);

    if (newCellSize >= 10 && newCellSize <= 100 && newUnitsPerEm >= 1000 && newUnitsPerEm <= 2048) {
        cellSize = newCellSize
        unitsPerEm = newUnitsPerEm

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
        modal.hide();

        updatePointsField();
    } else {
        alert('Please enter values within the allowed ranges.');
    }
});

function populateSettingsForm() {
    document.getElementById('cellSize').value = cellSize;
    document.getElementById('unitsPerEm').value = unitsPerEm;
}

document.getElementById('settingsModal').addEventListener('show.bs.modal', () => {
    populateSettingsForm();
});

const cellSizeInput = document.getElementById('cellSize');
const unitsPerEmInput = document.getElementById('unitsPerEm');

let lastCellSize = parseInt(cellSizeInput.value, 10) || 40;
let lastUnitsPerEm = parseInt(unitsPerEmInput.value, 10) || 1024;

// Utility: Get valid divisors of any number within range
function getValidDivisors(ofValue, min = 10, max = 100) {
    const divisors = [];
    for (let i = min; i <= Math.min(max, ofValue); i++) {
        if (ofValue % i === 0) divisors.push(i);
    }
    return divisors;
}

function snapCellSize(mode = 'nearest') {
    const unitsPerEm = parseInt(unitsPerEmInput.value, 10);
    const current = parseInt(cellSizeInput.value, 10);
    if (isNaN(unitsPerEm)) return;

    const divisors = getValidDivisors(unitsPerEm, 10, 100).sort((a, b) => a - b);

    if (divisors.length === 0) return;

    let next;

    if (mode === 'up') {
        next = divisors.find(v => v > current) || divisors[divisors.length - 1];
    } else if (mode === 'down') {
        next = [...divisors].reverse().find(v => v < current) || divisors[0];
    } else {
        // Snap to nearest valid value
        next = divisors.reduce((prev, curr) =>
            Math.abs(curr - current) < Math.abs(prev - current) ? curr : prev, divisors[0]);
    }

    if (current !== next || unitsPerEm % current !== 0) {
        cellSizeInput.value = next;
        lastCellSize = next;
    }
}

// Snap cellSize on user input (with up/down detection)
cellSizeInput.addEventListener('input', () => {
    const current = parseInt(cellSizeInput.value, 10);
    const direction = current > lastCellSize ? 'up' : current < lastCellSize ? 'down' : 'nearest';
    snapCellSize(direction);
});

// Snap to nearest on blur/commit
cellSizeInput.addEventListener('change', () => snapCellSize('nearest'));

unitsPerEmInput.addEventListener('input', () => {
    setTimeout(() => {
        lastUnitsPerEm = parseInt(unitsPerEmInput.value, 10);
        snapCellSize('nearest');
    }, 0);
});

unitsPerEmInput.addEventListener('change', () => {
    lastUnitsPerEm = parseInt(unitsPerEmInput.value, 10);
    snapCellSize('nearest');
});
