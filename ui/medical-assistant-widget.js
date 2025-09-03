/**
 * Medical AI Assistant Widget for NuvaFace
 * 
 * Floating widget for toggling medical overlays with professional UI
 * and comprehensive safety features.
 */

class MedicalAssistantWidget {
    constructor() {
        this.isOpen = false;
        this.currentArea = null;
        this.overlayRenderer = null;
        this.apiEndpoint = '/api/risk-map/analyze'; // Configure as needed
        
        // Widget state
        this.modes = {
            riskZones: false,
            injectionPoints: false
        };
        
        // Analysis state
        this.isAnalyzing = false;
        this.currentAnalysis = null;
        this.confidenceScore = 0;
        
        this.createWidget();
        this.attachEventListeners();
        
        console.log('🏥 Medical AI Assistant Widget initialized');
    }
    
    createWidget() {
        // Remove existing widget if any
        const existingWidget = document.getElementById('medicalAssistantWidget');
        if (existingWidget) {
            existingWidget.remove();
        }
        
        const widget = document.createElement('div');
        widget.id = 'medicalAssistantWidget';
        widget.className = 'medical-assistant-widget';
        
        widget.innerHTML = `
            <!-- Main Toggle Button -->
            <button class="assistant-toggle" id="assistantToggle">
                <div class="toggle-icon">
                    <i class="fas fa-stethoscope"></i>
                </div>
                <div class="toggle-text">
                    <span class="title">Medical AI Assistant</span>
                    <span class="subtitle">Analysis & Safety</span>
                </div>
                <div class="toggle-arrow">
                    <i class="fas fa-chevron-up"></i>
                </div>
            </button>
            
            <!-- Expanded Panel -->
            <div class="assistant-panel" id="assistantPanel">
                <div class="panel-header">
                    <h3>Treatment Analysis</h3>
                    <div class="panel-status" id="panelStatus">
                        <span class="status-indicator"></span>
                        <span class="status-text">Ready</span>
                    </div>
                </div>
                
                <div class="panel-content">
                    <!-- Analysis Controls -->
                    <div class="analysis-section">
                        <h4>Overlay Options</h4>
                        
                        <label class="toggle-option risk-zones">
                            <input type="checkbox" id="riskZonesToggle">
                            <div class="option-control">
                                <div class="checkbox-custom">
                                    <i class="fas fa-check"></i>
                                </div>
                                <div class="option-content">
                                    <span class="option-title">Risk Zones</span>
                                    <span class="option-description">Anatomical danger areas</span>
                                </div>
                            </div>
                            <div class="option-status">
                                <span class="status-badge danger">🚨</span>
                            </div>
                        </label>
                        
                        <label class="toggle-option injection-points">
                            <input type="checkbox" id="injectionPointsToggle">
                            <div class="option-control">
                                <div class="checkbox-custom">
                                    <i class="fas fa-check"></i>
                                </div>
                                <div class="option-content">
                                    <span class="option-title">Optimal Points</span>
                                    <span class="option-description">MD Code recommendations</span>
                                </div>
                            </div>
                            <div class="option-status">
                                <span class="status-badge success">💉</span>
                            </div>
                        </label>
                    </div>
                    
                    <!-- Analysis Status -->
                    <div class="analysis-status" id="analysisStatus">
                        <div class="status-content">
                            <div class="status-row">
                                <span class="status-label">Analysis Confidence:</span>
                                <div class="confidence-display">
                                    <div class="confidence-bar">
                                        <div class="confidence-fill" id="confidenceFill"></div>
                                    </div>
                                    <span class="confidence-value" id="confidenceValue">--</span>
                                </div>
                            </div>
                            
                            <div class="status-row">
                                <span class="status-label">Processing Time:</span>
                                <span class="processing-time" id="processingTime">--</span>
                            </div>
                            
                            <div class="status-row">
                                <span class="status-label">Current Area:</span>
                                <span class="current-area" id="currentArea">None selected</span>
                            </div>
                        </div>
                        
                        <div class="analysis-actions">
                            <button class="refresh-btn" id="refreshAnalysis" title="Refresh Analysis">
                                <i class="fas fa-sync"></i>
                            </button>
                            <button class="settings-btn" id="openSettings" title="Settings">
                                <i class="fas fa-cog"></i>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Loading Indicator -->
                    <div class="loading-section" id="loadingSection" style="display: none;">
                        <div class="loading-animation">
                            <div class="loading-spinner"></div>
                            <div class="loading-progress">
                                <div class="progress-bar">
                                    <div class="progress-fill" id="progressFill"></div>
                                </div>
                                <span class="progress-text" id="progressText">Analyzing facial landmarks...</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Legend -->
                    <div class="overlay-legend" id="overlayLegend" style="display: none;">
                        <h4>Legend</h4>
                        <div class="legend-items">
                            <div class="legend-item risk">
                                <div class="legend-color risk-high"></div>
                                <span>High Risk Zone</span>
                            </div>
                            <div class="legend-item risk">
                                <div class="legend-color risk-moderate"></div>
                                <span>Moderate Risk</span>
                            </div>
                            <div class="legend-item point">
                                <div class="legend-color point-optimal"></div>
                                <span>Optimal Injection Point</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Safety Disclaimer -->
                <div class="safety-disclaimer">
                    <div class="disclaimer-icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <div class="disclaimer-content">
                        <p><strong>Medical Professional Use Only</strong></p>
                        <p>This analysis is for trained medical professionals only. Not for patient consultation or treatment decisions.</p>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
        
        // Add CSS styles
        this.injectStyles();
    }
    
    injectStyles() {
        const styleId = 'medicalAssistantStyles';
        if (document.getElementById(styleId)) return;
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .medical-assistant-widget {
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .assistant-toggle {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 16px;
                padding: 16px 20px;
                color: white;
                cursor: pointer;
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 280px;
                backdrop-filter: blur(10px);
            }
            
            .assistant-toggle:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 35px rgba(0,0,0,0.2);
            }
            
            .toggle-icon i {
                font-size: 20px;
                color: #4ade80;
            }
            
            .toggle-text {
                flex: 1;
                text-align: left;
            }
            
            .toggle-text .title {
                display: block;
                font-weight: 600;
                font-size: 14px;
                margin-bottom: 2px;
            }
            
            .toggle-text .subtitle {
                display: block;
                font-size: 12px;
                opacity: 0.8;
            }
            
            .toggle-arrow {
                transition: transform 0.3s ease;
            }
            
            .assistant-toggle.open .toggle-arrow {
                transform: rotate(180deg);
            }
            
            .assistant-panel {
                position: absolute;
                bottom: calc(100% + 12px);
                right: 0;
                width: 380px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.15);
                border: 1px solid rgba(255,255,255,0.2);
                transform: translateY(20px) scale(0.95);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .assistant-panel.open {
                transform: translateY(0) scale(1);
                opacity: 1;
                visibility: visible;
            }
            
            .panel-header {
                padding: 20px 24px 16px;
                border-bottom: 1px solid rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .panel-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
                color: #1f2937;
            }
            
            .panel-status {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .status-indicator {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #10b981;
                animation: pulse 2s infinite;
            }
            
            .status-text {
                font-size: 12px;
                color: #6b7280;
                font-weight: 500;
            }
            
            .panel-content {
                padding: 20px 24px;
            }
            
            .analysis-section h4 {
                margin: 0 0 16px 0;
                font-size: 14px;
                font-weight: 600;
                color: #374151;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .toggle-option {
                display: flex;
                align-items: center;
                padding: 12px 0;
                cursor: pointer;
                transition: all 0.2s ease;
                border-radius: 12px;
                margin-bottom: 8px;
            }
            
            .toggle-option:hover {
                background: rgba(0,0,0,0.02);
                padding-left: 8px;
                padding-right: 8px;
            }
            
            .toggle-option input {
                display: none;
            }
            
            .option-control {
                display: flex;
                align-items: center;
                gap: 12px;
                flex: 1;
            }
            
            .checkbox-custom {
                width: 20px;
                height: 20px;
                border: 2px solid #d1d5db;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s ease;
            }
            
            .checkbox-custom i {
                font-size: 12px;
                color: white;
                opacity: 0;
                transition: opacity 0.2s ease;
            }
            
            .toggle-option input:checked + .option-control .checkbox-custom {
                background: #3b82f6;
                border-color: #3b82f6;
            }
            
            .toggle-option input:checked + .option-control .checkbox-custom i {
                opacity: 1;
            }
            
            .option-content {
                flex: 1;
            }
            
            .option-title {
                display: block;
                font-weight: 500;
                color: #1f2937;
                margin-bottom: 2px;
            }
            
            .option-description {
                display: block;
                font-size: 12px;
                color: #6b7280;
            }
            
            .option-status .status-badge {
                font-size: 16px;
            }
            
            .analysis-status {
                margin-top: 20px;
                padding: 16px;
                background: rgba(0,0,0,0.02);
                border-radius: 12px;
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
            }
            
            .status-content {
                flex: 1;
            }
            
            .status-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            
            .status-row:last-child {
                margin-bottom: 0;
            }
            
            .status-label {
                font-size: 12px;
                color: #6b7280;
                font-weight: 500;
            }
            
            .confidence-display {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .confidence-bar {
                width: 80px;
                height: 6px;
                background: #e5e7eb;
                border-radius: 3px;
                overflow: hidden;
            }
            
            .confidence-fill {
                height: 100%;
                background: linear-gradient(90deg, #ef4444, #f97316, #eab308, #22c55e);
                border-radius: 3px;
                width: 0%;
                transition: width 0.5s ease;
            }
            
            .confidence-value {
                font-size: 12px;
                font-weight: 600;
                color: #374151;
                min-width: 35px;
            }
            
            .processing-time, .current-area {
                font-size: 12px;
                color: #374151;
                font-weight: 500;
            }
            
            .analysis-actions {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .refresh-btn, .settings-btn {
                width: 32px;
                height: 32px;
                border: none;
                background: rgba(255,255,255,0.8);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
                color: #6b7280;
            }
            
            .refresh-btn:hover, .settings-btn:hover {
                background: #3b82f6;
                color: white;
                transform: scale(1.1);
            }
            
            .loading-section {
                text-align: center;
                padding: 20px;
            }
            
            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 3px solid #e5e7eb;
                border-top: 3px solid #3b82f6;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            }
            
            .progress-bar {
                width: 100%;
                height: 4px;
                background: #e5e7eb;
                border-radius: 2px;
                overflow: hidden;
                margin-bottom: 12px;
            }
            
            .progress-fill {
                height: 100%;
                background: #3b82f6;
                border-radius: 2px;
                width: 0%;
                transition: width 0.3s ease;
            }
            
            .progress-text {
                font-size: 12px;
                color: #6b7280;
            }
            
            .overlay-legend {
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid rgba(0,0,0,0.1);
            }
            
            .overlay-legend h4 {
                margin: 0 0 12px 0;
                font-size: 12px;
                font-weight: 600;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .legend-items {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            .legend-item {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12px;
                color: #374151;
            }
            
            .legend-color {
                width: 16px;
                height: 16px;
                border-radius: 4px;
            }
            
            .legend-color.risk-high {
                background: #ef4444;
            }
            
            .legend-color.risk-moderate {
                background: #f97316;
            }
            
            .legend-color.point-optimal {
                background: #3b82f6;
                border-radius: 50%;
            }
            
            .safety-disclaimer {
                padding: 16px 24px 20px;
                border-top: 1px solid rgba(239, 68, 68, 0.2);
                background: rgba(239, 68, 68, 0.02);
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
                display: flex;
                gap: 12px;
            }
            
            .disclaimer-icon {
                color: #ef4444;
                font-size: 16px;
                margin-top: 2px;
            }
            
            .disclaimer-content p {
                margin: 0 0 6px 0;
                font-size: 11px;
                line-height: 1.4;
            }
            
            .disclaimer-content p:first-child {
                font-weight: 600;
                color: #dc2626;
            }
            
            .disclaimer-content p:last-child {
                color: #6b7280;
                margin-bottom: 0;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Mobile responsiveness */
            @media (max-width: 480px) {
                .medical-assistant-widget {
                    bottom: 16px;
                    right: 16px;
                }
                
                .assistant-toggle {
                    min-width: 240px;
                    padding: 12px 16px;
                }
                
                .assistant-panel {
                    width: calc(100vw - 32px);
                    right: 0;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    attachEventListeners() {
        // Main toggle button
        const toggleBtn = document.getElementById('assistantToggle');
        toggleBtn.addEventListener('click', () => this.togglePanel());
        
        // Mode toggles
        const riskZonesToggle = document.getElementById('riskZonesToggle');
        const injectionPointsToggle = document.getElementById('injectionPointsToggle');
        
        riskZonesToggle.addEventListener('change', (e) => {
            this.modes.riskZones = e.target.checked;
            this.updateOverlays();
        });
        
        injectionPointsToggle.addEventListener('change', (e) => {
            this.modes.injectionPoints = e.target.checked;
            this.updateOverlays();
        });
        
        // Action buttons
        const refreshBtn = document.getElementById('refreshAnalysis');
        const settingsBtn = document.getElementById('openSettings');
        
        refreshBtn.addEventListener('click', () => this.refreshAnalysis());
        settingsBtn.addEventListener('click', () => this.openSettings());
        
        // Close panel when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.medical-assistant-widget') && this.isOpen) {
                this.closePanel();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closePanel();
            }
        });
    }
    
    togglePanel() {
        if (this.isOpen) {
            this.closePanel();
        } else {
            this.openPanel();
        }
    }
    
    openPanel() {
        this.isOpen = true;
        const toggle = document.getElementById('assistantToggle');
        const panel = document.getElementById('assistantPanel');
        
        toggle.classList.add('open');
        panel.classList.add('open');
        
        // Show legend if any overlays are active
        this.updateLegendVisibility();
        
        // Analytics
        this.trackEvent('panel_opened');
    }
    
    closePanel() {
        this.isOpen = false;
        const toggle = document.getElementById('assistantToggle');
        const panel = document.getElementById('assistantPanel');
        
        toggle.classList.remove('open');
        panel.classList.remove('open');
        
        this.trackEvent('panel_closed');
    }
    
    setOverlayRenderer(renderer) {
        this.overlayRenderer = renderer;
        
        // Set up overlay event handlers
        if (renderer) {
            renderer.onElementHover = (element) => this.handleElementHover(element);
            renderer.onElementClick = (element) => this.handleElementClick(element);
            renderer.onElementHoverOut = () => this.handleElementHoverOut();
        }
    }
    
    setCurrentArea(area) {
        this.currentArea = area;
        document.getElementById('currentArea').textContent = 
            area ? area.charAt(0).toUpperCase() + area.slice(1) : 'None selected';
        
        // Auto-refresh analysis if area changes
        if (area && (this.modes.riskZones || this.modes.injectionPoints)) {
            this.updateOverlays();
        }
    }
    
    async updateOverlays() {
        if (!this.overlayRenderer || !this.currentArea) return;
        
        // Check if any modes are active
        const hasActiveModes = this.modes.riskZones || this.modes.injectionPoints;
        if (!hasActiveModes) {
            await this.overlayRenderer.renderOverlays([], [], this.modes);
            this.updateLegendVisibility();
            return;
        }
        
        try {
            this.setAnalysisStatus('analyzing');
            
            const analysisData = await this.performAnalysis();
            
            if (analysisData) {
                await this.overlayRenderer.renderOverlays(
                    analysisData.risk_zones || [],
                    analysisData.injection_points || [],
                    this.modes
                );
                
                this.updateAnalysisDisplay(analysisData);
                this.setAnalysisStatus('completed');
            }
            
        } catch (error) {
            console.error('❌ Overlay update failed:', error);
            this.setAnalysisStatus('error', error.message);
        }
        
        this.updateLegendVisibility();
    }
    
    async performAnalysis() {
        // Get current image from the UI
        const imageElement = document.getElementById('beforeImage') || 
                           document.querySelector('.result-image') ||
                           document.querySelector('img[src*="data:"]');
        
        if (!imageElement || !imageElement.src) {
            throw new Error('No image available for analysis');
        }
        
        const requestData = {
            image: imageElement.src,
            area: this.currentArea,
            modes: this.modes
        };
        
        const startTime = Date.now();
        
        // Simulate API call progress
        this.updateProgress(0, 'Preparing image...');
        await this.delay(200);
        
        this.updateProgress(25, 'Detecting facial landmarks...');
        await this.delay(500);
        
        this.updateProgress(50, 'Analyzing treatment area...');
        await this.delay(400);
        
        this.updateProgress(75, 'Generating medical overlays...');
        await this.delay(300);
        
        // Make actual API call
        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
        }
        
        this.updateProgress(100, 'Analysis complete');
        
        const analysisData = await response.json();
        analysisData.processing_time_ms = Date.now() - startTime;
        
        return analysisData;
    }
    
    updateProgress(percentage, text) {
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (progressFill) progressFill.style.width = `${percentage}%`;
        if (progressText) progressText.textContent = text;
    }
    
    setAnalysisStatus(status, message = '') {
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        const loadingSection = document.getElementById('loadingSection');
        const analysisStatus = document.getElementById('analysisStatus');
        
        switch (status) {
            case 'analyzing':
                this.isAnalyzing = true;
                statusIndicator.style.background = '#f59e0b';
                statusText.textContent = 'Analyzing';
                loadingSection.style.display = 'block';
                analysisStatus.style.display = 'none';
                break;
                
            case 'completed':
                this.isAnalyzing = false;
                statusIndicator.style.background = '#10b981';
                statusText.textContent = 'Complete';
                loadingSection.style.display = 'none';
                analysisStatus.style.display = 'flex';
                break;
                
            case 'error':
                this.isAnalyzing = false;
                statusIndicator.style.background = '#ef4444';
                statusText.textContent = 'Error';
                loadingSection.style.display = 'none';
                analysisStatus.style.display = 'flex';
                this.showErrorMessage(message);
                break;
                
            default:
                this.isAnalyzing = false;
                statusIndicator.style.background = '#6b7280';
                statusText.textContent = 'Ready';
                loadingSection.style.display = 'none';
                analysisStatus.style.display = 'flex';
        }
    }
    
    updateAnalysisDisplay(analysisData) {
        this.currentAnalysis = analysisData;
        
        // Update confidence
        const confidence = analysisData.confidence_score || 0;
        this.updateConfidence(confidence);
        
        // Update processing time
        const processingTime = analysisData.processing_time_ms || 0;
        document.getElementById('processingTime').textContent = `${processingTime}ms`;
        
        // Track analytics
        this.trackEvent('analysis_completed', {
            area: this.currentArea,
            confidence: confidence,
            processing_time: processingTime,
            modes: this.modes
        });
    }
    
    updateConfidence(confidence) {
        this.confidenceScore = confidence;
        
        const confidenceFill = document.getElementById('confidenceFill');
        const confidenceValue = document.getElementById('confidenceValue');
        
        if (confidenceFill) {
            confidenceFill.style.width = `${confidence * 100}%`;
        }
        
        if (confidenceValue) {
            confidenceValue.textContent = `${Math.round(confidence * 100)}%`;
        }
        
        // Color based on confidence level
        if (confidenceFill) {
            if (confidence >= 0.8) {
                confidenceFill.style.background = '#22c55e';
            } else if (confidence >= 0.6) {
                confidenceFill.style.background = '#eab308';
            } else if (confidence >= 0.4) {
                confidenceFill.style.background = '#f97316';
            } else {
                confidenceFill.style.background = '#ef4444';
            }
        }
    }
    
    updateLegendVisibility() {
        const legend = document.getElementById('overlayLegend');
        const hasActiveOverlays = this.modes.riskZones || this.modes.injectionPoints;
        
        if (legend) {
            legend.style.display = hasActiveOverlays ? 'block' : 'none';
        }
    }
    
    async refreshAnalysis() {
        if (this.isAnalyzing) return;
        
        // Reset modes if nothing is selected
        if (!this.modes.riskZones && !this.modes.injectionPoints) {
            this.modes.riskZones = true;
            this.modes.injectionPoints = true;
            
            document.getElementById('riskZonesToggle').checked = true;
            document.getElementById('injectionPointsToggle').checked = true;
        }
        
        await this.updateOverlays();
    }
    
    openSettings() {
        // Placeholder for settings dialog
        console.log('🔧 Settings dialog would open here');
        
        // Could implement:
        // - Sensitivity adjustments
        // - Color scheme selection
        // - Advanced analysis options
        // - Export settings
    }
    
    handleElementHover(element) {
        // Could show preview tooltip or highlight related information
        console.log('🔍 Hovering over:', element.type, element.data.label || element.data.name);
    }
    
    handleElementClick(element) {
        // Could open detailed information panel
        console.log('👆 Clicked on:', element.type, element.data.label || element.data.name);
        
        // Show detailed info in a modal or side panel
        this.showElementDetails(element);
    }
    
    handleElementHoverOut() {
        // Clear any hover states
    }
    
    showElementDetails(element) {
        // Implementation for showing detailed medical information
        // This would integrate with the tooltip system
        console.log('📋 Showing details for:', element);
    }
    
    showErrorMessage(message) {
        // Show error in status area
        const statusContent = document.querySelector('.status-content');
        if (statusContent) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = 'color: #ef4444; font-size: 12px; margin-top: 8px;';
            errorDiv.textContent = message;
            
            // Remove existing error messages
            const existingError = statusContent.querySelector('.error-message');
            if (existingError) existingError.remove();
            
            statusContent.appendChild(errorDiv);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 5000);
        }
    }
    
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    trackEvent(eventName, properties = {}) {
        // Analytics tracking
        console.log('📊 Event:', eventName, properties);
        
        // Could integrate with analytics service:
        // analytics.track(eventName, {
        //     ...properties,
        //     timestamp: Date.now(),
        //     user_agent: navigator.userAgent
        // });
    }
    
    // Public API methods
    show() {
        document.getElementById('medicalAssistantWidget').style.display = 'block';
    }
    
    hide() {
        document.getElementById('medicalAssistantWidget').style.display = 'none';
        this.closePanel();
    }
    
    destroy() {
        const widget = document.getElementById('medicalAssistantWidget');
        const styles = document.getElementById('medicalAssistantStyles');
        
        if (widget) widget.remove();
        if (styles) styles.remove();
        
        console.log('🗑️ Medical AI Assistant Widget destroyed');
    }
}