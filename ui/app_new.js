// NuvaFace Modernized UI Application
// WICHTIG: API-Calls bleiben unverändert, nur UI/UX wird modernisiert

class NuvaFaceApp {
    constructor() {
        // API Configuration (UNCHANGED)
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        if (isLocal) {
            this.apiBaseUrl = 'http://localhost:8000';
        } else {
            // Production: Use Cloud Run URL
            this.apiBaseUrl = 'https://rmgpgab-nuvaface-api-europe-west1-philippstf-mvpn-hapllrcw7a-uc.a.run.app';
        }
        
        // State management
        this.currentImage = null;
        this.currentImageBase64 = null;
        this.selectedArea = null;
        this.currentMask = null;
        this.lastResult = null;
        this.generationHistory = [];
        this.maxHistoryItems = 12; // Max items in history
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkApiHealth();
        this.showSection('landingSection');
    }

    setupEventListeners() {
        // Area selection hotspots
        document.querySelectorAll('.hotspot').forEach(spot => {
            spot.addEventListener('click', this.selectArea.bind(this));
            spot.addEventListener('mouseenter', this.showAreaInfo.bind(this));
            spot.addEventListener('mouseleave', this.hideAreaInfo.bind(this));
        });

        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
            uploadArea.addEventListener('drop', this.handleDrop.bind(this));
            fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        }

        // Volume slider
        const volumeSlider = document.getElementById('volumeSlider');
        if (volumeSlider) {
            volumeSlider.addEventListener('input', this.updateVolumeDisplay.bind(this));
        }

        // Proceed to upload button
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', () => this.showSection('uploadSection'));
        }
    }

    // Section Navigation
    showSection(sectionId) {
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Update displayed area if on upload section
            if (sectionId === 'uploadSection' && this.selectedArea) {
                const display = document.getElementById('selectedAreaDisplay');
                if (display) {
                    const areaNames = {
                        'lips': 'Lippen (Filler)',
                        'chin': 'Kinn (Filler)',
                        'cheeks': 'Wangen (Filler)',
                        'forehead': 'Stirn (Botox)'
                    };
                    display.textContent = areaNames[this.selectedArea] || this.selectedArea;
                }
            }
        }
    }

    // Area Selection
    selectArea(e) {
        const area = e.currentTarget.dataset.area;
        
        // Update visual selection
        document.querySelectorAll('.hotspot').forEach(spot => {
            spot.classList.remove('selected');
        });
        e.currentTarget.classList.add('selected');
        
        this.selectedArea = area;
        
        // Enable proceed button
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.disabled = false;
        }
        
        // Update info display
        this.showAreaInfo(e);
    }

    showAreaInfo(e) {
        const area = e.currentTarget.dataset.area;
        const infoBox = document.getElementById('areaInfo');
        
        if (infoBox) {
            const descriptions = {
                'lips': 'Lippenvolumen mit Hyaluronsäure (0.5-4.0 ml)',
                'chin': 'Kinnkorrektur mit Hyaluronsäure (1.0-4.0 ml)',
                'cheeks': 'Wangenvolumen mit Hyaluronsäure (1.0-4.0 ml)',
                'forehead': 'Stirnfalten-Behandlung mit Botox (10-40 Units)'
            };
            infoBox.innerHTML = `<strong>${descriptions[area] || area}</strong>`;
        }
    }

    hideAreaInfo() {
        const infoBox = document.getElementById('areaInfo');
        if (infoBox && !this.selectedArea) {
            infoBox.innerHTML = '<p>Bewegen Sie die Maus über einen Bereich, um mehr zu erfahren</p>';
        }
    }

    // File Handling
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
            this.showError('Bitte wählen Sie eine Bilddatei aus.');
            return;
        }

        const reader = new FileReader();
        reader.onload = async (e) => {
            this.currentImageBase64 = e.target.result;
            this.currentImage = new Image();
            this.currentImage.src = this.currentImageBase64;
            
            // Show preview
            const uploadArea = document.getElementById('uploadArea');
            const uploadPreview = document.getElementById('uploadPreview');
            const previewImage = document.getElementById('previewImage');
            
            if (uploadArea && uploadPreview && previewImage) {
                uploadArea.style.display = 'none';
                uploadPreview.style.display = 'block';
                previewImage.src = this.currentImageBase64;
            }
            
            // ROUTING FIX: Only go to segmentation for lips
            if (this.selectedArea === 'lips') {
                // For lips, go to segmentation first
                setTimeout(() => {
                    this.showSection('segmentSection');
                    this.showSegmentationPreview();
                }, 500);
            } else {
                // For all other areas, go directly to result
                setTimeout(() => {
                    this.showSection('resultSection');
                    this.setupResultView();
                }, 500);
            }
        };
        reader.readAsDataURL(file);
    }

    changeImage() {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.click();
        }
    }

    // Simplified Segmentation Preview (Lips Only)
    async showSegmentationPreview() {
        if (this.selectedArea !== 'lips') return;
        
        try {
            // Call segmentation API
            const response = await fetch(`${this.apiBaseUrl}/segment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Request-ID': this.generateRequestId()
                },
                body: JSON.stringify({
                    image: this.currentImageBase64.split(',')[1],
                    area: 'lips'
                })
            });

            if (!response.ok) {
                throw new Error('Segmentierung fehlgeschlagen');
            }

            const result = await response.json();
            
            // Display the mask
            const canvas = document.getElementById('segmentCanvas');
            const overlay = document.getElementById('segmentOverlay');
            
            if (canvas && overlay && this.currentImage) {
                const ctx = canvas.getContext('2d');
                const overlayCtx = overlay.getContext('2d');
                
                // Set canvas size
                canvas.width = this.currentImage.width;
                canvas.height = this.currentImage.height;
                overlay.width = this.currentImage.width;
                overlay.height = this.currentImage.height;
                
                // Draw original image
                ctx.drawImage(this.currentImage, 0, 0);
                
                // Draw mask overlay
                if (result.mask_png) {
                    const maskImg = new Image();
                    maskImg.onload = () => {
                        overlayCtx.globalAlpha = 0.5;
                        overlayCtx.fillStyle = '#ff0000';
                        overlayCtx.globalCompositeOperation = 'source-over';
                        
                        // Create red overlay where mask is white
                        overlayCtx.drawImage(maskImg, 0, 0);
                        overlayCtx.globalCompositeOperation = 'source-in';
                        overlayCtx.fillRect(0, 0, canvas.width, canvas.height);
                    };
                    maskImg.src = 'data:image/png;base64,' + result.mask_png;
                }
                
                this.currentMask = result.mask_png;
            }
        } catch (error) {
            console.error('Segmentation error:', error);
            // Continue anyway
        }
    }

    proceedToResult() {
        this.showSection('resultSection');
        this.setupResultView();
    }

    setupResultView() {
        // Display the original image
        const beforeImage = document.getElementById('beforeImage');
        if (beforeImage && this.currentImageBase64) {
            beforeImage.src = this.currentImageBase64;
        }
        
        // Clear after image
        const afterImage = document.getElementById('afterImage');
        if (afterImage) {
            afterImage.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect width="400" height="400" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999" font-size="16"%3EKlicken Sie auf Generieren%3C/text%3E%3C/svg%3E';
        }
        
        // Set initial volume based on area
        this.updateVolumeDisplay();
    }

    updateVolumeDisplay() {
        const slider = document.getElementById('volumeSlider');
        const display = document.getElementById('volumeValue');
        
        if (slider && display) {
            const value = parseFloat(slider.value);
            display.textContent = value.toFixed(1) + ' ml';
        }
    }

    // Generate Simulation
    async generateSimulation() {
        const generateBtn = document.getElementById('generateBtn');
        const loader = document.getElementById('loader');
        const volumeSlider = document.getElementById('volumeSlider');
        
        if (!this.currentImageBase64 || !this.selectedArea) {
            this.showError('Bitte wählen Sie zuerst ein Bild und einen Bereich aus.');
            return;
        }
        
        // Show loading state
        if (generateBtn) generateBtn.style.display = 'none';
        if (loader) loader.style.display = 'block';
        
        try {
            const volume = parseFloat(volumeSlider.value);
            
            // API Call (UNCHANGED from original)
            const requestBody = {
                image: this.currentImageBase64.split(',')[1],
                area: this.selectedArea,
                strength: volume // API expects 'strength' field with ml value
            };
            
            // Add unique request ID for anti-cache
            const requestId = this.generateRequestId();
            
            const response = await fetch(`${this.apiBaseUrl}/simulate/filler`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Request-ID': requestId,
                    'Cache-Control': 'no-cache'
                },
                body: JSON.stringify(requestBody),
                cache: 'no-store'
            });

            if (!response.ok) {
                throw new Error(`Simulation fehlgeschlagen: ${response.status}`);
            }

            const result = await response.json();
            
            // Display result
            const afterImage = document.getElementById('afterImage');
            if (afterImage && result.result_png) {
                afterImage.src = 'data:image/png;base64,' + result.result_png;
                this.lastResult = result.result_png;
                
                // Show download button
                const downloadBtn = document.getElementById('downloadBtn');
                if (downloadBtn) downloadBtn.style.display = 'block';
                
                // Add to history
                this.addToHistory({
                    id: requestId,
                    area: this.selectedArea,
                    volume: volume,
                    image: result.result_png,
                    timestamp: Date.now()
                });
            }
            
        } catch (error) {
            console.error('Generation error:', error);
            this.showError('Generierung fehlgeschlagen. Bitte versuchen Sie es erneut.');
        } finally {
            // Hide loading state
            if (generateBtn) generateBtn.style.display = 'flex';
            if (loader) loader.style.display = 'none';
        }
    }

    // Generation History
    addToHistory(generation) {
        this.generationHistory.unshift(generation);
        
        // Limit history size
        if (this.generationHistory.length > this.maxHistoryItems) {
            this.generationHistory = this.generationHistory.slice(0, this.maxHistoryItems);
        }
        
        this.updateHistoryDisplay();
    }

    updateHistoryDisplay() {
        const carousel = document.getElementById('generationsCarousel');
        const section = document.getElementById('generationsSection');
        
        if (!carousel || !section) return;
        
        if (this.generationHistory.length > 0) {
            section.style.display = 'block';
            
            carousel.innerHTML = '';
            this.generationHistory.forEach((gen, index) => {
                const thumb = document.createElement('div');
                thumb.className = 'generation-thumb';
                thumb.innerHTML = `
                    <img src="data:image/png;base64,${gen.image}" alt="Generation ${index + 1}">
                    <div class="thumb-overlay">
                        <span>${gen.volume.toFixed(1)} ml</span>
                        <button class="thumb-download" onclick="app.downloadGeneration('${gen.id}')">
                            <i class="fas fa-download"></i>
                        </button>
                    </div>
                `;
                
                // Click to view
                thumb.addEventListener('click', (e) => {
                    if (!e.target.closest('.thumb-download')) {
                        const afterImage = document.getElementById('afterImage');
                        if (afterImage) {
                            afterImage.src = 'data:image/png;base64,' + gen.image;
                            this.lastResult = gen.image;
                        }
                    }
                });
                
                carousel.appendChild(thumb);
            });
        }
    }

    downloadGeneration(id) {
        const generation = this.generationHistory.find(g => g.id === id);
        if (generation) {
            this.downloadImage(generation.image, `nuvaface_${generation.area}_${generation.id}.png`);
        }
    }

    downloadResult() {
        if (this.lastResult) {
            this.downloadImage(this.lastResult, `nuvaface_${this.selectedArea}_${Date.now()}.png`);
        }
    }

    downloadImage(base64Data, filename) {
        const link = document.createElement('a');
        link.href = 'data:image/png;base64,' + base64Data;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // Utilities
    generateRequestId() {
        return 'req-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
    }

    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health?v=${Date.now()}`, { 
                cache: 'no-store',
                mode: 'cors'
            });
            const health = await response.json();
            console.log('API Health:', health);
        } catch (error) {
            console.error('API not available:', error);
            // Don't show error on startup, API might be waking up
        }
    }

    showError(message) {
        // Simple error display - can be enhanced with better UI
        alert(message);
    }

    startOver() {
        // Reset state
        this.currentImage = null;
        this.currentImageBase64 = null;
        this.selectedArea = null;
        this.currentMask = null;
        this.lastResult = null;
        
        // Clear selections
        document.querySelectorAll('.hotspot').forEach(spot => {
            spot.classList.remove('selected');
        });
        
        // Reset UI
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) proceedBtn.disabled = true;
        
        // Go to landing
        this.showSection('landingSection');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NuvaFaceApp();
});