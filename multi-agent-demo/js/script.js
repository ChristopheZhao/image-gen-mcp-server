document.addEventListener('DOMContentLoaded', function() {
    // Constants and global variables
    const BASE_URL = window.location.origin;
    const STORAGE_KEY = 'mcp_saved_images';
    let currentGeneratedImage = null;
    
    // Elements
    const promptInput = document.getElementById('prompt');
    const styleSelect = document.getElementById('style');
    const generateButton = document.getElementById('generate-button');
    const saveButton = document.getElementById('save-button');
    const generatedImage = document.getElementById('generated-image');
    const imageGallery = document.getElementById('image-gallery');
    const noImagesMessage = document.getElementById('no-images-message');
    
    // Initialize - create placeholder image
    createPlaceholderImage();
    
    // Load any saved images
    loadSavedImages();
    
    // Event listeners
    generateButton.addEventListener('click', generateImage);
    saveButton.addEventListener('click', saveCurrentImage);
    
    // Functions
    function createPlaceholderImage() {
        const canvas = document.createElement('canvas');
        canvas.width = 400;
        canvas.height = 300;
        const ctx = canvas.getContext('2d');
        
        // Draw gradient background
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
        gradient.addColorStop(0, '#f1f7fe');
        gradient.addColorStop(1, '#d5e9fc');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Draw text
        ctx.font = 'bold 24px Arial';
        ctx.fillStyle = '#3498db';
        ctx.textAlign = 'center';
        ctx.fillText('Your image will appear here', canvas.width/2, canvas.height/2);
        
        // Save placeholder
        const placeholderDataUrl = canvas.toDataURL('image/jpeg');
        saveImageToFile(placeholderDataUrl, 'placeholder.jpg');
    }
    
    async function generateImage() {
        // Validate input
        if (!promptInput.value.trim()) {
            alert('Please enter an image description');
            return;
        }
        
        // Update UI to show loading state
        generateButton.disabled = true;
        generateButton.textContent = 'Generating...';
        
        // Create loading animation instead of using loading.gif
        showLoadingAnimation();
        
        try {
            // In a real implementation, this would call an API or service
            // Here we'll simulate the image generation
            const imageData = await simulateImageGeneration(promptInput.value, styleSelect.value);
            
            // Update the image display
            generatedImage.src = imageData;
            currentGeneratedImage = {
                prompt: promptInput.value,
                style: styleSelect.value,
                dataUrl: imageData,
                timestamp: new Date().toISOString()
            };
            
            // Enable save button
            saveButton.disabled = false;
            
        } catch (error) {
            console.error('Error generating image:', error);
            alert('Failed to generate image. Please try again.');
            generatedImage.src = 'data:image/jpeg;base64,' + localStorage.getItem('image_placeholder.jpg');
        } finally {
            // Reset UI
            generateButton.disabled = false;
            generateButton.textContent = 'Generate Image';
        }
    }
    
    function showLoadingAnimation() {
        // Create a canvas for the loading animation
        const canvas = document.createElement('canvas');
        canvas.width = 400;
        canvas.height = 300;
        const ctx = canvas.getContext('2d');
        
        // Draw background
        ctx.fillStyle = '#f1f7fe';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Create loading text
        ctx.font = 'bold 24px Arial';
        ctx.fillStyle = '#3498db';
        ctx.textAlign = 'center';
        ctx.fillText('Generating Image...', canvas.width/2, canvas.height/2 - 50);
        
        // Draw loading spinner
        let dots = 0;
        let angle = 0;
        
        function animate() {
            // Clear spinner area
            ctx.fillStyle = '#f1f7fe';
            ctx.fillRect(canvas.width/2 - 100, canvas.height/2, 200, 60);
            
            // Draw dots
            ctx.fillStyle = '#3498db';
            let dotText = 'Please wait';
            for (let i = 0; i < dots; i++) {
                dotText += '.';
            }
            ctx.fillText(dotText, canvas.width/2, canvas.height/2 + 30);
            
            // Draw spinner
            ctx.save();
            ctx.translate(canvas.width/2, canvas.height/2 - 10);
            ctx.rotate(angle);
            
            for (let i = 0; i < 8; i++) {
                ctx.rotate(Math.PI / 4);
                ctx.fillStyle = `rgba(52, 152, 219, ${0.3 + 0.7 * (i / 7)})`;
                ctx.fillRect(-2, -15, 4, 10);
            }
            
            ctx.restore();
            
            // Update state
            dots = (dots + 1) % 4;
            angle += 0.1;
            
            // Set image
            generatedImage.src = canvas.toDataURL('image/jpeg');
            
            // Continue animation if still generating
            if (generateButton.disabled) {
                requestAnimationFrame(animate);
            }
        }
        
        // Start animation
        animate();
    }
    
    function saveCurrentImage() {
        if (!generatedImage.src) return;
        
        // Generate a unique filename based on timestamp
        const timestamp = new Date().getTime();
        const imageName = `mcp-image-${timestamp}`;
        
        // Create a download link to save the image
        const link = document.createElement('a');
        link.href = generatedImage.src;
        link.download = imageName + '.jpg';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Also store reference in localStorage for the gallery
        const savedImages = getSavedImages();
        savedImages.push({
            name: imageName,
            src: generatedImage.src,
            timestamp: new Date().toISOString()
        });
        
        localStorage.setItem(STORAGE_KEY, JSON.stringify(savedImages));
        
        // Refresh gallery
        loadSavedImages();
        
        alert('Image saved successfully!');
    }
    
    function saveImageToFile(dataUrl, filename) {
        // In a real implementation, this would save to server or download
        // Here we're simulating by storing in local storage
        
        // Create an invisible download link
        const link = document.createElement('a');
        link.href = dataUrl;
        link.download = filename;
        
        // Append to the body, click it, then remove it
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // For demo purposes, we'll also store the data URL in localStorage
        // (not recommended for production due to size limits)
        localStorage.setItem(`image_${filename}`, dataUrl);
    }
    
    function loadSavedImages() {
        const galleryElement = document.getElementById('image-gallery');
        const savedImages = getSavedImages();
        
        // Only attempt to update if we have a gallery element and new images
        if (!galleryElement || savedImages.length === 0) return;
        
        // Add each saved image to gallery
        savedImages.forEach(imageInfo => {
            // Check if this image is already in the gallery
            const existingImage = document.querySelector(`[data-image-id="${imageInfo.name}"]`);
            if (existingImage) return; // Skip if already displayed
            
            const imgElement = document.createElement('img');
            imgElement.src = imageInfo.src;
            imgElement.alt = imageInfo.name;
            imgElement.dataset.imageId = imageInfo.name;
            
            galleryElement.appendChild(imgElement);
        });
    }
    
    function getSavedImages() {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : [];
    }
    
    // Simulation function (replace with actual API call in production)
    async function simulateImageGeneration(prompt, style) {
        return new Promise((resolve, reject) => {
            // Simulate API delay
            setTimeout(() => {
                // For demo purposes, we'll use some predefined images based on style
                let imageUrl;
                
                switch(style) {
                    case 'riman':
                        imageUrl = 'https://via.placeholder.com/600x400/3498db/ffffff?text=Anime+Style+Image';
                        break;
                    case 'xieshi':
                        imageUrl = 'https://via.placeholder.com/600x400/2ecc71/ffffff?text=Realistic+Style+Image';
                        break;
                    case 'youhua':
                        imageUrl = 'https://via.placeholder.com/600x400/e74c3c/ffffff?text=Oil+Painting+Style+Image';
                        break;
                    default:
                        imageUrl = 'https://via.placeholder.com/600x400/f1c40f/ffffff?text=Generated+Image';
                }
                
                // In a real implementation, we'd convert the API response to a data URL
                // Here we're simulating that by creating an image and drawing it on canvas
                const img = new Image();
                img.crossOrigin = 'Anonymous';
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');
                    
                    // Draw image
                    ctx.drawImage(img, 0, 0);
                    
                    // Add the prompt text to the image
                    ctx.font = '20px Arial';
                    ctx.fillStyle = 'white';
                    ctx.textAlign = 'center';
                    
                    // Draw text with background
                    const text = prompt.length > 40 ? prompt.substring(0, 37) + '...' : prompt;
                    const textWidth = ctx.measureText(text).width;
                    
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.fillRect(canvas.width/2 - textWidth/2 - 10, canvas.height - 50, textWidth + 20, 40);
                    
                    ctx.fillStyle = 'white';
                    ctx.fillText(text, canvas.width/2, canvas.height - 25);
                    
                    // Convert to data URL and resolve
                    resolve(canvas.toDataURL('image/jpeg'));
                };
                
                img.onerror = function() {
                    reject(new Error('Failed to load image'));
                };
                
                img.src = imageUrl;
            }, 2000); // Simulate 2-second delay
        });
    }
}); 