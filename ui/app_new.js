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
            this.apiBaseUrl = 'https://nuvaface-gemini-api-212268956806.us-central1.run.app';
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
        // Don't initialize 3D picker immediately - wait for landing section to be visible
        this.checkApiHealth();
        this.showSection('heroSection');
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
            const container = document.getElementById('face3DContainer');
            if (!container) {
                console.warn('3D container not found');
                return;
            }
            
            // Ensure container has proper dimensions
            if (container.clientWidth === 0 || container.clientHeight === 0) {
                console.warn('3D container has no dimensions, retrying...');
                setTimeout(() => this.initialize3DPicker(), 500);
                return;
            }
            
            try {
                console.log('Initializing 3D picker with container dimensions:', 
                    container.clientWidth, 'x', container.clientHeight);
                this.areaPicker3D = new AreaPicker3D('face3DContainer');
                
                // Set up callbacks for area interaction
                this.areaPicker3D.setAreaHoverCallback((area) => {
                    // Make corresponding button light up (mobile-responsive)
                    this.highlightAreaButton(area, true);
                    this.showAreaInfo({ currentTarget: { dataset: { area } } });
                });
                
                this.areaPicker3D.setAreaLeaveCallback(() => {
                    // Remove button highlights
                    this.highlightAreaButton(null, false);
                    this.hideAreaInfo();
                });
                
                this.areaPicker3D.setAreaSelectCallback((area) => {
                    // Update button selection state
                    document.querySelectorAll('.area-select-btn').forEach(btn => {
                        btn.classList.remove('selected');
                        if (btn.dataset.area === area) {
                            btn.classList.add('selected');
                            gsap.fromTo(btn, { scale: 1 }, { scale: 1.05, duration: 0.3, ease: "back.out(2)" });
                        }
                    });
                    
                    // Legacy hotspot support
                    document.querySelectorAll('.hotspot').forEach(spot => {
                        spot.classList.remove('selected');
                        if (spot.dataset.area === area) {
                            spot.classList.add('selected');
                        }
                    });
                    
                    // Mobile haptic feedback
                    if (navigator.vibrate) {
                        navigator.vibrate(50);
                    }
                    
                    // Use centralized method
                    this.setSelectedArea(area);
                    
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
        // Mobile-first: Area selection buttons (primary)
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.addEventListener('click', this.selectAreaFromButton.bind(this));
            // Touch support for mobile
            btn.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
            btn.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
        });
        
        // Legacy hotspot support (for compatibility)
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
        
        // Mobile orientation change handling
        window.addEventListener('orientationchange', this.handleOrientationChange.bind(this));
        window.addEventListener('resize', this.handleResize.bind(this));
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
                                
                                // Initialize 3D picker when landing section becomes visible
                                if (sectionId === 'landingSection' && !this.areaPicker3D) {
                                    setTimeout(() => {
                                        console.log('Initializing 3D picker on section show');
                                        this.initialize3DPicker();
                                    }, 100);
                                }
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
                { 
                    opacity: 1, 
                    y: 0, 
                    duration: 0.5, 
                    onComplete: () => {
                        this.isAnimating = false;
                        
                        // Initialize 3D picker when landing section becomes visible
                        if (sectionId === 'landingSection' && !this.areaPicker3D) {
                            setTimeout(() => {
                                console.log('Initializing 3D picker on first load');
                                this.initialize3DPicker();
                            }, 100);
                        }
                    }
                }
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

    // Area Selection from Button (Mobile & Desktop)
    selectAreaFromButton(e) {
        const area = e.currentTarget.dataset.area;
        const button = e.currentTarget;
        
        // Update visual selection for buttons
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
            if (btn !== button) {
                gsap.to(btn, { scale: 1, duration: 0.2 });
            }
        });
        
        // Select current button with animation
        button.classList.add('selected');
        gsap.fromTo(button,
            { scale: 1 },
            { 
                scale: 1.05,
                duration: 0.3,
                ease: "back.out(2)",
                yoyo: false
            }
        );
        
        // Sync with 3D model if available
        if (this.areaPicker3D) {
            this.areaPicker3D.selectArea(area);
        }
        
        // Mobile haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Use centralized method
        this.setSelectedArea(area);
        
        // Update info display
        this.showAreaInfo(e);
    }
    
    // Legacy Area Selection (for hotspots)
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
        
        // Sync with buttons
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
            if (btn.dataset.area === area) {
                btn.classList.add('selected');
            }
        });
        
        // Use centralized method
        this.setSelectedArea(area);
        
        // Update info display
        this.showAreaInfo(e);
    }
    
    // Touch Event Handlers for Mobile
    handleTouchStart(e) {
        e.currentTarget.classList.add('touching');
        gsap.to(e.currentTarget, { scale: 0.95, duration: 0.1 });
    }
    
    handleTouchEnd(e) {
        e.currentTarget.classList.remove('touching');
        gsap.to(e.currentTarget, { scale: 1, duration: 0.1 });
    }
    
    // Centralized area selection logic
    setSelectedArea(area) {
        this.selectedArea = area;
        
        // Enable proceed button with animation
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.disabled = false;
            proceedBtn.classList.add('animate__animated', 'animate__pulse');
            gsap.fromTo(proceedBtn, 
                { scale: 1, opacity: 0.7 },
                { scale: 1.02, opacity: 1, duration: 0.3 }
            );
            setTimeout(() => {
                proceedBtn.classList.remove('animate__animated', 'animate__pulse');
            }, 1000);
        }
    }
    
    // Mobile orientation and resize handling
    handleOrientationChange() {
        setTimeout(() => {
            this.handleResize();
        }, 100);
    }
    
    handleResize() {
        // Re-initialize 3D model if needed
        if (this.areaPicker3D && window.innerWidth <= 768) {
            this.areaPicker3D.handleResize();
        }
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

    // Area Button Highlighting (Mobile-responsive)
    highlightAreaButton(area, highlight) {
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            if (highlight && btn.dataset.area === area && !btn.classList.contains('selected')) {
                btn.classList.add('hover-from-3d');
                gsap.to(btn, { scale: 1.02, duration: 0.2 });
            } else {
                btn.classList.remove('hover-from-3d');
                if (!btn.classList.contains('selected')) {
                    gsap.to(btn, { scale: 1, duration: 0.2 });
                }
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
        
        // Mobile: Show area info in dedicated area if needed
        const mobileAreaInfo = document.querySelector('.mobile-area-info');
        if (mobileAreaInfo) {
            const areaNames = {
                'lips': 'Lippen',
                'chin': 'Kinn',
                'cheeks': 'Wangen', 
                'forehead': 'Stirn'
            };
            mobileAreaInfo.textContent = areaNames[area] || area;
            mobileAreaInfo.style.display = 'block';
        }
    }

    hideAreaInfo() {
        const infoBox = document.getElementById('areaInfo');
        if (infoBox && !this.selectedArea) {
            infoBox.innerHTML = '<p>Bewegen Sie die Maus über einen Bereich, um mehr zu erfahren</p>';
        }
        
        // Mobile: Hide mobile area info
        const mobileAreaInfo = document.querySelector('.mobile-area-info');
        if (mobileAreaInfo) {
            mobileAreaInfo.style.display = 'none';
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
                // Skip upload section and go directly to result when from gallery
                if (this.fromGallery) {
                    this.fromGallery = false; // Reset flag
                    setTimeout(() => {
                        this.showSection('resultSection');
                        this.setupResultView();
                    }, 500);
                } else {
                    // Normal flow through upload section
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
        // Display the original image in base elements
        const beforeImage = document.getElementById('beforeImage');
        if (beforeImage && this.currentImageBase64) {
            beforeImage.src = this.currentImageBase64;
        }
        
        // Also set in side-by-side view
        const beforeImageSideBySide = document.getElementById('beforeImageSideBySide');
        if (beforeImageSideBySide && this.currentImageBase64) {
            beforeImageSideBySide.src = this.currentImageBase64;
        }
        
        // Clear after image
        const afterImage = document.getElementById('afterImage');
        const placeholderSvg = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="400"%3E%3Crect width="400" height="400" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="45%25" text-anchor="middle" dy=".3em" fill="%23999" font-size="16"%3EKlicken Sie auf%3C/text%3E%3Ctext x="50%25" y="55%25" text-anchor="middle" dy=".3em" fill="%23667eea" font-size="18" font-weight="bold"%3EGenerieren%3C/text%3E%3C/svg%3E';
        
        if (afterImage) {
            afterImage.src = placeholderSvg;
        }
        
        // Also clear in side-by-side view
        const afterImageSideBySide = document.getElementById('afterImageSideBySide');
        if (afterImageSideBySide) {
            afterImageSideBySide.src = placeholderSvg;
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
        const volumeSlider = document.getElementById('volumeSlider');
        const afterImage = document.getElementById('afterImage');
        
        if (!this.currentImageBase64 || !this.selectedArea) {
            this.showError('Bitte wählen Sie zuerst ein Bild und einen Bereich aus.');
            return;
        }
        
        // Show enhanced loading overlay
        this.showEnhancedLoading();
        
        // Disable generate button during processing
        if (generateBtn) {
            generateBtn.classList.add('loading');
            generateBtn.disabled = true;
        }
        
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
            
            // Update progress to completion
            this.updateEnhancedLoading('Ergebnis wird geladen...', 90);
            
            // Display result with smooth transition
            if (afterImage && result.result_png) {
                const resultImageData = 'data:image/png;base64,' + result.result_png;
                
                afterImage.style.opacity = '0';
                afterImage.src = resultImageData;
                
                // Also set in side-by-side view
                const afterImageSideBySide = document.getElementById('afterImageSideBySide');
                if (afterImageSideBySide) {
                    afterImageSideBySide.style.opacity = '0';
                    afterImageSideBySide.src = resultImageData;
                }
                
                afterImage.onload = () => {
                    afterImage.style.transition = 'opacity 0.5s ease';
                    afterImage.style.opacity = '1';
                    
                    // Animate side-by-side view too
                    if (afterImageSideBySide) {
                        afterImageSideBySide.style.transition = 'opacity 0.5s ease';
                        afterImageSideBySide.style.opacity = '1';
                    }
                    
                    // Show unified view toggle and container
                    this.showUnifiedViewSystem();
                    
                    // Update split view if currently active
                    if (this.currentViewMode === 'split') {
                        this.setupSplitView();
                    }
                    
                    // Complete progress and hide loading overlay
                    this.updateEnhancedLoading('✨ Simulation erfolgreich!', 100);
                    
                    setTimeout(() => {
                        this.hideEnhancedLoading();
                    }, 1500);
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
            
            // Show error state in loading overlay
            this.updateEnhancedLoading('❌ Generierung fehlgeschlagen', 0);
            
            setTimeout(() => {
                this.hideEnhancedLoading();
                this.showError('Generierung fehlgeschlagen. Bitte versuchen Sie es erneut.');
            }, 2000);
        } finally {
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
        const splitBefore = document.querySelector('.split-before');
        const splitAfter = document.querySelector('.split-after');
        const splitDivider = document.querySelector('.split-divider');

        if (splitBefore && splitAfter) {
            // Use the before image and after image
            const beforeImg = document.getElementById('beforeImage');
            const afterImg = document.getElementById('afterImage');
            
            if (beforeImg && beforeImg.src && afterImg && afterImg.src) {
                // Set background images
                splitBefore.style.backgroundImage = `url(${beforeImg.src})`;
                splitBefore.style.backgroundSize = 'cover';
                splitBefore.style.backgroundPosition = 'center';
                
                splitAfter.style.backgroundImage = `url(${afterImg.src})`;
                splitAfter.style.backgroundSize = 'cover';
                splitAfter.style.backgroundPosition = 'center';
                
                // Initialize split position to center
                this.splitPosition = 0.5;
                
                // Set initial divider position
                if (splitDivider) {
                    splitDivider.style.left = '50%';
                }
                
                // Update the split view
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

    // Unified View System
    switchUnifiedView(event) {
        const viewType = event.currentTarget.dataset.view;
        
        // Update button states
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.currentTarget.classList.add('active');
        
        // Switch views
        const sidebysidesView = document.getElementById('sidebysidesView');
        const splitView = document.getElementById('splitView');
        
        if (viewType === 'sidebyside') {
            sidebysidesView.style.display = 'grid';
            splitView.style.display = 'none';
            this.currentViewMode = 'sidebyside';
        } else if (viewType === 'split') {
            sidebysidesView.style.display = 'none';
            splitView.style.display = 'block';
            this.currentViewMode = 'split';
            // Initialize split view with proper images
            this.setupSplitView();
            this.setupSplitViewDrag();
        }
    }
    
    updateSplitViewImages(beforeImage, afterImage) {
        const splitBefore = document.querySelector('.split-before');
        const splitAfter = document.querySelector('.split-after');
        
        if (splitBefore && splitAfter) {
            splitBefore.style.backgroundImage = `url(${beforeImage})`;
            splitBefore.style.backgroundSize = 'cover';
            splitBefore.style.backgroundPosition = 'center';
            
            splitAfter.style.backgroundImage = `url(${afterImage})`;
            splitAfter.style.backgroundSize = 'cover';
            splitAfter.style.backgroundPosition = 'center';
        }
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
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        // Reset UI
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) proceedBtn.disabled = true;
        
        // Hide unified view toggle
        const unifiedViewToggle = document.getElementById('unifiedViewToggle');
        if (unifiedViewToggle) {
            unifiedViewToggle.style.display = 'none';
        }
        
        // Go to landing
        this.showSection('landingSection');
    }
    
    // NEW: Handle area button clicks (Kacheln)
    handleAreaButtonClick(e) {
        const area = e.currentTarget.dataset.area;
        const isCurrentlySelected = e.currentTarget.classList.contains('selected');
        
        if (isCurrentlySelected) {
            // Deselect current area
            this.deselectCurrentArea();
        } else {
            // Select new area
            this.setSelectedArea(area);
            
            // Highlight corresponding 3D area
            if (this.areaPicker3D) {
                console.log(`🎯 Button click: highlighting ${area} on 3D model`);
                this.areaPicker3D.selectAreaFromButton(area);
                this.areaPicker3D.highlightAreaFromButton(area);
            }
        }
    }
    
    // NEW: Update area button selection to match 3D model
    updateAreaButtonSelection(area) {
        console.log(`🔄 Updating area button selection to: ${area}`);
        
        // Clear all button selections
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        // Highlight matching button
        if (area) {
            const matchingBtn = document.querySelector(`[data-area="${area}"]`);
            if (matchingBtn) {
                matchingBtn.classList.add('selected');
                console.log(`✅ Area button ${area} selected`);
            }
        }
    }
    
    // NEW: Set selected area and update all related UI
    setSelectedArea(area) {
        this.selectedArea = area;
        console.log(`🎯 Area selected: ${area}`);
        
        // Update area buttons
        this.updateAreaButtonSelection(area);
        
        // Enable proceed button
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.disabled = false;
        }
        
        // Update area display
        const areaDisplay = document.getElementById('selectedAreaDisplay');
        if (areaDisplay) {
            const areaNames = {
                'lips': 'Lippen',
                'cheeks': 'Wangen', 
                'chin': 'Kinn',
                'forehead': 'Stirn'
            };
            areaDisplay.textContent = areaNames[area] || area;
        }
    }
    
    // NEW: Deselect current area
    deselectCurrentArea() {
        this.selectedArea = null;
        console.log('🗑️ Area deselected');
        
        // Clear all selections
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        document.querySelectorAll('.hotspot').forEach(spot => {
            spot.classList.remove('selected');
        });
        
        // Clear 3D highlighting
        if (this.areaPicker3D) {
            this.areaPicker3D.clearButtonSelection();
        }
        
        // Disable proceed button
        const proceedBtn = document.getElementById('proceedToUpload');
        if (proceedBtn) {
            proceedBtn.disabled = true;
        }
        
        // Clear area display
        const areaDisplay = document.getElementById('selectedAreaDisplay');
        if (areaDisplay) {
            areaDisplay.textContent = '-';
        }
    }

    // Enhanced Loading Animation System
    showEnhancedLoading() {
        const overlay = document.getElementById('enhancedLoadingOverlay');
        const progressBar = document.getElementById('progressBar');
        
        if (overlay) {
            overlay.style.display = 'flex';
            
            // Reset progress bar
            if (progressBar) {
                progressBar.style.width = '0%';
            }
            
            // Start progressive loading animation
            this.startProgressAnimation();
            
            // Animate overlay entrance
            gsap.fromTo(overlay, 
                { opacity: 0 }, 
                { opacity: 1, duration: 0.3 }
            );
        }
    }

    updateEnhancedLoading(message, progress = null) {
        const loadingMessage = document.getElementById('loadingMessage');
        const loadingTitle = document.getElementById('loadingTitle');
        const progressBar = document.getElementById('progressBar');
        
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
        
        if (progress !== null && progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        // Update title for error states
        if (message.includes('❌') && loadingTitle) {
            loadingTitle.textContent = 'Fehler aufgetreten';
        } else if (message.includes('✨') && loadingTitle) {
            loadingTitle.textContent = 'Simulation abgeschlossen!';
        }
    }

    hideEnhancedLoading() {
        const overlay = document.getElementById('enhancedLoadingOverlay');
        
        if (overlay) {
            // Animate overlay exit
            gsap.to(overlay, {
                opacity: 0,
                duration: 0.3,
                onComplete: () => {
                    overlay.style.display = 'none';
                    this.resetLoadingState();
                }
            });
        }
    }

    startProgressAnimation() {
        const progressBar = document.getElementById('progressBar');
        const loadingMessage = document.getElementById('loadingMessage');
        
        if (!progressBar) return;
        
        // Progressive loading messages
        const progressStages = [
            { progress: 20, message: 'KI analysiert Ihr Gesicht...', delay: 1000 },
            { progress: 40, message: 'Behandlungsbereich wird erkannt...', delay: 2500 },
            { progress: 60, message: 'Simulation wird generiert...', delay: 4000 },
            { progress: 80, message: 'Ergebnis wird optimiert...', delay: 6000 }
        ];
        
        progressStages.forEach(stage => {
            setTimeout(() => {
                if (progressBar.style.width !== '100%' && progressBar.style.width !== '0%') {
                    progressBar.style.width = `${stage.progress}%`;
                    if (loadingMessage) {
                        loadingMessage.textContent = stage.message;
                    }
                }
            }, stage.delay);
        });
    }

    resetLoadingState() {
        const loadingTitle = document.getElementById('loadingTitle');
        const loadingMessage = document.getElementById('loadingMessage');
        const progressBar = document.getElementById('progressBar');
        
        if (loadingTitle) {
            loadingTitle.textContent = 'KI generiert Simulation...';
        }
        if (loadingMessage) {
            loadingMessage.textContent = 'Ihr Behandlungsergebnis wird berechnet';
        }
        if (progressBar) {
            progressBar.style.width = '0%';
        }
    }

    // New methods for updated user journey
    showAreaSelection() {
        this.showSection('landingSection');
    }
    
    showImageSourceModal() {
        const modal = document.getElementById('imageSourceModal');
        if (modal) {
            modal.style.display = 'flex';
            gsap.fromTo(modal, 
                { opacity: 0 }, 
                { opacity: 1, duration: 0.3 }
            );
        }
    }
    
    closeImageSourceModal() {
        const modal = document.getElementById('imageSourceModal');
        if (modal) {
            gsap.to(modal, {
                opacity: 0,
                duration: 0.3,
                onComplete: () => {
                    modal.style.display = 'none';
                }
            });
        }
    }
    
    openGallery() {
        // Close modal first
        this.closeImageSourceModal();
        
        // Set flag to skip upload section
        this.fromGallery = true;
        
        // Trigger file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    async openCamera() {
        // Close modal
        this.closeImageSourceModal();
        
        // Show camera view
        const cameraView = document.getElementById('cameraView');
        if (cameraView) {
            cameraView.style.display = 'block';
            
            // Initialize camera and face detection
            await this.initializeCamera();
        }
    }
    
    async initializeCamera() {
        try {
            // Detect if mobile or desktop
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            
            // Use portrait aspect ratio (9:16) for both mobile and desktop
            let constraints = {
                video: {
                    width: { ideal: 1080 },
                    height: { ideal: 1920 },
                    aspectRatio: { ideal: 9/16 },
                    facingMode: 'environment' // Rear camera by default
                }
            };
            
            let stream;
            try {
                // Try rear camera first
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                this.currentFacingMode = 'environment';
            } catch (err) {
                // Fallback to front camera if rear is not available
                console.log('Rear camera not available, falling back to front camera');
                constraints.video.facingMode = 'user';
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                this.currentFacingMode = 'user';
            }
            
            const video = document.getElementById('cameraStream');
            if (video) {
                video.srcObject = stream;
                this.currentStream = stream;
                
                // Apply mirroring only for front camera
                if (this.currentFacingMode === 'user') {
                    video.style.transform = 'scaleX(-1)';
                } else {
                    video.style.transform = 'scaleX(1)';
                }
                
                // Initialize face detection
                await this.initializeFaceDetection();
            }
        } catch (error) {
            console.error('Camera access error:', error);
            this.showError('Kamera konnte nicht gestartet werden. Bitte prüfen Sie die Berechtigungen.');
            this.closeCamera();
        }
    }
    
    async initializeFaceDetection() {
        try {
            console.log('Initializing face detection...');
            
            // Load face detection model with error handling
            const model = faceDetection.SupportedModels.MediaPipeFaceDetector;
            const detectorConfig = {
                runtime: 'tfjs',
                modelType: 'short',
                maxFaces: 1,
                refineLandmarks: false
            };
            
            this.faceDetector = await faceDetection.createDetector(model, detectorConfig);
            console.log('Face detector initialized successfully');
            
            // Wait for video to be ready
            const video = document.getElementById('cameraStream');
            if (video) {
                video.addEventListener('loadeddata', () => {
                    console.log('Video loaded, starting face detection...');
                    this.detectFaces();
                });
                
                // If video is already loaded, start immediately
                if (video.readyState >= 2) {
                    console.log('Video already ready, starting face detection...');
                    this.detectFaces();
                }
            }
        } catch (error) {
            console.error('Failed to initialize face detection:', error);
            // Show error but allow manual capture
            const captureButton = document.getElementById('captureButton');
            if (captureButton) {
                captureButton.disabled = false;
            }
        }
    }
    
    async detectFaces() {
        if (!this.faceDetector || !this.currentStream) {
            console.log('Detector or stream not ready');
            return;
        }
        
        const video = document.getElementById('cameraStream');
        const faceOverlay = document.getElementById('faceOverlay');
        const faceStatus = document.getElementById('faceStatus');
        const captureButton = document.getElementById('captureButton');
        const faceGuide = document.querySelector('.face-guide');
        
        if (video && video.readyState >= 2) {
            try {
                const faces = await this.faceDetector.estimateFaces(video);
                console.log(`Detected ${faces.length} face(s)`);
                
                if (faces.length > 0) {
                    const face = faces[0];
                    // Try different properties for the bounding box
                    let box = face.box || face.boundingBox || {};
                    
                    // MediaPipe sometimes returns the box in a different format
                    if (!box.width && face.keypoints) {
                        // Calculate box from keypoints if available
                        const keypoints = face.keypoints;
                        let minX = Infinity, maxX = -Infinity;
                        let minY = Infinity, maxY = -Infinity;
                        
                        keypoints.forEach(kp => {
                            minX = Math.min(minX, kp.x);
                            maxX = Math.max(maxX, kp.x);
                            minY = Math.min(minY, kp.y);
                            maxY = Math.max(maxY, kp.y);
                        });
                        
                        box = {
                            xMin: minX,
                            yMin: minY,
                            width: maxX - minX,
                            height: maxY - minY
                        };
                    }
                    
                    // Log detection details
                    console.log('Face box:', {
                        x: box.xMin,
                        y: box.yMin,
                        width: box.width,
                        height: box.height
                    });
                    
                    // Get video dimensions
                    const videoWidth = video.videoWidth;
                    const videoHeight = video.videoHeight;
                    
                    // Calculate face position relative to frame center
                    const faceCenterX = box.xMin + (box.width / 2);
                    const faceCenterY = box.yMin + (box.height / 2);
                    const frameCenterX = videoWidth / 2;
                    const frameCenterY = videoHeight / 2;
                    
                    // Calculate offset from center (in percentage)
                    const xOffset = Math.abs(faceCenterX - frameCenterX) / videoWidth;
                    const yOffset = Math.abs(faceCenterY - frameCenterY) / videoHeight;
                    
                    // Calculate face size relative to frame
                    const faceWidthRatio = box.width / videoWidth;
                    const faceHeightRatio = box.height / videoHeight;
                    
                    console.log('Face position:', {
                        xOffset: (xOffset * 100).toFixed(1) + '%',
                        yOffset: (yOffset * 100).toFixed(1) + '%',
                        widthRatio: (faceWidthRatio * 100).toFixed(1) + '%',
                        heightRatio: (faceHeightRatio * 100).toFixed(1) + '%'
                    });
                    
                    // Check if we have valid box dimensions
                    const hasValidBox = box.width > 0 && box.height > 0;
                    
                    // If we don't have valid box dimensions but detected a face, enable capture anyway
                    if (!hasValidBox && faces.length > 0) {
                        console.log('⚠️ Face detected but box invalid, enabling capture anyway');
                        if (faceGuide) {
                            faceGuide.classList.add('detected');
                        }
                        if (faceStatus) {
                            faceStatus.innerHTML = '<span class="status-text">Gesicht erkannt - Bereit für Aufnahme</span>';
                        }
                        if (captureButton) {
                            captureButton.disabled = false;
                        }
                        // Skip the rest of the detection logic
                        setTimeout(() => this.detectFaces(), 100);
                        return;
                    }
                    
                    // More lenient detection criteria
                    const isCentered = xOffset < 0.25 && yOffset < 0.35; // Allow 25% x-offset, 35% y-offset
                    const isGoodSize = faceWidthRatio > 0.12 && faceWidthRatio < 0.7; // 12% to 70% of frame width
                    const isWellPositioned = hasValidBox && isCentered && isGoodSize;
                    
                    if (isWellPositioned) {
                        // Face is well positioned - make overlay green
                        console.log('✅ Face well positioned!');
                        if (faceGuide) {
                            faceGuide.classList.add('detected');
                        }
                        if (faceStatus) {
                            faceStatus.innerHTML = '<span class="status-text">Perfekt! Bereit für Aufnahme</span>';
                        }
                        if (captureButton) {
                            captureButton.disabled = false;
                        }
                    } else {
                        // Face needs adjustment
                        console.log('⚠️ Face needs adjustment');
                        if (faceGuide) {
                            faceGuide.classList.remove('detected');
                        }
                        
                        let message = 'Position anpassen';
                        if (!isGoodSize) {
                            if (faceWidthRatio < 0.12) {
                                message = 'Bitte näher kommen';
                            } else {
                                message = 'Bitte weiter weg';
                            }
                        } else if (!isCentered) {
                            message = 'Gesicht zentrieren';
                        }
                        
                        if (faceStatus) {
                            faceStatus.innerHTML = `<span class="status-text">${message}</span>`;
                        }
                        if (captureButton) {
                            captureButton.disabled = true;
                        }
                    }
                } else {
                    // No face detected
                    console.log('❌ No face detected');
                    if (faceGuide) {
                        faceGuide.classList.remove('detected');
                    }
                    if (faceStatus) {
                        faceStatus.innerHTML = '<span class="status-text">Kein Gesicht erkannt</span>';
                    }
                    if (captureButton) {
                        captureButton.disabled = true;
                    }
                }
            } catch (error) {
                console.error('Face detection error:', error);
                // Enable capture button as fallback
                if (captureButton) {
                    captureButton.disabled = false;
                }
            }
        }
        
        // Continue detection loop
        if (this.currentStream) {
            setTimeout(() => this.detectFaces(), 100); // Run every 100ms instead of every frame
        }
    }
    
    async switchCamera() {
        // Stop current stream
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
        }
        
        // Switch facing mode
        const newFacingMode = this.currentFacingMode === 'user' ? 'environment' : 'user';
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1080 },
                    height: { ideal: 1920 },
                    aspectRatio: { ideal: 9/16 },
                    facingMode: newFacingMode
                }
            });
            
            const video = document.getElementById('cameraStream');
            if (video) {
                video.srcObject = stream;
                this.currentStream = stream;
                this.currentFacingMode = newFacingMode;
                
                // Apply mirroring only for front camera
                if (newFacingMode === 'user') {
                    video.style.transform = 'scaleX(-1)';
                } else {
                    video.style.transform = 'scaleX(1)';
                }
            }
        } catch (error) {
            console.error('Error switching camera:', error);
            // Try to restart with current camera
            this.initializeCamera();
        }
    }
    
    capturePhoto() {
        const video = document.getElementById('cameraStream');
        const canvas = document.getElementById('cameraCanvas');
        
        if (video && canvas) {
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            // Handle mirroring for front camera captures
            if (this.currentFacingMode === 'user') {
                context.save();
                context.scale(-1, 1);
                context.drawImage(video, -canvas.width, 0);
                context.restore();
            } else {
                context.drawImage(video, 0, 0);
            }
            
            // Convert to base64
            const imageData = canvas.toDataURL('image/jpeg', 0.9);
            this.currentImageBase64 = imageData;
            
            // Create image object
            this.currentImage = new Image();
            this.currentImage.src = imageData;
            
            // Close camera and proceed
            this.closeCamera();
            
            // Skip upload section and go directly to result
            setTimeout(() => {
                this.showSection('resultSection');
                this.setupResultView();
            }, 500);
        }
    }
    
    closeCamera() {
        // Stop camera stream
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
        }
        
        // Stop face detection
        this.faceDetector = null;
        
        // Hide camera view
        const cameraView = document.getElementById('cameraView');
        if (cameraView) {
            cameraView.style.display = 'none';
        }
    }
    
    switchCamera() {
        // Toggle between front and back camera
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
        }
        
        const currentFacingMode = this.facingMode === 'user' ? 'environment' : 'user';
        this.facingMode = currentFacingMode;
        
        navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: currentFacingMode
            }
        }).then(stream => {
            const video = document.getElementById('cameraStream');
            if (video) {
                video.srcObject = stream;
                this.currentStream = stream;
            }
        }).catch(error => {
            console.error('Camera switch error:', error);
        });
    }
    
    // Show unified view system after successful generation
    showUnifiedViewSystem() {
        const unifiedViewToggle = document.getElementById('unifiedViewToggle');
        const unifiedViewContainer = document.getElementById('unifiedViewContainer');
        const downloadBtn = document.getElementById('downloadBtn');
        
        if (unifiedViewToggle) {
            unifiedViewToggle.style.display = 'flex';
            gsap.fromTo(unifiedViewToggle,
                { opacity: 0, y: 20 },
                { opacity: 1, y: 0, duration: 0.5, delay: 0.3 }
            );
        }
        
        if (unifiedViewContainer) {
            unifiedViewContainer.style.display = 'block';
            gsap.fromTo(unifiedViewContainer,
                { opacity: 0, y: 20 },
                { opacity: 1, y: 0, duration: 0.5, delay: 0.5 }
            );
        }
        
        if (downloadBtn) {
            downloadBtn.style.display = 'flex';
            gsap.fromTo(downloadBtn,
                { opacity: 0, scale: 0.8 },
                { opacity: 1, scale: 1, duration: 0.3, delay: 0.7 }
            );
        }
        
        // Show Medical AI Assistant after successful generation
        setTimeout(() => {
            if (window.medicalAssistant && window.medicalAssistant.assistantWidget) {
                window.medicalAssistant.assistantWidget.show();
                console.log('🏥 Medical Assistant widget shown after generation');
            } else {
                console.log('⚠️ Medical Assistant not available to show');
            }
        }, 1000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NuvaFaceApp();
});