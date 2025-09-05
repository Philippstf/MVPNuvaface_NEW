/**
 * Medical Overlay Renderer
 * Renders risk zones and injection points on the BEFORE image
 */

class MedicalOverlayRenderer {
    constructor() {
        this.canvas = null;
        this.ctx = null;
        this.currentData = null;
        this.beforeImage = null;
        this.isInitialized = false;
        
        // Visualization settings
        this.settings = {
            showRiskZones: false,
            showInjectionPoints: false,
            animateOverlays: true,
            opacity: {
                riskZones: 0.3,
                injectionPoints: 1.0
            }
        };
        
        // Colors for different severity levels
        this.colors = {
            high: '#FF4D4D',
            moderate: '#FFA500',
            low: '#FFFF99',
            safe: '#90EE90'
        };
    }
    
    /**
     * Initialize the overlay canvas
     */
    initialize() {
        // Find the before image
        this.beforeImage = document.getElementById('beforeImage') || 
                          document.getElementById('beforeImageSideBySide');
        
        if (!this.beforeImage) {
            console.error('Before image not found');
            return false;
        }
        
        // Create or get existing overlay canvas
        this.createCanvas();
        this.positionCanvas();
        this.isInitialized = true;
        
        // Listen for window resize
        window.addEventListener('resize', () => this.positionCanvas());
        
        return true;
    }
    
    /**
     * Create the overlay canvas
     */
    createCanvas() {
        // Remove existing canvas if present
        const existingCanvas = document.getElementById('medicalOverlayCanvas');
        if (existingCanvas) {
            existingCanvas.remove();
        }
        
        // Create new canvas
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'medicalOverlayCanvas';
        this.canvas.style.position = 'absolute';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '1000';
        
        // Insert canvas after the before image
        this.beforeImage.parentElement.style.position = 'relative';
        this.beforeImage.parentElement.appendChild(this.canvas);
        
        this.ctx = this.canvas.getContext('2d');
    }
    
    /**
     * Position and size the canvas to match the before image
     */
    positionCanvas() {
        if (!this.canvas || !this.beforeImage) return;
        
        const rect = this.beforeImage.getBoundingClientRect();
        const parentRect = this.beforeImage.parentElement.getBoundingClientRect();
        
        // Set canvas size to match image
        this.canvas.width = this.beforeImage.naturalWidth || this.beforeImage.width;
        this.canvas.height = this.beforeImage.naturalHeight || this.beforeImage.height;
        
        // Position canvas over image
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.canvas.style.left = (rect.left - parentRect.left) + 'px';
        this.canvas.style.top = (rect.top - parentRect.top) + 'px';
        
        // Redraw if we have data
        if (this.currentData) {
            this.render(this.currentData);
        }
    }
    
    /**
     * Update settings and re-render
     */
    updateSettings(settings) {
        this.settings = { ...this.settings, ...settings };
        if (this.currentData) {
            this.render(this.currentData);
        }
    }
    
    /**
     * Main render function
     */
    render(analysisData) {
        if (!this.isInitialized) {
            if (!this.initialize()) {
                console.error('Failed to initialize overlay renderer');
                return;
            }
        }
        
        this.currentData = analysisData;
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Calculate scale factor (API coordinates to canvas coordinates)
        const scaleX = this.canvas.width / (analysisData.imageSize?.w || this.canvas.width);
        const scaleY = this.canvas.height / (analysisData.imageSize?.h || this.canvas.height);
        
        // Render risk zones first (behind injection points)
        if (this.settings.showRiskZones && analysisData.risk_zones) {
            this.renderRiskZones(analysisData.risk_zones, scaleX, scaleY);
        }
        
        // Render injection points on top
        if (this.settings.showInjectionPoints && analysisData.injection_points) {
            this.renderInjectionPoints(analysisData.injection_points, scaleX, scaleY);
        }
    }
    
    /**
     * Render risk zones as semi-transparent polygons
     */
    renderRiskZones(zones, scaleX, scaleY) {
        zones.forEach(zone => {
            const color = this.colors[zone.severity] || this.colors.moderate;
            
            this.ctx.save();
            this.ctx.globalAlpha = zone.opacity || this.settings.opacity.riskZones;
            
            // Draw polygon
            if (zone.polygon && zone.polygon.length > 0) {
                this.ctx.beginPath();
                zone.polygon.forEach((point, idx) => {
                    const x = point[0] * scaleX;
                    const y = point[1] * scaleY;
                    if (idx === 0) {
                        this.ctx.moveTo(x, y);
                    } else {
                        this.ctx.lineTo(x, y);
                    }
                });
                this.ctx.closePath();
                
                // Fill
                this.ctx.fillStyle = color;
                this.ctx.fill();
                
                // Stroke with dashed/dotted style if specified
                if (zone.style?.includes('dashed')) {
                    this.ctx.setLineDash([5, 5]);
                } else if (zone.style?.includes('dotted')) {
                    this.ctx.setLineDash([2, 2]);
                }
                
                this.ctx.strokeStyle = color;
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
                this.ctx.setLineDash([]);
            }
            
            // Draw circle if specified
            if (zone.circle) {
                const x = zone.circle.x * scaleX;
                const y = zone.circle.y * scaleY;
                const radius = zone.circle.radius * Math.min(scaleX, scaleY);
                
                this.ctx.beginPath();
                this.ctx.arc(x, y, radius, 0, Math.PI * 2);
                this.ctx.fillStyle = color;
                this.ctx.fill();
                this.ctx.strokeStyle = color;
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
            }
            
            this.ctx.restore();
        });
    }
    
    /**
     * Render injection points as markers with labels
     */
    renderInjectionPoints(points, scaleX, scaleY) {
        points.forEach(point => {
            const x = point.x * scaleX;
            const y = point.y * scaleY;
            
            this.ctx.save();
            this.ctx.globalAlpha = this.settings.opacity.injectionPoints;
            
            // Draw point marker
            this.ctx.beginPath();
            this.ctx.arc(x, y, 6, 0, Math.PI * 2);
            
            // Color based on depth
            const depthColors = {
                'dermal': '#4CAF50',
                'subcutaneous': '#2196F3',
                'supraperiostal': '#9C27B0'
            };
            const color = depthColors[point.depth] || '#4CAF50';
            
            this.ctx.fillStyle = color;
            this.ctx.fill();
            this.ctx.strokeStyle = '#FFFFFF';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            // Draw MD code label
            if (point.code) {
                this.ctx.font = 'bold 10px Arial';
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText(point.code, x, y);
            }
            
            // Draw connecting line for threading technique
            if (point.technique === 'linear threading' && point.thread_to) {
                const toX = point.thread_to.x * scaleX;
                const toY = point.thread_to.y * scaleY;
                
                this.ctx.beginPath();
                this.ctx.moveTo(x, y);
                this.ctx.lineTo(toX, toY);
                this.ctx.strokeStyle = color;
                this.ctx.lineWidth = 1;
                this.ctx.setLineDash([3, 3]);
                this.ctx.stroke();
                this.ctx.setLineDash([]);
            }
            
            // Draw volume indicator
            if (point.volume) {
                this.ctx.font = '9px Arial';
                this.ctx.fillStyle = '#333333';
                this.ctx.textAlign = 'center';
                this.ctx.fillText(point.volume, x, y + 15);
            }
            
            this.ctx.restore();
        });
    }
    
    /**
     * Clear all overlays
     */
    clear() {
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }
    
    /**
     * Destroy the renderer and clean up
     */
    destroy() {
        this.clear();
        if (this.canvas) {
            this.canvas.remove();
        }
        this.canvas = null;
        this.ctx = null;
        this.currentData = null;
        this.isInitialized = false;
    }
}

// Export for use
window.MedicalOverlayRenderer = MedicalOverlayRenderer;