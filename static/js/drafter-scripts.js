// All of these will be loaded in index.html, since they may need to be accessible globally
let glyphSplineData = selectedSystem ? systems[selectedSystem]['glyphs'] : {}
let phraseSplineData = selectedSystem ? systems[selectedSystem]['phrases'] : {}
let modeSplineData = selectedSystem ? systems[selectedSystem]['modes']: {}

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
const cellSize = 20;
const centerOffset = Math.floor(gridSize / 2) * cellSize;

let zoomLevel = 1;
const zoomStep = 0.1;
const minZoom = 750.0 / 3040.0
const maxZoom = 1;

const zoomWrapper = document.getElementById('zoomWrapper');

function applyZoom() {
    updateZoomWrapperSize();
    updatePointsField();
    centerGridView();
    clampScrollToCanvas();

    const container = document.querySelector('.grid-container');
    const wrapper = document.getElementById('zoomWrapper');

    console.log("Scroll container size:", container.clientWidth, container.clientHeight);
    console.log("Wrapper size:", wrapper.offsetWidth, wrapper.offsetHeight);
    console.log("Max scrollLeft should be:", wrapper.offsetWidth - container.clientWidth);

}

function updateZoomWrapperSize() {
    const zoomWrapper = document.getElementById('zoomWrapper');
    const baseWidth = gridCanvas.width;
    const baseHeight = gridCanvas.height;

    const scaledWidth = baseWidth * zoomLevel;
    const scaledHeight = baseHeight * zoomLevel;

    // Resize wrapper only, NOT the canvas itself
    zoomWrapper.style.width = `${scaledWidth}px`;
    zoomWrapper.style.height = `${scaledHeight}px`;

    // // ❌ DO NOT scale canvas DOM size — keep it matching internal resolution
    // [gridCanvas, splineCanvas].forEach(canvas => {
    //     canvas.style.width = `${baseWidth}px`;  // Match internal resolution
    //     canvas.style.height = `${baseHeight}px`;
    // });
}

function clampScrollToCanvas() {
    const container = document.querySelector('.grid-container');
    const wrapper = document.getElementById('zoomWrapper');

    const maxScrollLeft = Math.max(0, wrapper.offsetWidth - container.clientWidth);
    const maxScrollTop = Math.max(0, wrapper.offsetHeight - container.clientHeight);

    container.scrollLeft = Math.max(0, Math.min(container.scrollLeft, maxScrollLeft));
    container.scrollTop = Math.max(0, Math.min(container.scrollTop, maxScrollTop));
}


// Mouse wheel for zooming
document.querySelector('.grid-container').addEventListener('wheel', function (e) {
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        if (e.deltaY < 0) {
            // Zoom in
            zoomLevel = Math.min(zoomLevel + zoomStep, maxZoom);
        } else {
            // Zoom out
            zoomLevel = Math.max(zoomLevel - zoomStep, minZoom);
        }
        applyZoom();
    }
});

function drawGrid() {
    // Now draw everything in the zoomed context
    gridCtx.beginPath();
    gridCtx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    gridCtx.lineWidth = 1;
    for (let i = 0; i <= gridSize; i++) {
        gridCtx.moveTo(i * cellSize, 0);
        gridCtx.lineTo(i * cellSize, gridCanvas.height);
        gridCtx.moveTo(0, i * cellSize);
        gridCtx.lineTo(gridCanvas.width, i * cellSize);
    }
    gridCtx.stroke();

    // Draw the darker center lines
    gridCtx.beginPath();
    gridCtx.strokeStyle = '#000';
    gridCtx.lineWidth = 1;
    const centerX = centerOffset;
    const centerY = centerOffset;

    gridCtx.moveTo(centerX, 0);
    gridCtx.lineTo(centerX, gridCanvas.height);
    gridCtx.moveTo(0, centerY);
    gridCtx.lineTo(gridCanvas.width, centerY);
    gridCtx.stroke();

    // Draw thicker lines at 120 px intervals
    gridCtx.beginPath();
    for (let y = 80; y <= 2980; y += 120) {
        gridCtx.moveTo(0, y);
        gridCtx.lineTo(3040, y);
    }
    gridCtx.stroke();

    gridCtx.beginPath();
    for (let x = 80; x <= 2980; x += 120) {
        gridCtx.moveTo(x, 0);
        gridCtx.lineTo(x, 3040);
    }
    gridCtx.stroke();

    // Draw circle
    gridCtx.beginPath();
    gridCtx.arc(1520, 1520, 20, 0, 2 * Math.PI);
    gridCtx.lineWidth = 2;
    gridCtx.stroke();
}

function drawPoints(points = null, color = colorSelected) {
    splineCtx.fillStyle = color;

    const sourcePoints = points || selectedPoints;

    sourcePoints.forEach(([x, y]) => {
        splineCtx.beginPath();
        splineCtx.arc(centerOffset + x * cellSize, centerOffset - y * cellSize, 6, 0, Math.PI * 2);
        splineCtx.fill();
    });
}

function updatePointsField() {
    // Handle zooming both canvases
    gridCtx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
    gridCtx.clearRect(0, 0, gridCanvas.width, gridCanvas.height);
    gridCtx.setTransform(zoomLevel, 0, 0, zoomLevel, 0, 0);

    splineCtx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
    splineCtx.clearRect(0, 0, splineCanvas.width, splineCanvas.height);
    splineCtx.setTransform(zoomLevel, 0, 0, zoomLevel, 0, 0); // Apply zoom

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
        // Spline math as-is
        const t = points.map((_, i) => i / (points.length - 1));

        const interpolate = (t, values) => {
            const n = values.length;
            const a = values.slice();
            const b = new Array(n).fill(0);
            const d = new Array(n).fill(0);
            const h = new Array(n - 1).fill(0).map((_, i) => t[i + 1] - t[i]);

            const alpha = new Array(n - 1).fill(0).map((_, i) => {
                if (i === 0) return 0;
                return (3 / h[i] * (a[i + 1] - a[i]) - 3 / h[i - 1] * (a[i] - a[i - 1]));
            });

            const c = new Array(n).fill(0);
            const l = new Array(n).fill(1);
            const mu = new Array(n).fill(0);
            const z = new Array(n).fill(0);

            for (let i = 1; i < n - 1; i++) {
                l[i] = 2 * (t[i + 1] - t[i - 1]) - h[i - 1] * mu[i - 1];
                mu[i] = h[i] / l[i];
                z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i];
            }

            for (let j = n - 2; j >= 0; j--) {
                c[j] = z[j] - mu[j] * c[j + 1];
                b[j] = (a[j + 1] - a[j]) / h[j] - h[j] * (c[j + 1] + 2 * c[j]) / 3;
                d[j] = (c[j + 1] - c[j]) / (3 * h[j]);
            }

            return { a, b, c, d, t };
        };

        const splinePoints = (coeffs, numPoints) => {
            const { a, b, c, d, t } = coeffs;
            const result = [];

            for (let i = 0; i < t.length - 1; i++) {
                const step = (t[i + 1] - t[i]) / numPoints;
                for (let j = 0; j <= numPoints; j++) {
                    const x = t[i] + j * step;
                    const dx = x - t[i];
                    const value = a[i] + b[i] * dx + c[i] * dx ** 2 + d[i] * dx ** 3;
                    result.push(value);
                }
            }

            return result;
        };

        const x = points.map(p => p[0]);
        const y = points.map(p => p[1]);

        const xCoeffs = interpolate(t, x);
        const yCoeffs = interpolate(t, y);

        const xDense = splinePoints(xCoeffs, 20);
        const yDense = splinePoints(yCoeffs, 20);

        splineCtx.beginPath();
        splineCtx.lineWidth = 5;
        splineCtx.strokeStyle = color;
        splineCtx.lineCap = 'round';

        xDense.forEach((x, index) => {
            const plotX = x * cellSize + centerOffset;
            const plotY = centerOffset - yDense[index] * cellSize;
            if (index === 0) {
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

    // Adjust for zoom: map from screen coords to canvas coords
    const canvasX = (event.clientX - rect.left) / zoomLevel;
    const canvasY = (event.clientY - rect.top) / zoomLevel;

    // Now convert to grid coordinates
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
    event.preventDefault(); // Prevent the default right-click menu

    const rect = gridCanvas.getBoundingClientRect();

    // Convert screen pixels to canvas coordinates with zoom correction
    const canvasX = (event.clientX - rect.left) / zoomLevel;
    const canvasY = (event.clientY - rect.top) / zoomLevel;

    // Convert canvas coords to grid coords
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
            // Remove this spline entirely
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