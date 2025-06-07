document.addEventListener('DOMContentLoaded', function () {
    const imageUploadInput = document.getElementById('imageUpload');
    const uploadedImageDisplay = document.getElementById('uploadedImage');
    const originalImageSection = document.getElementById('originalImageSection');
    const marqueeTextInput = document.getElementById('marqueeText');
    const submitButton = document.getElementById('submitButton');
    const processedImageDisplay = document.getElementById('processedImage');
    const processedImageSection = document.getElementById('processedImageSection');
    const downloadLink = document.getElementById('downloadLink');
    const loader = document.getElementById('loader');

    const canvas = document.getElementById('selectionCanvas');
    const ctx = canvas.getContext('2d');

    let currentUploadedFilenameForServer = null; // Filename to be sent to server
    let selectionRect = null;
    let isSelecting = false;
    let startX_canvas, startY_canvas; // Renamed to avoid conflict

    // --- Image Upload Logic ---
    imageUploadInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (!file) { return; }

        // 1. Local Preview using FileReader
        const reader = new FileReader();
        reader.onload = function(e) {
            uploadedImageDisplay.onload = () => {
                canvas.width = uploadedImageDisplay.clientWidth;
                canvas.height = uploadedImageDisplay.clientHeight;
                console.log(`Canvas dimensions set for local preview: ${canvas.width}x${canvas.height}`);
                originalImageSection.style.display = 'block';
            };
            uploadedImageDisplay.src = e.target.result; // Show local preview
        }
        reader.readAsDataURL(file);

        // 2. Send image to backend to store in /tmp
        const formData = new FormData();
        formData.append('imageFile', file);
        loader.style.display = 'block';
        // Keep originalImageSection visible if preview is shown, or hide then show after server confirmation
        // For now, local preview keeps it visible.
        processedImageSection.style.display = 'none'; // Hide previous result
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        selectionRect = null;
        currentUploadedFilenameForServer = null; // Reset server filename status

        try {
            const response = await fetch('/upload_image/', { method: 'POST', body: formData });
            if (response.ok) {
                const result = await response.json();
                console.log("Backend received image:", result);
                currentUploadedFilenameForServer = result.filename; // Store filename for server processing
                // No need to set uploadedImageDisplay.src from server response here
                // as local preview is already shown.
            } else {
                const errorResult = await response.json();
                alert("Image upload to server failed: " + (errorResult.message || response.statusText));
                originalImageSection.style.display = 'none'; // Hide preview if server upload failed
                uploadedImageDisplay.removeAttribute('src'); // Clear local preview
            }
        } catch (error) {
            alert("An error occurred during server upload: " + error.message);
            originalImageSection.style.display = 'none';
            uploadedImageDisplay.removeAttribute('src'); // Clear local preview
        } finally {
            loader.style.display = 'none';
        }
    });

    // --- Canvas Selection Logic ---
    canvas.addEventListener('mousedown', function(e) {
        // Check if src is a data URL (local preview) or if it was ever set
        if (!uploadedImageDisplay.src || !uploadedImageDisplay.src.startsWith('data:image')) {
            console.log("No image loaded or preview available for selection.");
            return;
        }
        isSelecting = true;
        startX_canvas = e.offsetX;
        startY_canvas = e.offsetY;
    });

    canvas.addEventListener('mousemove', function(e) {
        if (!isSelecting) return;
        const currentX = e.offsetX;
        const currentY = e.offsetY;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.rect(startX_canvas, startY_canvas, currentX - startX_canvas, currentY - startY_canvas);
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    canvas.addEventListener('mouseup', function(e) {
        if (!isSelecting) return;
        isSelecting = false;
        const endX_canvas = e.offsetX;
        const endY_canvas = e.offsetY;

        const finalStartX_canvas = Math.min(startX_canvas, endX_canvas);
        const finalStartY_canvas = Math.min(startY_canvas, endY_canvas);
        const finalEndX_canvas = Math.max(startX_canvas, endX_canvas);
        const finalEndY_canvas = Math.max(startY_canvas, endY_canvas);

        const displayWidth = uploadedImageDisplay.clientWidth;
        const displayHeight = uploadedImageDisplay.clientHeight;
        const naturalWidth = uploadedImageDisplay.naturalWidth;
        const naturalHeight = uploadedImageDisplay.naturalHeight;

        const scaleX = naturalWidth / displayWidth;
        const scaleY = naturalHeight / displayHeight;

        selectionRect = {
            startX: Math.round(finalStartX_canvas * scaleX),
            startY: Math.round(finalStartY_canvas * scaleY),
            endX: Math.round(finalEndX_canvas * scaleX),
            endY: Math.round(finalEndY_canvas * scaleY)
        };

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.rect(finalStartX_canvas, finalStartY_canvas, finalEndX_canvas - finalStartX_canvas, finalEndY_canvas - finalStartY_canvas);
        ctx.strokeStyle = 'blue';
        ctx.lineWidth = 2;
        ctx.stroke();

        if (selectionRect.endX - selectionRect.startX <= 1 || selectionRect.endY - selectionRect.startY <= 1) {
            selectionRect = null;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            alert("Selection area is too small. Please draw a larger rectangle.");
        }
        console.log("Scaled selectionRect:", selectionRect);
    });

    window.addEventListener('resize', () => {
        if (uploadedImageDisplay.src && uploadedImageDisplay.src.startsWith('data:image') && originalImageSection.style.display !== 'none') {
            canvas.width = uploadedImageDisplay.clientWidth;
            canvas.height = uploadedImageDisplay.clientHeight;
            // Clear selection on resize; user needs to re-select.
            // This simplifies handling redrawing on a dynamically changing canvas/image ratio.
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            selectionRect = null;
            console.log("Window resized. Canvas cleared. Please re-select marquee area if selection was active.");
        }
    });

    // --- Submit Button Logic ---
    submitButton.addEventListener('click', async function() {
        if (!currentUploadedFilenameForServer) {
            alert("Please upload an image and ensure it's confirmed by the server.");
            return;
        }
        if (!selectionRect) {
            alert("Please select a marquee area on the image.");
            return;
        }
        const text = marqueeTextInput.value.trim();
        if (!text) {
            alert("Please enter the text for the marquee.");
            return;
        }

        const payload = {
            filename: currentUploadedFilenameForServer,
            selection: selectionRect,
            text: text,
            font_size: 40 // Or get from an input field if you add one
        };

        console.log("Processing with payload:", payload);
        loader.style.display = 'block';
        processedImageSection.style.display = 'none';

        try {
            const response = await fetch('/process_image/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const imageBlob = await response.blob();
                const objectURL = URL.createObjectURL(imageBlob);

                processedImageDisplay.src = objectURL;
                downloadLink.href = objectURL;

                // Try to get filename from Content-Disposition header if server sends it
                const disposition = response.headers.get('content-disposition');
                let downloadFilename = "processed_marquee.png"; // Default
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) {
                        downloadFilename = matches[1].replace(/['"]/g, '');
                    }
                }
                downloadLink.download = downloadFilename;

                processedImageSection.style.display = 'block';
                downloadLink.style.display = 'inline-block';
                console.log("Processed image displayed.");

            } else {
                // Try to parse error as JSON, otherwise use statusText
                let errorMsg = response.statusText;
                try {
                    const errorResult = await response.json();
                    errorMsg = errorResult.detail || errorMsg;
                } catch (e) {
                    // Not a JSON error response, stick with statusText
                }
                console.error("Processing failed:", errorMsg);
                alert("Image processing failed: " + errorMsg);
            }
        } catch (error) {
            console.error("Error during processing:", error);
            alert("An error occurred during processing: " + error.message);
        } finally {
            loader.style.display = 'none';
        }
    });
});
