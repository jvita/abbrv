let rules = selectedSystem ? systems[selectedSystem]['rules'] : []

// Function to fetch and render rules
function renderRules() {
    const rulesList = document.getElementById('rulesList');
    rulesList.innerHTML = ''; // Clear the existing list

    // Render each rule
    rules.forEach((rule, index) => {
        const ruleItem = document.createElement('li');
        ruleItem.className = 'list-group-item d-flex justify-content-between align-items-center';

        // Create a div for the rule content (left side)
        const ruleContent = document.createElement('div');
        ruleContent.innerHTML = `
            <strong>Name:</strong> ${rule.name} <br>
        `;

        // Create a span for the regex, ensuring it's safe
        const regexSpan = document.createElement('span');
        regexSpan.innerHTML = `<strong>Pattern:</strong> `;
        const regexContent = document.createElement('span');
        regexContent.textContent = rule.regex; // Ensure raw text for regex

        // Append the regex content to the regex span
        regexSpan.appendChild(regexContent);

        // Append the regex span to the ruleContent div
        ruleContent.appendChild(regexSpan);

        // Add a line break and the Replacement field
        const replacementSpan = document.createElement('div');
        replacementSpan.innerHTML = `<strong>Replacement:</strong> ${rule.replacement}`;
        ruleContent.appendChild(replacementSpan);

        // Create the move up button
        const moveUpButton = document.createElement('button');
        moveUpButton.className = 'btn btn-primary btn-sm me-2';
        moveUpButton.innerHTML = '<i class="bi bi-arrow-up"></i>';
        moveUpButton.onclick = () => moveRuleUp(index);

        // Create the move down button
        const moveDownButton = document.createElement('button');
        moveDownButton.className = 'btn btn-primary btn-sm me-2';
        moveDownButton.innerHTML = '<i class="bi bi-arrow-down"></i>';
        moveDownButton.onclick = () => moveRuleDown(index);

        // Create the delete button (right side)
        const deleteButton = document.createElement('button');
        deleteButton.className = 'btn btn-danger btn-sm';
        deleteButton.textContent = 'Delete';
        deleteButton.onclick = () => deleteRule(index); // Attach delete function

        // Append the content and buttons to the rule item
        const buttonContainer = document.createElement('div');
        buttonContainer.appendChild(moveUpButton);
        buttonContainer.appendChild(moveDownButton);
        buttonContainer.appendChild(deleteButton);

        ruleItem.appendChild(ruleContent);
        ruleItem.appendChild(buttonContainer);

        // Append the rule item to the list
        rulesList.appendChild(ruleItem);
    });
}

// Function to add a new rule
document.getElementById('addRuleForm').addEventListener('submit', function(e) {
    e.preventDefault(); // Prevent form submission

    // Get input values
    const regexInput = document.getElementById('regexInput').value;
    const replacementText = document.getElementById('replacementText').value;
    const ruleName = document.getElementById('ruleName').value;

    // Create a new rule object and add it to the list
    const newRule = { regex: regexInput, replacement: replacementText, name: ruleName };
    rules.push(newRule);

    // Clear the form
    document.getElementById('addRuleForm').reset();
    saveSystems();
    renderRules(); // Ensure the updated list is displayed
});

// Function to delete a rule
function deleteRule(index) {
    rules.splice(index, 1); // Remove the rule from the array
    saveSystems();
    renderRules(); // Ensure the updated list is displayed after deletion
}

// Function to move a rule up
function moveRuleUp(index) {
    if (index > 0) {
        const temp = rules[index];
        rules[index] = rules[index - 1];
        rules[index - 1] = temp;
        saveSystems();
        renderRules();
    }
}

// Function to move a rule down
function moveRuleDown(index) {
    if (index < rules.length - 1) {
        const temp = rules[index];
        rules[index] = rules[index + 1];
        rules[index + 1] = temp;
        saveSystems();
        renderRules();
    }
}

// On page load, load existing rules
window.onload = function() {
    renderRules();
};