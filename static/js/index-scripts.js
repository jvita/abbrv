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

// // Function to handle downloading systems
// function handleDownloadSystems() {
//     // event.preventDefault(); // Prevent default anchor behavior

//     // Fetch the JSON file
//     fetch('./static/data/systems/available_systems.json')
//     .then(response => {
//         if (!response.ok) {
//         throw new Error(`HTTP error! Status: ${response.status}`);
//         }
//         return response.json();
//     })
//     .then(data => {
//         displayDownloadableSystems(data.systems);
//     })
//     .catch(error => console.error('Error loading JSON:', error));
// }

// // Function to display the list of downloadable systems in the modal
// function displayDownloadableSystems(availableSystems) {
//     const downloadableList = document.getElementById('downloadableList');

//     // Clear any existing items
//     downloadableList.innerHTML = '';

//     // Loop through the systems and create list items
//     availableSystems.forEach(system => {
//         const listItem = document.createElement('li');
//         listItem.classList.add('list-group-item', 'list-group-item-action');
//         listItem.innerText = system;

//         // Add click event listener to each item
//         listItem.addEventListener('click', function () {
//             // Load the selected system's data
//             loadSystemData(system);
//             // Close the modal after selection
//             const modal = bootstrap.Modal.getInstance(document.getElementById('downloadSystemsModal'));
//             modal.hide();
//         });

//         downloadableList.appendChild(listItem)
//     });

//     // Show the modal
//     const modal = new bootstrap.Modal(document.getElementById('downloadSystemsModal'));
//     modal.show();
// }

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

// Example usage in the export button event listener
document.getElementById('exportSystem').addEventListener('click', async function() {
    await saveSystemToServer(selectedSystem, systems[selectedSystem])
});

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
        data.systems.forEach(systemKey => {
            const listItem = document.createElement('li');
            listItem.classList.add('list-group-item', 'list-group-item-action');
            // listItem.innerText = system;
            listItem.innerHTML = `<a class="dropdown-item" href="#">${systemKey}</a>`; // Use the key as the link text

            // Add a click event listener to the anchor element
            listItem.querySelector('a').addEventListener('click', async function (event) {

            // // Add click event listener to each item
            // listItem.addEventListener('click', function () {
                if (!(systemKey in systems)) {
                    // Load the selected system's data
                    await loadSystemData(systemKey);
                }

                // event.preventDefault(); // Prevent default anchor behavior
                // selectedSystem = systemKey; // Use the key as the selected system
                // localStorage.setItem('selectedSystem', selectedSystem);

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

    // // Loop through the dictionary keys
    // for (const systemKey in systems) {
    //     if (systems.hasOwnProperty(systemKey)) {
    //         const listItem = document.createElement('li'); // Create a list item
    //         listItem.innerHTML = `<a class="dropdown-item" href="#">${systemKey}</a>`; // Use the key as the link text

    //         // Add a click event listener to the anchor element
    //         listItem.querySelector('a').addEventListener('click', function (event) {
    //             event.preventDefault(); // Prevent default anchor behavior

    //             // Set the currently selected system
    //             selectedSystem = systemKey; // Use the key as the selected system

    //             // Store the selected system in local storage or a global variable
    //             localStorage.setItem('selectedSystem', selectedSystem);
    //             navbarElement.textContent = `system: ${selectedSystem ? selectedSystem : 'select'}`;

    //             // Refresh the page
    //             location.reload(); // This will reload the current page
    //         });

    //         systemsListContainer.appendChild(listItem); // Append the item to the systems list
    //     }
    // }
}

async function loadSystemsAndUpdateDropdown() {
    addSystemsToDropdown();     // Then run addSystemsToDropdown after

    const divider = document.getElementById("systemsDivider");

    divider.style.display = "block"
    // if (Object.keys(systems).length > 0) {
    //     divider.style.display = "block"; // Show divider if systems exist
    // } else {
    //     divider.style.display = "none"; // Hide divider if no systems
    // }

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
