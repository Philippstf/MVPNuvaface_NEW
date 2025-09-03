/**
 * Medical AI Assistant Integration
 * 
 * Main integration file that connects all medical assistant components
 * and provides the complete functionality for NuvaFace.
 */

class MedicalAssistantIntegration {
    constructor() {
        this.overlayRenderer = null;
        this.assistantWidget = null;
        this.tooltipSystem = null;
        
        // State management
        this.currentArea = null;
        this.currentImage = null;
        this.isInitialized = false;
        
        // Configuration
        this.config = {
            apiEndpoint: 'https://nuvaface-medical-assistant-212268956806.us-central1.run.app/api/risk-map/analyze',
            enableTooltips: true,
            enableWidget: true,
            autoAnalyzeOnImageChange: true,
            debugMode: true // Enable for debugging
        };
        
        this.init();
    }
    
    async init() {
        try {
            console.log('🏥 Initializing Medical AI Assistant Integration...');
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
            }
            
            // Initialize components
            await this.initializeComponents();
            
            // Setup integrations
            this.setupIntegrations();
            
            // Attach to existing NuvaFace app
            this.integrateWithNuvaFace();
            
            this.isInitialized = true;
            console.log('✅ Medical AI Assistant Integration initialized successfully');
            
        } catch (error) {
            console.error('❌ Medical AI Assistant initialization failed:', error);
            this.handleInitializationError(error);
        }
    }
    
    async initializeComponents() {
        // Initialize tooltip system
        if (this.config.enableTooltips) {
            this.tooltipSystem = new MedicalTooltipSystem();
            console.log('💬 Tooltip system initialized');
        }
        
        // Initialize assistant widget
        if (this.config.enableWidget) {
            this.assistantWidget = new MedicalAssistantWidget();
            console.log('🔧 Assistant widget initialized');
        }
        
        // Initialize overlay renderer (will be setup when image is ready)
        this.setupOverlayRenderer();
    }
    
    setupOverlayRenderer() {
        // Find the image and create canvas for overlays
        const imageElement = this.findMainImage();
        if (!imageElement) {
            console.warn('⚠️ Main image not found, overlay renderer will be initialized later');
            return;
        }
        
        // Create overlay canvas
        const canvas = this.createOverlayCanvas(imageElement);
        
        // Initialize overlay renderer
        this.overlayRenderer = new MedicalOverlayRenderer(imageElement, canvas);
        console.log('🎨 Overlay renderer initialized');
    }
    
    findMainImage() {
        // NEW: Focus on before image for medical overlays
        const beforeImg = document.querySelector('#beforeImage');
        if (beforeImg && beforeImg.src && beforeImg.offsetWidth > 0) {
            console.log('🎯 Using beforeImage for medical overlays');
            return beforeImg;
        }
        
        // Fallback to other selectors
        const selectors = [
            '#previewImage', 
            '.result-image',
            'img[id*="before"]',
            'img[id*="result"]',
            '.image-panel img'
        ];
        
        for (const selector of selectors) {
            const img = document.querySelector(selector);
            if (img && img.src && img.offsetWidth > 0) {
                console.log(`🎯 Using ${selector} for medical overlays`);
                return img;
            }
        }
        
        console.warn('⚠️ No suitable image found for medical overlays');
        return null;
    }
    
    createOverlayCanvas(imageElement) {
        // Check if canvas already exists
        let canvas = document.querySelector('.medical-overlay-canvas');
        if (canvas) return canvas;
        
        // Create new canvas
        canvas = document.createElement('canvas');
        canvas.className = 'medical-overlay-canvas';
        canvas.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: auto;
            z-index: 10;
        `;
        
        // Find container for the image
        const container = imageElement.parentElement;
        
        // Make container relative if needed
        const containerStyle = window.getComputedStyle(container);
        if (containerStyle.position === 'static') {
            container.style.position = 'relative';
        }
        
        // Add canvas to container
        container.appendChild(canvas);
        
        return canvas;
    }
    
    setupIntegrations() {
        // Connect overlay renderer to tooltip system
        if (this.overlayRenderer && this.tooltipSystem) {
            this.overlayRenderer.onElementHover = (element) => {
                const rect = this.overlayRenderer.canvas.getBoundingClientRect();
                const x = rect.left + element.data.position?.x || 0;
                const y = rect.top + (element.data.position?.y || 0) - 10;
                
                this.tooltipSystem.showTooltipForElement(element, x, y, false);
            };
            
            this.overlayRenderer.onElementClick = (element) => {
                const rect = this.overlayRenderer.canvas.getBoundingClientRect();
                const x = rect.left + element.data.position?.x || 0;
                const y = rect.top + (element.data.position?.y || 0) - 10;
                
                this.tooltipSystem.showTooltipForElement(element, x, y, true);
            };
            
            this.overlayRenderer.onElementHoverOut = () => {
                this.tooltipSystem.scheduleHide();
            };
        }
        
        // Connect widget to overlay renderer
        if (this.assistantWidget && this.overlayRenderer) {
            this.assistantWidget.setOverlayRenderer(this.overlayRenderer);
        }
        
        // Setup API endpoint for widget
        if (this.assistantWidget) {
            this.assistantWidget.apiEndpoint = this.config.apiEndpoint;
        }
    }
    
    integrateWithNuvaFace() {
        // Hook into existing NuvaFace app if available
        if (window.app) {
            console.log('🔗 Integrating with existing NuvaFace app (non-invasive)');
            
            // DON'T override selectedArea - let index.html handle integration
            // Just monitor for changes through the existing property
            
            // Hook into image loading
            this.hookImageLoading();
            
            // Hook into section changes
            this.hookSectionChanges();
            
            // Monitor existing selectedArea periodically (fallback)
            this.monitorAreaSelection();
        }
        
        // Make medical assistant globally available
        window.medicalAssistant = this;
    }
    
    monitorAreaSelection() {
        // Fallback monitoring in case property enhancement doesn't work
        setInterval(() => {
            if (window.app && window.app.selectedArea !== this.currentArea) {
                const newArea = window.app.selectedArea;
                console.log(`🔄 Area change detected: ${this.currentArea} → ${newArea}`);
                this.setCurrentArea(newArea);
            }
        }, 1000);
    }
    
    hookImageLoading() {
        // Watch for image changes in the result section
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'src') {
                    const img = mutation.target;
                    if (img.tagName === 'IMG' && this.isMainImage(img)) {
                        this.handleImageChange(img);
                    }
                }
            });
        });
        
        // Observe image elements
        document.querySelectorAll('img').forEach(img => {
            observer.observe(img, { attributes: true, attributeFilter: ['src'] });
        });
        
        // Also watch for new images being added
        const documentObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const images = node.tagName === 'IMG' ? [node] : node.querySelectorAll('img');
                        images.forEach(img => {
                            observer.observe(img, { attributes: true, attributeFilter: ['src'] });
                            if (this.isMainImage(img) && img.src) {
                                this.handleImageChange(img);
                            }
                        });
                    }
                });
            });
        });
        
        documentObserver.observe(document.body, { childList: true, subtree: true });
    }
    
    isMainImage(img) {
        return img.id === 'beforeImage' || 
               img.classList.contains('result-image') ||
               img.closest('.image-panel');
    }
    
    async handleImageChange(img) {
        console.log('📸 Image change detected:', img.src ? 'loaded' : 'cleared');
        
        this.currentImage = img.src || null;
        
        // Reinitialize overlay renderer if needed
        if (img.src && (!this.overlayRenderer || this.overlayRenderer.image !== img)) {
            const canvas = this.createOverlayCanvas(img);
            this.overlayRenderer = new MedicalOverlayRenderer(img, canvas);
            this.setupIntegrations();
        }
        
        // Auto-analyze if enabled
        if (this.config.autoAnalyzeOnImageChange && this.currentImage && this.currentArea) {
            await this.delay(500); // Wait for image to render
            this.triggerAnalysis();
        }
        
        // Show/hide widget based on image presence AND current section
        if (this.assistantWidget) {
            const currentSection = document.querySelector('.section.active');
            const isResultSection = currentSection && currentSection.id === 'resultSection';
            
            if (this.currentImage && isResultSection) {
                console.log('🏥 Medical Assistant: Showing on result section with image');
                this.assistantWidget.show();
            } else {
                console.log('🏥 Medical Assistant: Hiding (not result section or no image)');
                this.assistantWidget.hide();
            }
        }
    }
    
    hookSectionChanges() {
        // Watch for section changes in NuvaFace app
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const element = mutation.target;
                    if (element.classList.contains('section') && element.classList.contains('active')) {
                        this.handleSectionChange(element.id);
                    }
                }
            });
        });
        
        document.querySelectorAll('.section').forEach(section => {
            observer.observe(section, { attributes: true, attributeFilter: ['class'] });
        });
    }
    
    handleSectionChange(sectionId) {
        console.log('📄 Section changed to:', sectionId);
        
        // STRICT: Show widget ONLY in result section
        if (this.assistantWidget) {
            if (sectionId === 'resultSection') {
                console.log('🏥 Medical Assistant: Showing on result section');
                this.assistantWidget.show();
                
                // Reinitialize overlay renderer for result section
                setTimeout(() => {
                    this.setupOverlayRenderer();
                    this.setupIntegrations();
                }, 100);
            } else {
                console.log('🏥 Medical Assistant: Hiding - not result section');
                this.assistantWidget.hide();
            }
        }
    }
    
    // Public API methods
    
    setCurrentArea(area) {
        console.log('🎯 Setting current area:', area);
        this.currentArea = area;
        
        if (this.assistantWidget) {
            this.assistantWidget.setCurrentArea(area);
        }
    }
    
    async triggerAnalysis(modes = null) {
        if (!this.assistantWidget) return;
        
        // Use current modes or default
        if (modes) {
            this.assistantWidget.modes = { ...this.assistantWidget.modes, ...modes };
            
            // Update UI toggles
            if (modes.riskZones !== undefined) {
                const toggle = document.getElementById('riskZonesToggle');
                if (toggle) toggle.checked = modes.riskZones;
            }
            if (modes.injectionPoints !== undefined) {
                const toggle = document.getElementById('injectionPointsToggle');
                if (toggle) toggle.checked = modes.injectionPoints;
            }
        }
        
        await this.assistantWidget.updateOverlays();
    }
    
    showRiskZones(show = true) {
        return this.triggerAnalysis({ riskZones: show });
    }
    
    showInjectionPoints(show = true) {
        return this.triggerAnalysis({ injectionPoints: show });
    }
    
    clearOverlays() {
        if (this.overlayRenderer) {
            this.overlayRenderer.renderOverlays([], [], { riskZones: false, injectionPoints: false });
        }
        
        if (this.tooltipSystem) {
            this.tooltipSystem.hide();
        }
    }
    
    // Demo and testing methods
    
    async runDemo() {
        console.log('🎬 Starting Medical AI Assistant demo...');
        
        if (!this.isInitialized) {
            console.warn('⚠️ System not initialized, cannot run demo');
            return;
        }
        
        // Demo sequence
        await this.demoSequence();
    }
    
    async demoSequence() {
        const steps = [
            {
                name: 'Show Widget',
                action: () => this.assistantWidget?.show(),
                delay: 1000
            },
            {
                name: 'Open Panel', 
                action: () => this.assistantWidget?.openPanel(),
                delay: 1500
            },
            {
                name: 'Enable Risk Zones',
                action: () => {
                    const toggle = document.getElementById('riskZonesToggle');
                    if (toggle) {
                        toggle.checked = true;
                        toggle.dispatchEvent(new Event('change'));
                    }
                },
                delay: 2000
            },
            {
                name: 'Enable Injection Points',
                action: () => {
                    const toggle = document.getElementById('injectionPointsToggle');
                    if (toggle) {
                        toggle.checked = true;
                        toggle.dispatchEvent(new Event('change'));
                    }
                },
                delay: 2000
            },
            {
                name: 'Simulate Analysis Complete',
                action: () => {
                    // Simulate successful analysis
                    if (this.assistantWidget) {
                        this.assistantWidget.updateConfidence(0.85);
                        this.assistantWidget.setAnalysisStatus('completed');
                    }
                },
                delay: 1000
            }
        ];
        
        for (const step of steps) {
            console.log(`🎬 Demo step: ${step.name}`);
            step.action();
            await this.delay(step.delay);
        }
        
        console.log('✅ Demo sequence completed');
    }
    
    // Configuration methods
    
    configure(options) {
        this.config = { ...this.config, ...options };
        
        if (options.apiEndpoint && this.assistantWidget) {
            this.assistantWidget.apiEndpoint = options.apiEndpoint;
        }
        
        console.log('⚙️ Configuration updated:', options);
    }
    
    enableDebugMode(enabled = true) {
        this.config.debugMode = enabled;
        
        if (enabled) {
            // Add debug styles and information
            this.addDebugStyles();
        }
        
        console.log(`🐛 Debug mode ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    addDebugStyles() {
        const style = document.createElement('style');
        style.id = 'medicalAssistantDebug';
        style.textContent = `
            .medical-overlay-canvas {
                border: 2px dashed #00ff00;
            }
            
            .medical-assistant-widget::after {
                content: 'DEBUG MODE';
                position: absolute;
                top: -8px;
                right: -8px;
                background: #ff0000;
                color: white;
                font-size: 8px;
                padding: 2px 4px;
                border-radius: 2px;
                font-weight: bold;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Error handling
    
    handleInitializationError(error) {
        console.error('Medical AI Assistant initialization failed:', error);
        
        // Show user-friendly error message
        this.showErrorNotification('Medical AI Assistant could not be initialized. Some features may be unavailable.');
        
        // Try to initialize in safe mode
        this.initializeSafeMode();
    }
    
    initializeSafeMode() {
        console.log('🔒 Initializing Medical AI Assistant in safe mode...');
        
        try {
            // Initialize minimal functionality
            this.config.enableTooltips = false;
            this.config.enableWidget = true;
            this.config.autoAnalyzeOnImageChange = false;
            
            // Basic widget only
            this.assistantWidget = new MedicalAssistantWidget();
            
            console.log('✅ Safe mode initialized');
            
        } catch (safeError) {
            console.error('❌ Safe mode initialization also failed:', safeError);
        }
    }
    
    showErrorNotification(message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fee2e2;
            border: 1px solid #fca5a5;
            color: #dc2626;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 10001;
            max-width: 300px;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 10000);
    }
    
    // Utility methods
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Cleanup
    
    destroy() {
        console.log('🗑️ Destroying Medical AI Assistant Integration...');
        
        if (this.overlayRenderer) {
            this.overlayRenderer.destroy();
        }
        
        if (this.assistantWidget) {
            this.assistantWidget.destroy();
        }
        
        if (this.tooltipSystem) {
            this.tooltipSystem.destroy();
        }
        
        // Remove debug styles
        const debugStyle = document.getElementById('medicalAssistantDebug');
        if (debugStyle) {
            debugStyle.remove();
        }
        
        // Clean up global reference
        delete window.medicalAssistant;
        
        console.log('✅ Medical AI Assistant Integration destroyed');
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait a moment for other scripts to load
    setTimeout(() => {
        if (!window.medicalAssistant) {
            window.medicalAssistant = new MedicalAssistantIntegration();
        }
    }, 1000);
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MedicalAssistantIntegration;
}