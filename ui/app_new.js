// NuvaFace Modernized UI Application
// WICHTIG: API-Calls bleiben unverändert, nur UI/UX wird modernisiert

class NuvaFaceApp {
    constructor() {
        // API Configuration (UNCHANGED)
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        if (isLocal) {
            this.apiBaseUrl = 'http://localhost:8080';
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
        this.currentViewMode = 'before'; // before, after, split
        this.splitPosition = 0.5; // 50% split (0.0-1.0)
        this.isDragging = false;
        this.isAnimating = false;
        this.areaPicker3D = null; // 3D area picker instance
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeAnimations();
        this.initialize3DPicker();
        this.checkApiHealth();
        this.showSection('landingSection');
    }
    
    initializeAnimations() {
        // Set up GSAP defaults
        gsap.defaults({
            duration: 0.3,
            ease: "power2.out"
        });
        
        // Initialize page with animation
        gsap.from(".main-container", {
            opacity: 0,
            y: 20,
            duration: 0.8,
            ease: "power3.out"
        });
    }
    
    initialize3DPicker() {
        // Initialize 3D area picker when Three.js is available
        if (typeof THREE !== 'undefined' && typeof AreaPicker3D !== 'undefined') {
            try {
                this.areaPicker3D = new AreaPicker3D('face3DContainer');
                
                // Set up callbacks for area interaction
                this.areaPicker3D.setAreaHoverCallback((area) => {
                    this.showAreaInfo({ currentTarget: { dataset: { area } } });
                });
                
                this.areaPicker3D.setAreaLeaveCallback(() => {
                    this.hideAreaInfo();
                });
                
                this.areaPicker3D.setAreaSelectCallback((area) => {
                    this.selectedArea = area;
                    
                    // Update UI to show selection
                    document.querySelectorAll('.hotspot').forEach(spot => {
                        spot.classList.remove('selected');
                    });
                    
                    const hotspot = document.querySelector(`[data-area="${area}"]`);
                    if (hotspot) {
                        hotspot.classList.add('selected');
                    }
                    
                    // Enable proceed button
                    const proceedBtn = document.getElementById('proceedToUpload');
                    if (proceedBtn) {
                        proceedBtn.disabled = false;
                    }
                    
                    // Show area info
                    this.showAreaInfo({ currentTarget: { dataset: { area } } });
                });
                
                // Hide loading and show 3D model
                setTimeout(() => {
                    const loading = document.querySelector('.loading-3d');
                    if (loading) {
                        loading.style.display = 'none';
                    }
                }, 2000);
                
            } catch (error) {
                console.warn('Failed to initialize 3D picker:', error);
                this.fallbackToSVG();
            }
        } else {
            console.warn('Three.js or AreaPicker3D not available, falling back to SVG');
            this.fallbackToSVG();
        }
    }
    
    fallbackToSVG() {
        // Show fallback SVG and hide 3D container
        const container3D = document.getElementById('face3DContainer');
        const svgFallback = document.querySelector('.fallback-svg');
        
        if (container3D && svgFallback) {
            container3D.style.display = 'none';
            svgFallback.style.display = 'block';
            
            // Show instructions
            const instructions = document.createElement('div');
            instructions.className = 'model-instructions';
            instructions.innerHTML = `
                <h4>🔄 3D Modell verfügbar machen</h4>
                <p>Für eine bessere Erfahrung:</p>
                <p><strong>1.</strong> Laden Sie das <a href="https://download.blender.org/demo/asset-bundles/human-base-meshes/" target="_blank">Blender Studio Human Base Meshes Bundle</a> herunter</p>
                <p><strong>2.</strong> Exportieren Sie den weiblichen Kopf als GLB aus Blender</p>
                <p><strong>3.</strong> Speichern Sie ihn als <code>assets/models/female_head.glb</code></p>
            `;
            
            const areaSelection = document.querySelector('.area-selection-interactive');
            if (areaSelection) {
                areaSelection.appendChild(instructions);
            }
        }
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
        
        // Initialize split view drag functionality
        this.setupSplitViewDrag();
    }

    // Enhanced Section Navigation with GSAP
    showSection(sectionId) {
        if (this.isAnimating) return;
        this.isAnimating = true;
        
        const currentSection = document.querySelector('.section.active');
        const targetSection = document.getElementById(sectionId);
        
        if (!targetSection) {
            this.isAnimating = false;
            return;
        }
        
        // Exit animation for current section
        if (currentSection) {
            gsap.to(currentSection, {
                opacity: 0,
                y: -20,
                duration: 0.2,
                onComplete: () => {
                    currentSection.classList.remove('active');
                    currentSection.style.display = 'none';
                    
                    // Enter animation for target section
                    targetSection.style.display = 'block';
                    targetSection.classList.add('active');
                    
                    gsap.fromTo(targetSection, 
                        { opacity: 0, y: 30, scale: 0.95 },
                        { 
                            opacity: 1, 
                            y: 0, 
                            scale: 1,
                            duration: 0.5,
                            ease: "back.out(1.7)",
                            onComplete: () => {
                                this.isAnimating = false;
                            }
                        }
                    );
                }
            });
        } else {
            // First load
            targetSection.style.display = 'block';
            targetSection.classList.add('active');
            gsap.fromTo(targetSection, 
                { opacity: 0, y: 30 },
                { opacity: 1, y: 0, duration: 0.5, onComplete: () => this.isAnimating = false }
            );
        }
        
        // Section-specific setup
        if (sectionId === 'uploadSection' && this.selectedArea) {
            this.setupUploadSection();
        }
    }
    
    setupUploadSection() {
        const display = document.getElementById('selectedAreaDisplay');
        if (display) {
            const areaNames = {
                'lips': 'Lippen (Filler)',
                'chin': 'Kinn (Filler)',
                'cheeks': 'Wangen (Filler)',
                'forehead': 'Stirn (Botox)'
            };
            
            // Animate area display
            gsap.fromTo(display, 
                { opacity: 0, scale: 0.8 },
                { opacity: 1, scale: 1, delay: 0.2 }
            );
            
            display.textContent = areaNames[this.selectedArea] || this.selectedArea;
        }
        
        // Show area-specific guidelines with stagger animation
        this.showAreaSpecificGuidelines(this.selectedArea);
    }

    // Enhanced Area Selection with Animations
    selectArea(e) {
        const area = e.currentTarget.dataset.area;
        const hotspot = e.currentTarget;
        
        // Deselect all with animation
        document.querySelectorAll('.hotspot').forEach(spot => {
            if (spot !== hotspot) {
                spot.classList.remove('selected');
                gsap.to(spot, {
                    scale: 1,
                    duration: 0.2
                });
            }
        });
        
        // Select current with bounce animation
        hotspot.classList.add('selected');
        gsap.fromTo(hotspot,
            { scale: 1 },
            { 
                scale: 1.15,
                duration: 0.4,
                ease: "back.out(3)",
                yoyo: false
            }
        );
        
        this.selectedArea = area;
        
        // Animate proceed button
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.disabled = false;
            gsap.fromTo(proceedBtn,
                { scale: 0.9, opacity: 0.5 },
                { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }
            );
        }
        
        // Update info with slide animation
        this.animateAreaInfo(e);
    }
    
    animateAreaInfo(e) {
        const infoBox = document.getElementById('areaInfo');
        if (!infoBox) return;
        
        const area = e.currentTarget.dataset.area;
        const descriptions = {
            'lips': 'Lippenvolumen mit Hyaluronsäure (0.5-5.0 ml)',
            'chin': 'Kinnkorrektur mit Hyaluronsäure (1.0-4.0 ml)',
            'cheeks': 'Wangenvolumen mit Hyaluronsäure (1.0-4.0 ml)',
            'forehead': 'Stirnfalten-Behandlung mit Botox (10-40 Units)'
        };
        
        gsap.to(infoBox, {
            opacity: 0,
            y: -10,
            duration: 0.15,
            onComplete: () => {
                infoBox.innerHTML = `<strong>${descriptions[area] || area}</strong>`;
                gsap.to(infoBox, {
                    opacity: 1,
                    y: 0,
                    duration: 0.25,
                    ease: "back.out(2)"
                });
            }
        });
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
        
        // Validate area selection
        if (!this.selectedArea) {
            this.showError('Bitte wählen Sie zuerst einen Behandlungsbereich aus.');
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
            
            // Wait for image to load before proceeding
            this.currentImage.onload = () => {
                // ROUTING FIX: Only go to segmentation for lips
                if (this.selectedArea === 'lips') {
                    // For lips, go to segmentation first
                    setTimeout(() => {
                        this.showSection('segmentSection');
                        this.showSegmentationPreview();
                    }, 800);
                } else {
                    // For all other areas, go directly to result
                    setTimeout(() => {
                        this.showSection('resultSection');
                        this.setupResultView();
                    }, 800);
                }
            };
        };
        reader.readAsDataURL(file);
    }

    changeImage() {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    removeImage() {
        // Reset image state
        this.currentImage = null;
        this.currentImageBase64 = null;
        
        // Show upload area, hide preview
        const uploadArea = document.getElementById('uploadArea');
        const uploadPreview = document.getElementById('uploadPreview');
        const fileInput = document.getElementById('fileInput');
        
        if (uploadArea && uploadPreview) {
            uploadArea.style.display = 'block';
            uploadPreview.style.display = 'none';
        }
        
        // Reset file input
        if (fileInput) {
            fileInput.value = '';
        }
    }

    // Enhanced Segmentation Preview with Status Updates
    async showSegmentationPreview() {
        if (this.selectedArea !== 'lips') return;
        
        const statusLoading = document.getElementById('statusLoading');
        const statusSuccess = document.getElementById('statusSuccess');
        const statusWarning = document.getElementById('statusWarning');
        const continueBtn = document.getElementById('continueToResult');
        
        // Show loading state
        if (statusLoading) statusLoading.style.display = 'flex';
        if (statusSuccess) statusSuccess.style.display = 'none';
        if (statusWarning) statusWarning.style.display = 'none';
        if (continueBtn) continueBtn.disabled = true;
        
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
                
                // Set canvas size to fit container
                const containerWidth = Math.min(this.currentImage.width, 500);
                const scale = containerWidth / this.currentImage.width;
                
                canvas.width = this.currentImage.width * scale;
                canvas.height = this.currentImage.height * scale;
                overlay.width = this.currentImage.width * scale;
                overlay.height = this.currentImage.height * scale;
                
                // Make canvases visible and properly sized
                canvas.style.position = 'relative';
                canvas.style.maxWidth = '100%';
                canvas.style.height = 'auto';
                overlay.style.position = 'absolute';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.maxWidth = '100%';
                overlay.style.height = 'auto';
                
                // Draw scaled original image
                ctx.drawImage(this.currentImage, 0, 0, canvas.width, canvas.height);
                
                // Show canvas immediately
                canvas.style.display = 'block';
                overlay.style.display = 'block';
                
                // Draw mask overlay
                if (result.mask_png) {
                    const maskImg = new Image();
                    maskImg.onload = () => {
                        overlayCtx.globalAlpha = 0.5;
                        overlayCtx.fillStyle = '#ff4444';
                        overlayCtx.globalCompositeOperation = 'source-over';
                        
                        // Create red overlay where mask is white
                        overlayCtx.drawImage(maskImg, 0, 0, canvas.width, canvas.height);
                        overlayCtx.globalCompositeOperation = 'source-in';
                        overlayCtx.fillRect(0, 0, canvas.width, canvas.height);
                        
                        // Show success status
                        if (statusLoading) statusLoading.style.display = 'none';
                        if (statusSuccess) statusSuccess.style.display = 'flex';
                        if (continueBtn) continueBtn.disabled = false;
                    };
                    maskImg.src = 'data:image/png;base64,' + result.mask_png;
                    
                    this.currentMask = result.mask_png;
                } else {
                    // No mask found, but still show image and allow continue
                    if (statusLoading) statusLoading.style.display = 'none';
                    if (statusSuccess) statusSuccess.style.display = 'flex';
                    if (continueBtn) continueBtn.disabled = false;
                }
            }
        } catch (error) {
            console.error('Segmentation error:', error);
            this.showSegmentationWarning();
        }
    }
    
    showSegmentationWarning() {
        const statusLoading = document.getElementById('statusLoading');
        const statusWarning = document.getElementById('statusWarning');
        const continueBtn = document.getElementById('continueToResult');
        
        if (statusLoading) statusLoading.style.display = 'none';
        if (statusWarning) statusWarning.style.display = 'flex';
        if (continueBtn) {
            continueBtn.disabled = false;
            continueBtn.innerHTML = '<i class="fas fa-arrow-right"></i> Trotzdem fortfahren';
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
            afterImage.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect width="400" height="400" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="45%25" text-anchor="middle" dy=".3em" fill="%23999" font-size="16"%3EKlicken Sie auf%3C/text%3E%3Ctext x="50%25" y="55%25" text-anchor="middle" dy=".3em" fill="%23667eea" font-size="18" font-weight="bold"%3EGenerieren%3C/text%3E%3C/svg%3E';
        }
        
        // Hide download button initially
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) downloadBtn.style.display = 'none';
        
        // Set initial volume based on area
        this.setInitialVolumeForArea();
        this.updateVolumeDisplay();
    }
    
    setInitialVolumeForArea() {
        const slider = document.getElementById('volumeSlider');
        if (!slider) return;
        
        // Set default volumes based on area
        const defaultVolumes = {
            'lips': 1.5,
            'chin': 2.0,
            'cheeks': 1.8, 
            'forehead': 1.0 // For Botox, this represents intensity
        };
        
        slider.value = defaultVolumes[this.selectedArea] || 2.0;
    }

    updateVolumeDisplay() {
        const slider = document.getElementById('volumeSlider');
        const display = document.getElementById('volumeValue');
        
        if (slider && display) {
            const value = parseFloat(slider.value);
            display.textContent = value.toFixed(1) + ' ml';
        }
    }

    // Enhanced Generate Simulation with Animated Loading
    async generateSimulation() {
        const generateBtn = document.getElementById('generateBtn');
        const progressIndicator = document.getElementById('progressIndicator');
        const progressText = document.getElementById('progressText');
        const volumeSlider = document.getElementById('volumeSlider');
        const afterImage = document.getElementById('afterImage');
        
        if (!this.currentImageBase64 || !this.selectedArea) {
            this.showError('Bitte wählen Sie zuerst ein Bild und einen Bereich aus.');
            return;
        }
        
        // Show enhanced loading state
        if (generateBtn) {
            generateBtn.classList.add('loading');
            generateBtn.disabled = true;
        }
        if (progressIndicator) {
            progressIndicator.classList.add('active');
        }
        
        // Progress messages
        const progressMessages = [
            'KI analysiert Ihr Gesicht...',
            'Behandlungsbereich wird erkannt...',
            'Simulation wird generiert...',
            'Ergebnis wird optimiert...'
        ];
        
        let progressIndex = 0;
        const progressInterval = setInterval(() => {
            if (progressText && progressIndex < progressMessages.length) {
                progressText.textContent = progressMessages[progressIndex];
                progressIndex++;
            }
        }, 1500);
        
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
            
            // Final progress message
            if (progressText) {
                progressText.textContent = 'Ergebnis wird geladen...';
            }
            
            // Display result with smooth transition
            if (afterImage && result.result_png) {
                afterImage.style.opacity = '0';
                afterImage.src = 'data:image/png;base64,' + result.result_png;
                
                afterImage.onload = () => {
                    afterImage.style.transition = 'opacity 0.5s ease';
                    afterImage.style.opacity = '1';
                    
                    // Success feedback
                    if (progressText) {
                        progressText.textContent = '✨ Simulation erfolgreich!';
                    }
                    
                    setTimeout(() => {
                        if (progressIndicator) {
                            progressIndicator.classList.remove('active');
                        }
                    }, 2000);
                };
                
                this.lastResult = result.result_png;
                
                // Show view toggle and download button
                const viewToggle = document.getElementById('viewToggle');
                const downloadBtn = document.getElementById('downloadBtn');
                
                if (viewToggle) {
                    viewToggle.style.display = 'flex';
                    gsap.fromTo(viewToggle,
                        { opacity: 0, y: 20 },
                        { opacity: 1, y: 0, duration: 0.5, delay: 0.3 }
                    );
                }
                
                if (downloadBtn) {
                    downloadBtn.style.display = 'flex';
                    gsap.fromTo(downloadBtn,
                        { opacity: 0, scale: 0.8 },
                        { opacity: 1, scale: 1, duration: 0.3, delay: 0.5 }
                    );
                }
                
                // Store result for split view
                this.lastResult = {
                    original_png: beforeImage.src.split(',')[1],
                    result_png: result.result_png
                };
                
                // Initialize in before view mode
                this.currentViewMode = 'before';
                
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
            if (progressText) {
                progressText.textContent = '❌ Generierung fehlgeschlagen';
            }
            setTimeout(() => {
                this.showError('Generierung fehlgeschlagen. Bitte versuchen Sie es erneut.');
                if (progressIndicator) {
                    progressIndicator.classList.remove('active');
                }
            }, 1500);
        } finally {
            // Clear progress interval
            clearInterval(progressInterval);
            
            // Reset loading state
            if (generateBtn) {
                generateBtn.classList.remove('loading');
                generateBtn.disabled = false;
            }
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
        // Enhanced error display with better UX
        const errorToast = this.createErrorToast(message);
        document.body.appendChild(errorToast);
        
        setTimeout(() => {
            errorToast.remove();
        }, 4000);
    }
    
    createErrorToast(message) {
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" class="toast-close">×</button>
        `;
        
        // Add toast styles dynamically
        const style = document.createElement('style');
        style.textContent = `
            .error-toast {
                position: fixed;
                top: 2rem;
                right: 2rem;
                background: #f87171;
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 0.75rem;
                box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
                display: flex;
                align-items: center;
                gap: 0.75rem;
                z-index: 1000;
                animation: slideIn 0.3s ease;
                max-width: 400px;
            }
            .error-toast i {
                font-size: 1.25rem;
                flex-shrink: 0;
            }
            .toast-close {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                margin-left: auto;
                opacity: 0.7;
            }
            .toast-close:hover {
                opacity: 1;
            }
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        
        if (!document.head.querySelector('style[data-toast-styles]')) {
            style.setAttribute('data-toast-styles', 'true');
            document.head.appendChild(style);
        }
        
        return toast;
    }
    
    // Original Working Switch View
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
                
                // Initialize split view
                if (this.lastResult) {
                    this.setupSplitView();
                } else {
                    // Show current image on both sides if no result yet
                    const splitBefore = document.querySelector('.split-before');
                    const splitAfter = document.querySelector('.split-after');
                    
                    if (this.currentImageBase64 && splitBefore && splitAfter) {
                        const imgSrc = this.currentImageBase64;
                        splitBefore.style.backgroundImage = `url(${imgSrc})`;
                        splitAfter.style.backgroundImage = `url(${imgSrc})`;
                        this.updateSplitView();
                    }
                }
                break;
        }
        
        this.currentViewMode = view;
    }
    
    // Original Split View Functions
    setupSplitViewDrag() {
        const splitView = document.getElementById('splitView');
        if (!splitView) return;
        
        splitView.addEventListener('mousedown', this.startSplitDrag.bind(this));
        document.addEventListener('mousemove', this.handleSplitDrag.bind(this));
        document.addEventListener('mouseup', this.endSplitDrag.bind(this));
        
        // Touch events for mobile
        splitView.addEventListener('touchstart', this.startSplitDrag.bind(this));
        document.addEventListener('touchmove', this.handleSplitDrag.bind(this));
        document.addEventListener('touchend', this.endSplitDrag.bind(this));
    }
    
    startSplitDrag(e) {
        e.preventDefault();
        this.isDragging = true;
        document.body.style.cursor = 'col-resize';
    }
    
    handleSplitDrag(e) {
        if (!this.isDragging) return;
        
        const splitView = document.getElementById('splitView');
        if (!splitView) return;
        
        const rect = splitView.getBoundingClientRect();
        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        const position = (clientX - rect.left) / rect.width;
        
        // Clamp position between 0.1 and 0.9
        this.splitPosition = Math.max(0.1, Math.min(0.9, position));
        this.updateSplitView();
    }
    
    endSplitDrag() {
        this.isDragging = false;
        document.body.style.cursor = '';
    }
    
    updateSplitView() {
        const splitAfter = document.querySelector('.split-after');
        const splitDivider = document.querySelector('.split-divider');
        
        if (splitAfter && splitDivider) {
            const percentage = this.splitPosition * 100;
            splitAfter.style.clipPath = `polygon(${percentage}% 0%, 100% 0%, 100% 100%, ${percentage}% 100%)`;
            splitDivider.style.left = `${percentage}%`;
        }
    }

    setupSplitView() {
        if (!this.lastResult) return;

        const splitBefore = document.querySelector('.split-before');
        const splitAfter = document.querySelector('.split-after');

        if (splitBefore && splitAfter) {
            // Use the before image and after image
            const beforeImg = document.getElementById('beforeImage');
            const afterImg = document.getElementById('afterImage');
            
            if (beforeImg.src && afterImg.src) {
                splitBefore.style.backgroundImage = `url(${beforeImg.src})`;
                splitAfter.style.backgroundImage = `url(${afterImg.src})`;
                this.updateSplitView();
            }
        }
    }

    // Area-specific Do's & Don'ts
    showAreaSpecificGuidelines(area) {
        const areaTypeDisplay = document.getElementById('areaTypeDisplay');
        const guidelinesGrid = document.getElementById('guidelinesGrid');
        
        if (!areaTypeDisplay || !guidelinesGrid) return;
        
        const areaNames = {
            'lips': 'Lippenbehandlung',
            'chin': 'Kinnkorrektur', 
            'cheeks': 'Wangenkonturierung',
            'forehead': 'Stirnbehandlung'
        };
        
        areaTypeDisplay.textContent = areaNames[area] || area;
        
        // Common Do's for all areas
        const commonDos = [
            {
                icon: '✓',
                title: 'Heller, einheitlicher Hintergrund',
                description: 'Neutraler weißer oder grauer Hintergrund, gleichmäßiges Licht',
                image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23888' font-size='14'%3EHeller Hintergrund%3C/text%3E%3C/svg%3E"
            },
            {
                icon: '✓',
                title: 'Frontales Portrait, scharf',
                description: 'Bitte direkt in die Kamera, keine starke Neigung oder Drehung',
                image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23f0f0f0'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23888' font-size='14'%3EFrontales Portrait%3C/text%3E%3C/svg%3E"
            }
        ];
        
        // Area-specific Don'ts
        const areaDonts = {
            'lips': [
                {
                    icon: '✗',
                    title: 'Lippenstift oder Lipgloss',
                    description: 'Make-up verfälscht die natürliche Lippenfarbe und -textur',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23ff6b6b'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EMake-up%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Gespitzte oder offene Lippen',
                    description: 'Natürliche, entspannte Lippenstellung für beste Ergebnisse',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23ff8787'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EGespitzt%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Dunkel / Gegenlicht',
                    description: 'Zu wenig Licht führt zu ungenauen Simulationen',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23333'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='14'%3EDunkel%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Haare verdecken Mundbereich',
                    description: 'Bitte Lippen und Mundwinkel vollständig sichtbar lassen',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23999'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EVerdeckt%3C/text%3E%3C/svg%3E"
                }
            ],
            'chin': [
                {
                    icon: '✗',
                    title: 'Starker Schatten am Kinn',
                    description: 'Schatten verfälschen die natürliche Kinnkontur',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23666'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3ESchatten%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Bart oder Stoppeln',
                    description: 'Gesichtsbehaarung kann die Kinnlinie verdecken',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23777'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='14'%3EBart%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Hochgezogenes Kinn',
                    description: 'Neutrale Kopfhaltung für präzise Kinnanalyse',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23888'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EGeneigt%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Mehrere Personen',
                    description: 'Nur eine Person pro Foto für klare Analyse',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23555'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='10'%3EMehrere%3C/text%3E%3C/svg%3E"
                }
            ],
            'cheeks': [
                {
                    icon: '✗',
                    title: 'Rouge oder Contouring',
                    description: 'Make-up verfälscht die natürliche Wangenkontur',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23ff6b9d'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3ERouge%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Haare verdecken Wangen',
                    description: 'Wangenknochen und Jochbein sichtbar lassen',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23999'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EVerdeckt%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Seitliches Profil',
                    description: 'Frontale Aufnahme für symmetrische Analyse',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23777'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='14'%3EProfil%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Starker Schatten',
                    description: 'Gleichmäßige Beleuchtung für präzise Konturerkennung',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23444'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3ESchatten%3C/text%3E%3C/svg%3E"
                }
            ],
            'forehead': [
                {
                    icon: '✗',
                    title: 'Pony oder Stirnfransen',
                    description: 'Stirnbereich vollständig sichtbar lassen',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%238B4513'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='14'%3EPony%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Hochgezogene Augenbrauen',
                    description: 'Entspannte Gesichtsmuskulatur für natürliche Falten',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23666'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='10'%3EAngespannt%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Kopfbedeckung oder Mütze',
                    description: 'Stirnregion muss vollständig erkennbar sein',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23333'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='12'%3EMütze%3C/text%3E%3C/svg%3E"
                },
                {
                    icon: '✗',
                    title: 'Stirnrunzeln oder Grimassen',
                    description: 'Neutraler Gesichtsausdruck für präzise Analyse',
                    image: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='150' height='150' fill='%23555'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23fff' font-size='10'%3EGrimasse%3C/text%3E%3C/svg%3E"
                }
            ]
        };
        
        const currentDonts = areaDonts[area] || [];
        const allGuidelines = [...commonDos, ...currentDonts];
        
        guidelinesGrid.innerHTML = '';
        allGuidelines.forEach(guideline => {
            const card = document.createElement('div');
            card.className = `guideline-card ${guideline.icon === '✓' ? 'do' : 'dont'}`;
            card.innerHTML = `
                <div class="guideline-icon">${guideline.icon}</div>
                <img src="${guideline.image}" alt="${guideline.title}">
                <h4>${guideline.title}</h4>
                <p>${guideline.description}</p>
            `;
            guidelinesGrid.appendChild(card);
        });
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