document.addEventListener('click', function(event) {
    // Find closest anchor with data-scroll-to attribute
    const link = event.target.closest('a[data-scroll-to]');

    if (link) {
        event.preventDefault();
        const targetId = link.getAttribute('data-scroll-to');
        const targetElement = document.getElementById(targetId);

        if (targetElement) {
            // Scroll to the element
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    }
});