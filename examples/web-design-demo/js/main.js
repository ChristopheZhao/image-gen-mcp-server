// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get the contact form
    const contactForm = document.getElementById('contact-form');
    
    // Add event listener for form submission
    if (contactForm) {
        contactForm.addEventListener('submit', function(event) {
            // Prevent the default form submission
            event.preventDefault();
            
            // Get form values
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const project = document.getElementById('project').value;
            
            // In a real application, you would send this data to a server
            // For this demo, we'll just show an alert
            alert(`Thank you, ${name}! Your project request has been received. We'll contact you at ${email} shortly.`);
            
            // Reset the form
            contactForm.reset();
        });
    }
    
    // Replace all MCP image links with actual image URLs once they are generated
    // This would require an actual implementation to listen for MCP generation events
    // For demo purposes, we're just showing the concept
    
    // Note: In a real implementation, you might use a message bus or callback system
    // to update the image src attributes once the MCP tool returns the generated image paths
}); 