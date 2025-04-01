const systemsJson = localStorage.getItem('systems');
let systems = systemsJson ? JSON.parse(systemsJson) : {}

const selectedSystemJson = localStorage.getItem('selectedSystem')
let selectedSystem = selectedSystemJson ? selectedSystemJson : null

const navbarElement = document.getElementById('navbarDropdown');  // may be null at first
// navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

// Initialize Bootstrap tooltips
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

// document.getElementById('downloadSystem').addEventListener('click', handleDownloadSystems);

function saveSystems() {
    // TODO: this is inefficient; should only update current system
    // TODO: there can be an issue when you make an edit in one page,
    // then make another edit in a second page without refreshing first.
    // this will overwrite the first set of changes
    const systemsJson = JSON.stringify(systems);
    localStorage.setItem('systems', systemsJson);

    // saveSystemToServer(selectedSystem, systems[selectedSystem])
}

async function saveSystemToServer(systemName, systemData) {
    const requiredKeys = ['glyphs', 'modes', 'rules', 'phrases'];

    // Ensure the dictionary has the required keys
    for (const key of requiredKeys) {
        if (!(key in systemData)) {
            console.error(`Missing key: ${key}`);
            return;
        }
    }

    try {
        // Create a new instance of JSZip
        const zip = new JSZip();

        // Save each entry as a JSON file
        for (const key of requiredKeys) {
            const jsonString = JSON.stringify(systemData[key], null, 4);
            zip.file(`${key}.json`, jsonString);
        }

        // Generate the ZIP file asynchronously
        const content = await zip.generateAsync({ type: "blob" });

        // Check if showSaveFilePicker is supported
        if ('showSaveFilePicker' in window) {
            const options = {
                suggestedName: `${systemName}.zip`,
                types: [{
                    description: 'ZIP files',
                    accept: {
                        'application/zip': ['.zip'],
                    },
                }],
            };

            const fileHandle = await window.showSaveFilePicker(options);
            const writableStream = await fileHandle.createWritable();
            await writableStream.write(content);
            await writableStream.close();
        } else {
            // Fallback method using a temporary anchor element
            const link = document.createElement('a');
            link.href = URL.createObjectURL(content);
            link.download = `${systemName}.zip`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        console.log(`System saved as ${systemName}.zip`);
    } catch (err) {
        if (err.name === 'AbortError') {
            console.log('User canceled the save operation');
        } else {
            console.error('Error during save:', err);
        }
    }
}

function newSystem() {

    // Prompt user for the system name
    const inputName = prompt("Name for new system:");
    if (!inputName) return; // Exit if user cancels or enters nothing

    // Initialize new system object
    const newSystemData = {
        modes: {},
        glyphs: {},
        rules: [],
        phrases: {}
    };

    // Set selectedSystem and add to systems
    selectedSystem = inputName;
    systems[selectedSystem] = newSystemData;

    // Store in localStorage
    localStorage.setItem('selectedSystem', selectedSystem);
    localStorage.setItem('systems', JSON.stringify(systems));

    // Update navbar or UI
    navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

    // Reload the page
    location.reload();
}


function deleteSystem() {
    if (!selectedSystem) {
        alert("No system is currently selected.");
        return;
    }

    const confirmDelete = confirm(`Are you sure you want to delete the system "${selectedSystem}"? This cannot be undone.`);
    if (!confirmDelete) return;

    // Delete the selected system
    delete systems[selectedSystem];

    // Clear selectedSystem
    selectedSystem = null;

    // Update localStorage
    localStorage.setItem('systems', JSON.stringify(systems));
    localStorage.removeItem('selectedSystem');

    // Update UI
    navbarElement.textContent = 'system: select';

    // Optionally reload the page
    location.reload();
}



async function loadSystemData(systemName) {
    const basePath = `./static/data/systems/${systemName}`;
    const requiredFiles = ['glyphs.json', 'modes.json', 'rules.json', 'phrases.json'];
    const systemData = {};

    try {
        for (const filename of requiredFiles) {
            const response = await fetch(`${basePath}/${filename}`);
            if (!response.ok) {
                throw new Error(`Failed to load ${filename}`);
            }
            const content = await response.json();
            const key = filename.replace('.json', '');
            systemData[key] = content;
        }

        systems[systemName] = systemData;

        // location.reload();
    } catch (error) {
        console.error('Error loading system data:', error);
    }
}

function importSystem() {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.zip';

    fileInput.onchange = function(event) {
        const file = event.target.files[0];
        if (!file) return;

        const systemName = file.name.replace(/\.zip$/i, '');

        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const zip = await JSZip.loadAsync(e.target.result);

                // Helper to load and parse JSON from a file inside the zip
                const loadJson = async (filename) => {
                    const fileObj = zip.file(filename);
                    if (!fileObj) return filename === 'rules.json' ? [] : {};
                    const content = await fileObj.async('string');
                    return JSON.parse(content);
                };

                const [glyphs, modes, rules, phrases] = await Promise.all([
                    loadJson('glyphs.json'),
                    loadJson('modes.json'),
                    loadJson('rules.json'),
                    loadJson('phrases.json')
                ]);

                systems[systemName] = { glyphs, modes, rules, phrases };
                selectedSystem = systemName;

                localStorage.setItem('systems', JSON.stringify(systems));
                localStorage.setItem('selectedSystem', selectedSystem);

                location.reload();

            } catch (err) {
                console.error("Failed to import zip file:", err);
                alert("Error importing system. Please check that the zip contains valid JSON files.");
            }
        };

        reader.readAsArrayBuffer(file);
    };

    fileInput.click();
}

// Example usage in the export button event listener
function addSystemsToDropdown() {
    // Get the systems list container
    const systemsListContainer = document.getElementById('systemsList');
    const navbarElement = document.getElementById('navbarDropdown');

    // Clear any existing items
    systemsListContainer.innerHTML = '';

    // Fetch the JSON file
    fetch('./static/data/systems/available_systems.json')
    .then(response => {
        if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // displayDownloadableSystems(data.systems);
        // const downloadableList = document.getElementById('downloadableList');

        // Loop through the systems and create list items
        // data.systems.forEach(systemKey => {
        // Create a Set to avoid duplicates from merging both sources
        const allSystemKeys = new Set([
            ...(data.systems || []),
            ...Object.keys(systems || {})
        ]);

        // Loop through the combined set of system keys
        allSystemKeys.forEach(systemKey => {
                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item', 'list-group-item-action');
                // listItem.innerText = system;
                listItem.innerHTML = `<a class="dropdown-item" href="#">${systemKey}</a>`; // Use the key as the link text

                // Add a click event listener to the anchor element
                listItem.querySelector('a').addEventListener('click', async function (event) {

                // Add click event listener to each item
                if (!(systemKey in systems)) {
                    // Load the selected system's data
                    await loadSystemData(systemKey);
                }

                selectedSystem = systemKey;
                localStorage.setItem('selectedSystem', selectedSystem);
                localStorage.setItem('systems', JSON.stringify(systems));
                navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

                location.reload(); // This will reload the current page
            });

            // downloadableList.appendChild(listItem)
            systemsListContainer.appendChild(listItem);
        });
    })
    .catch(error => console.error('Error loading JSON:', error));
}

async function loadSystemsAndUpdateDropdown() {
    addSystemsToDropdown();     // Then run addSystemsToDropdown after

    const divider = document.getElementById("systemsDivider");

    divider.style.display = "block"
}

// Call the fetch function on page load
document.addEventListener('DOMContentLoaded', function () {
    const navbarHTML = `
    <nav class="navbar navbar-expand-lg navbar-light" style="background-color:var(--background-color);">
        <a class="navbar-brand" href="index.html">abbrv</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav"
            aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav">
                <li class="nav-item">
                    <a class="nav-link" href="writer.html">write</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="drafter.html">draft</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="rules.html">rules</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="help.html">help</a>
                </li>
                <!-- Systems Dropdown -->
                <li class="nav-item dropdown">
                    <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button"
                        data-bs-toggle="dropdown" aria-expanded="false">
                        system: select
                    </a>
                    <ul class="dropdown-menu" aria-labelledby="navbarDropdown">
                        <div id="systemsList"></div>
                        <li><hr class="dropdown-divider" id="systemsDivider"></li>
                        <li><a class="dropdown-item" href="#" id="newSystem">New</a></li>
                        <li><a class="dropdown-item" href="#" id="deleteSystem">Delete</a></li>
                        <li><a class="dropdown-item" href="#" id="importSystem">Import</a></li>
                        <!-- Modified: Export is now a dropdown -->
                        <li class="dropdown-submenu">
                            <a class="dropdown-item dropdown-toggle" href="#" id="exportDropdown">Export</a>
                            <ul class="dropdown-menu" aria-labelledby="exportDropdown">
                                <li><a class="dropdown-item" href="#" id="exportOpenType">OpenType</a></li>
                                <li><a class="dropdown-item" href="#" id="exportZip">ZIP</a></li>
                            </ul>
                        </li>
                        <li><a class="dropdown-item" href="#" id="openUploadModal" data-bs-toggle="modal"
                            data-bs-target="#uploadModal">Upload</a></li>
                    </ul>
                </li>
            </ul>
            <!-- Don't need discord button for index.html since it's already in hero area -->
        </div>
        <!-- Modal for Uploading Files -->
        <div class="modal fade" id="uploadModal" tabindex="-1" aria-labelledby="uploadModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="uploadModalLabel">Upload your system</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>
                            System upload is currently only supported through Github.
                            This is to allow us to run automated validation checks to ensure that your uploaded files are safe and correctly formatted, and to provide ease-of-use commands to facilitate merging into the master branch.
                        </p>


                        <p>To upload a new system, please follow these steps: </p>
                        <ul>
                            <li><a href="https://gist.github.com/" target="_blank">Create a new GitHub Gist</a></li>
                            <ul>
                                <li>Drag-and-drop your <code>[glyphs, modes, rules, phrases].json</code> files.</li>
                                <li>Make sure they're uploaded as four separate files.</li>
                            </ul>
                            <li><a href="https://github.com/jvita/abbrv/issues/new?template=submit_upload.yml" target="_blank">Open a new issue</a> on the <b>abbrv</b> repo</li>
                            <ul>
                                <li>GitHub will post a comment with additional instructions.</li>
                            </ul>
                            <li>Add a comment to the issue with the command: <code>/submit [url_of_your_gist]</code></li>
                            <ul>
                                <li>This will automatically validate the files from your gist and open a new PR for merging your results.</li>
                            </ul>
                        </ul>

                        <p>If you do not have a Github account, contact <a href="https://www.reddit.com/user/jerrshv/">u/jerrshv</a> on Reddit for assistance.</p>

                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
        <!-- Modal for downloading systems -->
        <div class="modal fade" id="downloadSystemsModal" tabindex="-1" aria-labelledby="downloadSystemsModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="downloadSystemsModalLabel">Available systems</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <ul id="downloadableList" class="list-group">
                        </ul>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    </nav>
    `

    const navbarContainer = document.getElementById('navbar-container');
    if (navbarContainer) {
        navbarContainer.innerHTML = navbarHTML;
    }

    const navbarElement = document.getElementById('navbarDropdown');
    navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

    loadSystemsAndUpdateDropdown();

    document.getElementById('exportZip').addEventListener('click', async function() {
        await saveSystemToServer(selectedSystem, systems[selectedSystem])
    });

    document.getElementById('newSystem').addEventListener('click', newSystem)
    document.getElementById('deleteSystem').addEventListener('click', deleteSystem);
    document.getElementById('importSystem').addEventListener('click', importSystem);

    // Add CSS for the nested dropdown
    const style = document.createElement('style');
    style.textContent = `
        .dropdown-submenu {
            position: relative;
        }
        
        .dropdown-submenu .dropdown-menu {
            top: 0;
            left: 100%;
            margin-top: -1px;
            display: none;
        }
        
        .dropdown-submenu:hover > .dropdown-menu {
            display: block;
        }
    `;
    document.head.appendChild(style);
    
    // Add event listener for the Export dropdown
    document.getElementById('exportDropdown').addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const menu = this.nextElementSibling;
        if (menu.style.display === 'block') {
            menu.style.display = 'none';
        } else {
            menu.style.display = 'block';
        }
    });
    
    // Event listeners for export options
    document.getElementById('exportOpenType').addEventListener('click', function(e) {
        e.preventDefault();
        // Add your OpenType export logic here
        console.log('Export as OpenType');
    });
    
    document.getElementById('exportZip').addEventListener('click', function(e) {
        e.preventDefault();
        // Add your Zip export logic here
        console.log('Export as Zip');
    });
});

$(document).ready(function() {
    $('.navbar-toggler').click(function() {
        $('#navbarNav').toggleClass('show');
    });

});
