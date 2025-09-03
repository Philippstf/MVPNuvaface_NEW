/**
 * Medical Overlay System for NuvaFace
 * 
 * Renders risk zones and injection points on 2D images using Canvas API
 * with smooth animations and medical-grade precision.
 */

class MedicalOverlayRenderer {
    constructor(imageElement, canvasElement) {
        this.image = imageElement;
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        
        // Current overlay data
        this.riskZones = [];
        this.injectionPoints = [];
        this.scaleFactor = { x: 1, y: 1 };
        
        // Animation state
        this.animationId = null;
        this.fadeAnimation = null;
        
        // Mouse interaction
        this.hoveredElement = null;
        this.selectedElement = null;
        
        // Configuration
        this.config = {
            riskZones: {
                defaultColor: '#FF4D4D',
                defaultOpacity: 0.25,
                strokeWidth: 2,
                hoverOpacity: 0.4
            },
            injectionPoints: {
                radius: 6,
                color: '#FFFFFF',
                glowColor: '#4A90E2',
                glowRadius: 10,
                hoverRadius: 8
            },
            animation: {
                fadeInDuration: 500,
                fadeOutDuration: 300,
                hoverTransition: 150
            }
        };
        
        this.setupEventListeners();
        this.updateScaleFactor();
        
        console.log('🎨 Medical Overlay Renderer initialized');
    }
    
    setupEventListeners() {
        // Mouse events for interactivity
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('click', this.handleClick.bind(this));
        this.canvas.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
        
        // Resize observer to update scale factor
        if (window.ResizeObserver) {
            const resizeObserver = new ResizeObserver(() => {
                this.updateScaleFactor();
                this.redraw();
            });
            resizeObserver.observe(this.image);
            resizeObserver.observe(this.canvas);
        }
        
        // Window resize fallback
        window.addEventListener('resize', () => {
            setTimeout(() => {
                this.updateScaleFactor();
                this.redraw();
            }, 100);
        });
    }
    
    updateScaleFactor() {
        if (!this.image.naturalWidth || !this.image.naturalHeight) return;
        
        const imageRect = this.image.getBoundingClientRect();
        const canvasRect = this.canvas.getBoundingClientRect();
        
        // Update canvas size to match image display size
        this.canvas.width = imageRect.width;
        this.canvas.height = imageRect.height;
        
        // Calculate scale factors
        this.scaleFactor = {
            x: imageRect.width / this.image.naturalWidth,
            y: imageRect.height / this.image.naturalHeight
        };
        
        console.log(`📐 Scale factor updated: ${this.scaleFactor.x.toFixed(3)}x, ${this.scaleFactor.y.toFixed(3)}y`);
    }
    
    async renderOverlays(riskZones = [], injectionPoints = [], modes = { riskZones: true, injectionPoints: true }) {
        console.log(`🎨 Rendering overlays: ${riskZones.length} zones, ${injectionPoints.length} points`);
        
        // Store overlay data
        this.riskZones = riskZones || [];
        this.injectionPoints = injectionPoints || [];
        
        // Clear canvas
        this.clearCanvas();
        
        // Animate in the overlays
        await this.animateOverlaysIn(modes);
    }
    
    async animateOverlaysIn(modes) {
        return new Promise((resolve) => {
            const startTime = Date.now();
            const duration = this.config.animation.fadeInDuration;
            
            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function (ease-out)
                const eased = 1 - Math.pow(1 - progress, 3);
                
                this.clearCanvas();
                
                // Render with animated opacity
                if (modes.riskZones && this.riskZones.length > 0) {
                    this.renderRiskZones(eased);
                }
                
                if (modes.injectionPoints && this.injectionPoints.length > 0) {
                    this.renderInjectionPoints(eased);
                }
                
                if (progress < 1) {
                    this.animationId = requestAnimationFrame(animate);
                } else {
                    resolve();
                }
            };
            
            animate();
        });
    }
    
    renderRiskZones(opacity = 1) {
        this.riskZones.forEach((zone, index) => {
            this.drawRiskZone(zone, opacity, index);
        });
    }
    
    drawRiskZone(zone, globalOpacity = 1, zoneIndex = 0) {
        if (!zone.polygon || zone.polygon.length < 3) return;
        
        const ctx = this.ctx;
        const isHovered = this.hoveredElement?.type === 'riskZone' && this.hoveredElement?.index === zoneIndex;
        
        // Calculate final opacity
        const baseOpacity = zone.opacity || this.config.riskZones.defaultOpacity;
        const finalOpacity = isHovered ? 
            this.config.riskZones.hoverOpacity : 
            baseOpacity * globalOpacity;
        
        // Get color
        const color = zone.color || this.config.riskZones.defaultColor;
        const rgbaColor = this.hexToRgba(color, finalOpacity);
        
        ctx.save();
        
        // Draw filled polygon
        ctx.beginPath();
        const scaledPolygon = this.scalePolygon(zone.polygon);
        
        ctx.moveTo(scaledPolygon[0].x, scaledPolygon[0].y);
        for (let i = 1; i < scaledPolygon.length; i++) {
            ctx.lineTo(scaledPolygon[i].x, scaledPolygon[i].y);
        }
        ctx.closePath();
        
        // Fill
        ctx.fillStyle = rgbaColor;
        ctx.fill();
        
        // Stroke
        ctx.strokeStyle = this.hexToRgba(color, Math.min(finalOpacity * 2, 1));
        ctx.lineWidth = this.config.riskZones.strokeWidth;
        
        // Apply stroke style
        if (zone.style?.stroke_style === 'dashed') {
            ctx.setLineDash([5, 5]);
        } else if (zone.style?.stroke_style === 'dotted') {
            ctx.setLineDash([2, 3]);
        } else if (zone.style?.stroke_style === 'hatched') {
            // Add hatching pattern
            this.addHatchingPattern(ctx, scaledPolygon, color, finalOpacity);
        }
        
        ctx.stroke();
        
        // Draw severity indicator
        if (zone.severity && isHovered) {
            this.drawSeverityIndicator(ctx, scaledPolygon, zone.severity);
        }
        
        ctx.restore();
    }
    
    renderInjectionPoints(opacity = 1) {
        this.injectionPoints.forEach((point, index) => {
            this.drawInjectionPoint(point, opacity, index);
        });
    }
    
    drawInjectionPoint(point, globalOpacity = 1, pointIndex = 0) {
        const ctx = this.ctx;
        const scaledPos = this.scalePoint(point.position);
        const isHovered = this.hoveredElement?.type === 'injectionPoint' && this.hoveredElement?.index === pointIndex;
        const isSelected = this.selectedElement?.type === 'injectionPoint' && this.selectedElement?.index === pointIndex;
        
        // Calculate radius
        const baseRadius = this.config.injectionPoints.radius;
        const radius = isHovered ? this.config.injectionPoints.hoverRadius : baseRadius;
        
        ctx.save();
        
        // Draw glow effect
        if (globalOpacity > 0.5) {
            const glowRadius = this.config.injectionPoints.glowRadius;
            const gradient = ctx.createRadialGradient(
                scaledPos.x, scaledPos.y, 0,
                scaledPos.x, scaledPos.y, glowRadius
            );
            
            const glowOpacity = (isHovered ? 0.6 : 0.3) * globalOpacity;
            gradient.addColorStop(0, this.hexToRgba(this.config.injectionPoints.glowColor, glowOpacity));
            gradient.addColorStop(1, this.hexToRgba(this.config.injectionPoints.glowColor, 0));
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(scaledPos.x, scaledPos.y, glowRadius, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Draw main point
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetY = 2;
        
        ctx.fillStyle = this.hexToRgba(this.config.injectionPoints.color, globalOpacity);
        ctx.beginPath();
        ctx.arc(scaledPos.x, scaledPos.y, radius, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw outer ring
        ctx.shadowColor = 'transparent';
        ctx.strokeStyle = this.hexToRgba(this.config.injectionPoints.glowColor, globalOpacity * 0.8);
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // Draw MD Code if available
        if (point.code && (isHovered || isSelected)) {
            this.drawMDCodeLabel(ctx, scaledPos, point.code, globalOpacity);
        }
        
        // Draw confidence indicator
        if (point.confidence !== undefined && point.confidence < 0.8) {
            this.drawConfidenceIndicator(ctx, scaledPos, point.confidence, globalOpacity);
        }
        
        ctx.restore();
    }
    
    drawMDCodeLabel(ctx, position, code, opacity) {
        ctx.save();
        
        const fontSize = 12;
        ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        
        // Background
        const textWidth = ctx.measureText(code).width;
        const padding = 4;
        const labelY = position.y - 15;
        
        ctx.fillStyle = this.hexToRgba('#000000', 0.7 * opacity);
        ctx.fillRect(
            position.x - textWidth/2 - padding, 
            labelY - fontSize - padding,
            textWidth + padding * 2,
            fontSize + padding * 2
        );
        
        // Text
        ctx.fillStyle = this.hexToRgba('#FFFFFF', opacity);
        ctx.fillText(code, position.x, labelY);
        
        ctx.restore();
    }
    
    drawConfidenceIndicator(ctx, position, confidence, opacity) {
        ctx.save();
        
        const indicatorSize = 8;
        const x = position.x + 12;
        const y = position.y - 12;
        
        // Background circle
        ctx.fillStyle = this.hexToRgba('#FFA500', 0.8 * opacity);
        ctx.beginPath();
        ctx.arc(x, y, indicatorSize/2, 0, Math.PI * 2);
        ctx.fill();
        
        // Confidence arc
        const startAngle = -Math.PI/2;
        const endAngle = startAngle + (confidence * 2 * Math.PI);
        
        ctx.strokeStyle = this.hexToRgba('#FFFFFF', opacity);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, indicatorSize/2 - 1, startAngle, endAngle);
        ctx.stroke();
        
        ctx.restore();
    }
    
    drawSeverityIndicator(ctx, polygon, severity) {
        const severityColors = {
            'low': '#FFFF99',
            'moderate': '#FFA500', 
            'high': '#FF4D4D',
            'critical': '#DC143C'
        };
        
        const color = severityColors[severity] || severityColors['moderate'];
        const center = this.getPolygonCenter(polygon);
        
        ctx.save();
        
        // Draw severity badge
        const badgeRadius = 12;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(center.x, center.y, badgeRadius, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw severity text
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(severity.charAt(0).toUpperCase(), center.x, center.y);
        
        ctx.restore();
    }
    
    addHatchingPattern(ctx, polygon, color, opacity) {
        const spacing = 8;
        const angle = Math.PI / 4; // 45 degrees
        
        ctx.save();
        
        // Create clipping path
        ctx.beginPath();
        ctx.moveTo(polygon[0].x, polygon[0].y);
        for (let i = 1; i < polygon.length; i++) {
            ctx.lineTo(polygon[i].x, polygon[i].y);
        }
        ctx.closePath();
        ctx.clip();
        
        // Get bounding box
        const bbox = this.getPolygonBoundingBox(polygon);
        const diagonal = Math.sqrt(bbox.width * bbox.width + bbox.height * bbox.height);
        
        // Draw hatching lines
        ctx.strokeStyle = this.hexToRgba(color, opacity * 0.6);
        ctx.lineWidth = 1;
        
        for (let i = -diagonal; i < diagonal; i += spacing) {
            const startX = bbox.x + i;
            const startY = bbox.y;
            const endX = bbox.x + i + bbox.height * Math.tan(angle);
            const endY = bbox.y + bbox.height;
            
            ctx.beginPath();
            ctx.moveTo(startX, startY);
            ctx.lineTo(endX, endY);
            ctx.stroke();
        }
        
        ctx.restore();
    }
    
    // Mouse interaction handlers
    handleMouseMove(event) {
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        
        const hoveredElement = this.findElementAtPosition(mouseX, mouseY);
        
        if (hoveredElement !== this.hoveredElement) {
            this.hoveredElement = hoveredElement;
            
            // Update cursor
            this.canvas.style.cursor = hoveredElement ? 'pointer' : 'default';
            
            // Trigger hover events
            if (hoveredElement) {
                this.onElementHover?.(hoveredElement);
            } else {
                this.onElementHoverOut?.();
            }
            
            // Redraw with hover effects
            this.redraw();
        }
    }
    
    handleClick(event) {
        if (this.hoveredElement) {
            this.selectedElement = this.hoveredElement;
            this.onElementClick?.(this.hoveredElement);
            this.redraw();
        }
    }
    
    handleMouseLeave() {
        if (this.hoveredElement) {
            this.hoveredElement = null;
            this.canvas.style.cursor = 'default';
            this.onElementHoverOut?.();
            this.redraw();
        }
    }
    
    findElementAtPosition(x, y) {
        // Check injection points first (they're on top)
        for (let i = this.injectionPoints.length - 1; i >= 0; i--) {
            const point = this.injectionPoints[i];
            const scaledPos = this.scalePoint(point.position);
            const distance = Math.sqrt(
                Math.pow(x - scaledPos.x, 2) + Math.pow(y - scaledPos.y, 2)
            );
            
            if (distance <= this.config.injectionPoints.hoverRadius) {
                return { type: 'injectionPoint', index: i, data: point };
            }
        }
        
        // Check risk zones
        for (let i = this.riskZones.length - 1; i >= 0; i--) {
            const zone = this.riskZones[i];
            if (this.isPointInPolygon({ x, y }, this.scalePolygon(zone.polygon))) {
                return { type: 'riskZone', index: i, data: zone };
            }
        }
        
        return null;
    }
    
    // Utility methods
    scalePoint(point) {
        return {
            x: point.x * this.scaleFactor.x,
            y: point.y * this.scaleFactor.y
        };
    }
    
    scalePolygon(polygon) {
        return polygon.map(point => this.scalePoint(point));
    }
    
    hexToRgba(hex, alpha = 1) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        if (result) {
            const r = parseInt(result[1], 16);
            const g = parseInt(result[2], 16);
            const b = parseInt(result[3], 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return `rgba(255, 77, 77, ${alpha})`; // Fallback color
    }
    
    isPointInPolygon(point, polygon) {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i].x, yi = polygon[i].y;
            const xj = polygon[j].x, yj = polygon[j].y;
            
            if (((yi > point.y) !== (yj > point.y)) && 
                (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }
        return inside;
    }
    
    getPolygonCenter(polygon) {
        let x = 0, y = 0;
        for (const point of polygon) {
            x += point.x;
            y += point.y;
        }
        return { x: x / polygon.length, y: y / polygon.length };
    }
    
    getPolygonBoundingBox(polygon) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const point of polygon) {
            minX = Math.min(minX, point.x);
            minY = Math.min(minY, point.y);
            maxX = Math.max(maxX, point.x);
            maxY = Math.max(maxY, point.y);
        }
        return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
    }
    
    clearCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    redraw() {
        this.clearCanvas();
        this.renderRiskZones();
        this.renderInjectionPoints();
    }
    
    // Public API for event callbacks
    onElementHover = null;
    onElementClick = null;
    onElementHoverOut = null;
    
    // Cleanup
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.clearCanvas();
        console.log('🗑️ Medical Overlay Renderer destroyed');
    }
}