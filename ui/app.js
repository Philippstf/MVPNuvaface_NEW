// NuvaFace UI JavaScript Application

class NuvaFaceApp {
    constructor() {
        // API URL configuration
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        if (isLocal) {
            this.apiBaseUrl = 'http://localhost:8000';
        } else {
            // Production: Use Cloud Run URL
            // This will be set after Cloud Run deployment
            this.apiBaseUrl = 'https://nuvaface-api-[REPLACE-WITH-HASH]-ew.a.run.app';
        }
        
        this.currentImage = null;
        this.currentMask = null;
        this.selectedArea = null;
        this.selectedProcedure = null;
        this.lastResult = null;
        
        // Canvas references
        this.maskCanvas = null;
        this.overlayCanvas = null;
        this.maskCtx = null;
        this.overlayCtx = null;
        
        // Drawing state
        this.isDrawing = false;
        this.currentTool = 'brush';
        this.brushSize = 20;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupCanvases();
        this.checkApiHealth();
    }

    setupEventListeners() {
        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');

        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));

        // Area selection
        document.querySelectorAll('.area-btn').forEach(btn => {
            btn.addEventListener('click', this.selectArea.bind(this));
        });

        // Mask editor tools
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', this.selectTool.bind(this));
        });

        const brushSizeSlider = document.getElementById('brushSize');
        brushSizeSlider.addEventListener('input', this.updateBrushSize.bind(this));

        document.getElementById('resetMask').addEventListener('click', this.resetMask.bind(this));
        document.getElementById('generateMask').addEventListener('click', this.generateMask.bind(this));

        // Navigation buttons
        document.getElementById('backToArea').addEventListener('click', () => this.showSection('areaSelection'));
        document.getElementById('proceedToSimulation').addEventListener('click', () => this.showSection('simulationSection'));
        document.getElementById('backToMask').addEventListener('click', () => this.showSection('maskEditor'));

        // Simulation controls
        const strengthSlider = document.getElementById('strengthSlider');
        strengthSlider.addEventListener('input', this.updateStrengthValue.bind(this));

        const fixedSeedCheckbox = document.getElementById('fixedSeed');
        fixedSeedCheckbox.addEventListener('change', this.toggleFixedSeed.bind(this));

        document.getElementById('generateButton').addEventListener('click', this.generateSimulation.bind(this));
        document.getElementById('downloadButton').addEventListener('click', this.downloadResult.bind(this));

        // View toggle
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', this.switchView.bind(this));
        });

        // Other buttons
        document.getElementById('startOver').addEventListener('click', this.startOver.bind(this));
    }

    setupCanvases() {
        this.maskCanvas = document.getElementById('maskCanvas');
        this.overlayCanvas = document.getElementById('overlayCanvas');
        this.maskCtx = this.maskCanvas.getContext('2d');
        this.overlayCtx = this.overlayCanvas.getContext('2d');

        // Canvas mouse events
        this.maskCanvas.addEventListener('mousedown', this.startDrawing.bind(this));
        this.maskCanvas.addEventListener('mousemove', this.draw.bind(this));
        this.maskCanvas.addEventListener('mouseup', this.stopDrawing.bind(this));
        this.maskCanvas.addEventListener('mouseout', this.stopDrawing.bind(this));

        // Touch events for mobile
        this.maskCanvas.addEventListener('touchstart', this.handleTouch.bind(this));
        this.maskCanvas.addEventListener('touchmove', this.handleTouch.bind(this));
        this.maskCanvas.addEventListener('touchend', this.stopDrawing.bind(this));
    }

    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const health = await response.json();
            console.log('API Health:', health);
        } catch (error) {
            console.error('API not available:', error);
            this.showError('API server is not available. Please ensure the server is running.');
        }
    }

    // File handling
    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.classList.add('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        e.currentTarget.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }

    async processFile(file) {
        if (!file.type.startsWith('image/')) {
            this.showError('Please select a valid image file.');
            return;
        }

        try {
            this.showLoading('Processing image...', 'Reading and optimizing your photo');
            
            const base64 = await this.fileToBase64(file);
            this.currentImage = base64;
            
            // Show preview
            const img = new Image();
            img.onload = () => {
                this.hideLoading();
                this.showSection('areaSelection');
            };
            img.src = `data:image/${file.type.split('/')[1]};base64,${base64}`;
            
        } catch (error) {
            this.hideLoading();
            this.showError('Failed to process image: ' + error.message);
        }
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // Area selection
    selectArea(e) {
        const area = e.currentTarget.dataset.area;
        const procedure = e.currentTarget.dataset.procedure;
        
        // Update selection
        document.querySelectorAll('.area-btn').forEach(btn => btn.classList.remove('selected'));
        e.currentTarget.classList.add('selected');
        
        this.selectedArea = area;
        this.selectedProcedure = procedure;
        
        // Update volume range based on selected area
        this.updateVolumeRangeForArea(area);
        
        // Auto-proceed to mask editor after a short delay
        setTimeout(() => {
            this.showSection('maskEditor');
            this.generateMask();
        }, 500);
    }

    // Mask editor
    selectTool(e) {
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.currentTool = e.currentTarget.dataset.tool;
    }

    updateBrushSize(e) {
        this.brushSize = parseInt(e.target.value);
        document.getElementById('brushSizeValue').textContent = this.brushSize;
    }

    async generateMask() {
        if (!this.currentImage || !this.selectedArea) return;

        try {
            this.showLoading('Generating mask...', 'Analyzing facial features');

            const response = await fetch(`${this.apiBaseUrl}/segment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: this.currentImage,
                    area: this.selectedArea,
                    feather_px: 3
                })
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Segmentation failed');
            }

            this.currentMask = result.mask_png;
            this.displayMaskOnCanvas();
            
            this.hideLoading();
            
        } catch (error) {
            this.hideLoading();
            this.showError('Failed to generate mask: ' + error.message);
        }
    }

    displayMaskOnCanvas() {
        if (!this.currentImage || !this.currentMask) return;

        const img = new Image();
        img.onload = () => {
            // Resize canvas to image
            this.maskCanvas.width = img.width;
            this.maskCanvas.height = img.height;
            this.overlayCanvas.width = img.width;
            this.overlayCanvas.height = img.height;

            // Draw image
            this.maskCtx.drawImage(img, 0, 0);

            // Draw mask overlay
            const maskImg = new Image();
            maskImg.onload = () => {
                this.overlayCtx.globalAlpha = 0.3;
                this.overlayCtx.fillStyle = 'red';
                this.overlayCtx.globalCompositeOperation = 'source-over';
                
                // Create mask overlay
                const tempCanvas = document.createElement('canvas');
                const tempCtx = tempCanvas.getContext('2d');
                tempCanvas.width = img.width;
                tempCanvas.height = img.height;
                
                tempCtx.drawImage(maskImg, 0, 0, img.width, img.height);
                const imageData = tempCtx.getImageData(0, 0, img.width, img.height);
                
                this.overlayCtx.clearRect(0, 0, img.width, img.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    if (imageData.data[i] > 128) { // White pixels in mask
                        const x = (i / 4) % img.width;
                        const y = Math.floor((i / 4) / img.width);
                        this.overlayCtx.fillRect(x, y, 1, 1);
                    }
                }
            };
            maskImg.src = `data:image/png;base64,${this.currentMask}`;
        };
        img.src = `data:image/jpeg;base64,${this.currentImage}`;
    }

    resetMask() {
        if (this.overlayCtx) {
            this.overlayCtx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);
        }
        this.generateMask();
    }

    // Drawing functions
    startDrawing(e) {
        this.isDrawing = true;
        this.draw(e);
    }

    draw(e) {
        if (!this.isDrawing) return;

        const rect = this.maskCanvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) * (this.maskCanvas.width / rect.width);
        const y = (e.clientY - rect.top) * (this.maskCanvas.height / rect.height);

        this.overlayCtx.globalAlpha = 0.3;
        this.overlayCtx.fillStyle = this.currentTool === 'brush' ? 'red' : 'transparent';
        this.overlayCtx.globalCompositeOperation = this.currentTool === 'brush' ? 'source-over' : 'destination-out';

        this.overlayCtx.beginPath();
        this.overlayCtx.arc(x, y, this.brushSize / 2, 0, 2 * Math.PI);
        this.overlayCtx.fill();
    }

    stopDrawing() {
        this.isDrawing = false;
    }

    handleTouch(e) {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent(e.type === 'touchstart' ? 'mousedown' : 'mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        this.maskCanvas.dispatchEvent(mouseEvent);
    }

    // Simulation
    updateStrengthValue(e) {
        const value = parseFloat(e.target.value).toFixed(1);
        document.getElementById('strengthValue').textContent = value;
    }

    toggleFixedSeed(e) {
        const seedInput = document.getElementById('seedValue');
        seedInput.style.display = e.target.checked ? 'block' : 'none';
    }
    
    updateVolumeRangeForArea(area) {
        const slider = document.getElementById('strengthSlider');
        const volumeInfo = document.querySelector('.volume-info p');
        const labels = document.querySelector('.strength-labels');
        
        switch(area) {
            case 'lips':
                slider.max = 5;
                slider.step = 0.1;
                volumeInfo.innerHTML = '<small><strong>0-1ml:</strong> Subtle hydration & definition • <strong>1-3ml:</strong> Natural enhancement • <strong>3-5ml:</strong> Dramatic, luxurious results</small>';
                labels.innerHTML = '<span>0ml - Natural</span><span>2.5ml - Moderate</span><span>5ml - Maximum</span>';
                break;
                
            case 'chin':
                slider.max = 5;
                slider.step = 0.1;
                volumeInfo.innerHTML = '<small><strong>0-2ml:</strong> Subtle projection • <strong>2-4ml:</strong> Moderate augmentation • <strong>4-5ml:</strong> Strong, confident profile</small>';
                labels.innerHTML = '<span>0ml - Natural</span><span>2.5ml - Enhanced</span><span>5ml - Strong</span>';
                break;
                
            case 'cheeks':
                slider.max = 4;
                slider.step = 0.1;
                volumeInfo.innerHTML = '<small><strong>0-1ml:</strong> Natural freshness • <strong>1-2.5ml:</strong> Attractive contour • <strong>2.5-4ml:</strong> Model-like cheekbones</small>';
                labels.innerHTML = '<span>0ml - Natural</span><span>2ml - Contoured</span><span>4ml - Sculpted</span>';
                break;
                
            case 'forehead':
                slider.max = 1.5;
                slider.step = 0.1;
                volumeInfo.innerHTML = '<small><strong>0-0.5ml:</strong> Subtle smoothing • <strong>0.5-1ml:</strong> Clear reduction • <strong>1-1.5ml:</strong> Maximum smoothness (≈33 Units)</small>';
                labels.innerHTML = '<span>0ml - Natural</span><span>0.7ml - Smooth</span><span>1.5ml - Maximum</span>';
                break;
                
            default:
                slider.max = 5;
                slider.step = 0.1;
        }
        
        // Reset slider value when changing areas
        slider.value = 0;
        this.updateStrengthValue({ target: slider });
    }

    // This function is no longer needed as seed is handled by the backend if necessary
    // toggleFixedSeed(e) { ... }

    async generateSimulation() {
        if (!this.currentImage || !this.selectedArea) return;

        try {
            // The slider value is now directly used as milliliters (ml)
            const volumeMl = parseFloat(document.getElementById('strengthSlider').value);

            // If volume is 0, just show the original image without an API call
            if (volumeMl === 0) {
                this.displaySimulationResult({
                    original_png: this.currentImage,
                    result_png: this.currentImage,
                    qc: { id_similarity: 1.0, ssim_off_mask: 1.0 },
                    warnings: ["Set to 0.0 ml, showing original image."]
                });
                return;
            }

            this.showLoading('Generating simulation...', `Calling Gemini API for ${volumeMl}ml simulation.`);

            const endpoint = this.selectedProcedure === 'filler' ? '/simulate/filler' : '/simulate/botox';
            
            // The request body now sends the 'strength' as the ml value
            const requestBody = {
                image: this.currentImage,
                area: this.selectedArea,
                strength: volumeMl, // 'strength' now means 'ml'
                mask: this.currentMask // Mask is sent for UX display purposes
            };

            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'Simulation failed');
            }

            this.lastResult = result;
            this.displaySimulationResult(result);
            this.hideLoading();
            
        } catch (error) {
            this.hideLoading();
            this.showError('Simulation failed: ' + error.message);
        }
    }

    displaySimulationResult(result) {
        // Display images
        const beforeImg = document.getElementById('beforeImage');
        const afterImg = document.getElementById('afterImage');
        
        beforeImg.src = `data:image/png;base64,${result.original_png}`;
        afterImg.src = `data:image/png;base64,${result.result_png}`;

        // Show quality metrics
        this.displayQualityMetrics(result.qc, result.warnings);

        // Show download button
        document.getElementById('downloadButton').style.display = 'inline-flex';

        // Switch to after view
        this.switchView({ target: { dataset: { view: 'after' }, classList: { add: () => {}, remove: () => {} } } });
    }

    displayQualityMetrics(qc, warnings) {
        const metricsSection = document.getElementById('qualityMetrics');
        metricsSection.style.display = 'block';

        // Identity similarity
        const identityBar = document.getElementById('identityBar');
        const identityValue = document.getElementById('identityValue');
        const idPercentage = Math.round(qc.id_similarity * 100);
        identityBar.style.width = idPercentage + '%';
        identityValue.textContent = idPercentage + '%';

        // SSIM off-mask
        const ssimBar = document.getElementById('ssimBar');
        const ssimValue = document.getElementById('ssimValue');
        const ssimPercentage = Math.round(qc.ssim_off_mask * 100);
        ssimBar.style.width = ssimPercentage + '%';
        ssimValue.textContent = ssimPercentage + '%';

        // Warnings
        const warningsContainer = document.getElementById('warningsContainer');
        if (warningsContainer) {
            warningsContainer.innerHTML = '';
            
            if (warnings && warnings.length > 0) {
                warnings.forEach(warning => {
                    const warningDiv = document.createElement('div');
                    warningDiv.className = 'warning';
                    warningDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${warning}`;
                    warningsContainer.appendChild(warningDiv);
                });
            }
        }
    }

    switchView(e) {
        const view = e.target.dataset.view;
        const beforeImg = document.getElementById('beforeImage');
        const afterImg = document.getElementById('afterImage');
        const splitView = document.getElementById('splitView');

        // Update button states
        document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));
        if (e.target.classList) {
            e.target.classList.add('active');
        }

        // Hide all views
        beforeImg.style.display = 'none';
        afterImg.style.display = 'none';
        splitView.style.display = 'none';

        // Show selected view
        switch (view) {
            case 'before':
                beforeImg.style.display = 'block';
                break;
            case 'after':
                afterImg.style.display = 'block';
                break;
            case 'split':
                splitView.style.display = 'block';
                this.setupSplitView();
                break;
        }
    }

    setupSplitView() {
        if (!this.lastResult) return;

        const splitBefore = document.querySelector('.split-before');
        const splitAfter = document.querySelector('.split-after');

        splitBefore.style.backgroundImage = `url(data:image/png;base64,${this.lastResult.original_png})`;
        splitAfter.style.backgroundImage = `url(data:image/png;base64,${this.lastResult.result_png})`;
    }

    downloadResult() {
        if (!this.lastResult) return;

        const link = document.createElement('a');
        link.href = `data:image/png;base64,${this.lastResult.result_png}`;
        link.download = `nuvaface_${this.selectedArea}_${Date.now()}.png`;
        link.click();
    }

    // Navigation
    showSection(sectionId) {
        // Hide all sections
        document.querySelectorAll('section').forEach(section => {
            section.style.display = 'none';
        });

        // Show target section
        document.getElementById(sectionId).style.display = 'block';

        // Initialize section-specific functionality
        if (sectionId === 'maskEditor' && this.currentImage) {
            setTimeout(() => this.displayMaskOnCanvas(), 100);
        }
    }

    startOver() {
        this.currentImage = null;
        this.currentMask = null;
        this.selectedArea = null;
        this.selectedProcedure = null;
        this.lastResult = null;

        // Reset UI
        document.querySelectorAll('.area-btn').forEach(btn => btn.classList.remove('selected'));
        document.getElementById('qualityMetrics').style.display = 'none';
        document.getElementById('downloadButton').style.display = 'none';
        document.getElementById('strengthSlider').value = 50;
        document.getElementById('strengthValue').textContent = '50';

        this.showSection('uploadSection');
    }

    // Utility functions
    showLoading(message, details) {
        const overlay = document.getElementById('loadingOverlay');
        const messageEl = document.getElementById('loadingMessage');
        const detailsEl = document.getElementById('loadingDetails');

        messageEl.textContent = message;
        detailsEl.textContent = details;
        overlay.style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }

    showError(message) {
        alert('Error: ' + message); // Simple error handling for now
        console.error(message);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NuvaFaceApp();
});