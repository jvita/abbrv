const systemsJson = localStorage.getItem('systems');
let systems = systemsJson ? JSON.parse(systemsJson) : {}

const selectedSystemJson = localStorage.getItem('selectedSystem')
let selectedSystem = selectedSystemJson ? selectedSystemJson : null

const navbarElement = document.getElementById('navbarDropdown');
navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

// Initialize Bootstrap tooltips
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
});

document.getElementById('downloadSystem').addEventListener('click', handleDownloadSystems);

function saveSystems() {
    // TODO: this is inefficient; should only update current system
    // TODO: there can be an issue when you make an edit in one page,
    // then make another edit in a second page without refreshing first.
    // this will overwrite the first set of changes
    const systemsJson = JSON.stringify(systems);
    localStorage.setItem('systems', systemsJson);

    const systemsJson2 = localStorage.getItem('systems');

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

// Function to handle downloading systems
function handleDownloadSystems() {
    event.preventDefault(); // Prevent default anchor behavior

    // Fetch the JSON file
    fetch('./static/data/systems/available_systems.json')
    .then(response => {
        if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        displayDownloadableSystems(data.systems);
    })
    .catch(error => console.error('Error loading JSON:', error));
}

// Function to display the list of downloadable systems in the modal
function displayDownloadableSystems(availableSystems) {
    const downloadableList = document.getElementById('downloadableList');

    // Clear any existing items
    downloadableList.innerHTML = '';

    // Loop through the systems and create list items
    availableSystems.forEach(system => {
        const listItem = document.createElement('li');
        listItem.classList.add('list-group-item', 'list-group-item-action');
        listItem.innerText = system;

        // Add click event listener to each item
        listItem.addEventListener('click', function () {
            // Load the selected system's data
            loadSystemData(system);
            // Close the modal after selection
            const modal = bootstrap.Modal.getInstance(document.getElementById('downloadSystemsModal'));
            modal.hide();
        });

        downloadableList.appendChild(listItem)
    });

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('downloadSystemsModal'));
    modal.show();
}

// Function to load the selected system's data
async function loadSystemData(systemName) {
    try {
        // Fetch the ZIP file from the server
        const response = await fetch(`./static/data/systems/${systemName}.zip`);
        const blob = await response.blob();

        // Create a new instance of JSZip
        const zip = await JSZip.loadAsync(blob);

        // Initialize an empty object to store the system data
        const systemData = {};

        // Iterate over each file in the ZIP
        for (const filename of Object.keys(zip.files)) {
            const file = zip.files[filename];
            const fileContent = await file.async('text');
            const parsedData = JSON.parse(fileContent);

            // Store data based on the filename
            if (filename.includes('glyphs')) {
                systemData['glyphs'] = parsedData;
            } else if (filename.includes('phrases')) {
                systemData['phrases'] = parsedData;
            } else if (filename.includes('modes')) {
                systemData['modes'] = parsedData;
            } else if (filename.includes('rules')) {
                systemData['rules'] = parsedData;
            }
        }

        // Store the system data
        systems[systemName] = systemData;

        selectedSystem = systemName;
        localStorage.setItem('selectedSystem', selectedSystem);

        const systemsJson = JSON.stringify(systems);
        localStorage.setItem('systems', systemsJson);

        location.reload(); // This will reload the current page
    } catch (error) {
        console.error('Error loading system data:', error);
    }
}

// Import System
document.getElementById('importSystem').addEventListener('click', function() {
    // Logic to handle file upload
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.zip';
    fileInput.onchange = function(event) {
        const file = event.target.files[0];
        if (file) {
            // Logic to extract and handle the zip file
            console.log("Importing file:", file.name);
        }
    };
    fileInput.click();
});

// Save As Function
async function saveAs(data) {
    // Create a new instance of JSZip
    const zip = new JSZip();

    // Convert the JavaScript object to a JSON string
    const jsonString = JSON.stringify(data, null, 2); // Pretty-print JSON

    // Add the JSON string to the zip file
    zip.file('data.json', jsonString);

    // Generate the zip file asynchronously
    const content = await zip.generateAsync({ type: "blob" });

    // Check if showSaveFilePicker is supported
    if ('showSaveFilePicker' in window) {
        try {
            // Use the File System Access API
            const options = {
                suggestedName: (selectedSystem ? selectedSystem : 'system') + '.zip', // Default name for the file
                types: [{
                    description: 'ZIP files',
                    accept: {
                        'application/zip': ['.zip'],
                    },
                }],
            };

            // Show the save file dialog
            const fileHandle = await window.showSaveFilePicker(options);

            // Create a writable stream
            const writableStream = await fileHandle.createWritable();

            // Write the blob data to the file
            await writableStream.write(content);

            // Close the writable stream
            await writableStream.close();
        } catch (err) {
            if (err.name === 'AbortError') {
                console.log('User canceled the save operation')
            } else {
                console.error('Error during save:', err)
            }
        }
    } else {

        let filename = prompt("Enter the name of the new system:", "new_system_name");

        // If the user clicks "Cancel" or provides an empty input, exit the function
        if (!filename) {
            return; // Exit without downloading
        }

        // Fallback method using a temporary anchor element
        const link = document.createElement('a');
        link.href = URL.createObjectURL(content);
        link.download = filename + '.zip'; // Specify the file name with .zip extension

        // Append to the body
        document.body.appendChild(link);
        link.click(); // Trigger the download
        document.body.removeChild(link); // Clean up the DOM
    }
}

// Example usage in the export button event listener
document.getElementById('exportSystem').addEventListener('click', async function() {
    // Example JavaScript object to be exported
    const myObject = {
        glyphs: {},
        phrases: {},
        modes: {},
        rules: {},
    };

    // Call the saveAs function with the object and filename
    await saveAs(myObject);
});

function addSystemsToDropdown() {
    // Get the systems list container
    const systemsListContainer = document.getElementById('systemsList');

    // Clear any existing items
    systemsListContainer.innerHTML = '';

    const navbarElement = document.getElementById('navbarDropdown');

    // Loop through the dictionary keys
    for (const systemKey in systems) {
        if (systems.hasOwnProperty(systemKey)) {
            const listItem = document.createElement('li'); // Create a list item
            listItem.innerHTML = `<a class="dropdown-item" href="#">${systemKey}</a>`; // Use the key as the link text

            // Add a click event listener to the anchor element
            listItem.querySelector('a').addEventListener('click', function (event) {
                event.preventDefault(); // Prevent default anchor behavior

                // Set the currently selected system
                selectedSystem = systemKey; // Use the key as the selected system

                // Store the selected system in local storage or a global variable
                localStorage.setItem('selectedSystem', selectedSystem);

                localStorage.setItem('selectedSystem', selectedSystem);
                navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

                // Refresh the page
                location.reload(); // This will reload the current page
            });

            systemsListContainer.appendChild(listItem); // Append the item to the systems list
        }
    }
}

async function loadSystemsAndUpdateDropdown() {
    addSystemsToDropdown();     // Then run addSystemsToDropdown after

    const divider = document.getElementById("systemsDivider");

    console.log(Object.keys(systems).length)

    if (Object.keys(systems).length > 0) {
        divider.style.display = "block"; // Show divider if systems exist
    } else {
        divider.style.display = "none"; // Hide divider if no systems
    }

}

// Call the fetch function on page load
document.addEventListener('DOMContentLoaded', function () {
    loadSystemsAndUpdateDropdown();
});

$(document).ready(function() {
    $('.navbar-toggler').click(function() {
        $('#navbarNav').toggleClass('show');
    });

});
