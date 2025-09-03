/**
 * Medical Tooltip System for NuvaFace
 * 
 * Professional tooltip system for displaying detailed medical information
 * about injection points and risk zones with rich content and citations.
 */

class MedicalTooltipSystem {
    constructor() {
        this.activeTooltip = null;
        this.tooltipData = new Map();
        this.tooltipContainer = null;
        this.showDelay = 300;  // ms to show tooltip
        this.hideDelay = 100;  // ms to hide tooltip
        this.showTimer = null;
        this.hideTimer = null;
        
        this.createTooltipContainer();
        this.attachGlobalListeners();
        
        console.log('💬 Medical Tooltip System initialized');
    }
    
    createTooltipContainer() {
        // Remove existing container
        const existing = document.getElementById('medicalTooltipContainer');
        if (existing) existing.remove();
        
        const container = document.createElement('div');
        container.id = 'medicalTooltipContainer';
        container.className = 'medical-tooltip-container';
        
        container.innerHTML = `
            <div class="medical-tooltip" id="medicalTooltip">
                <!-- Quick Tooltip -->
                <div class="tooltip-quick" id="tooltipQuick">
                    <div class="tooltip-header">
                        <h4 class="tooltip-title" id="tooltipQuickTitle"></h4>
                        <span class="tooltip-type" id="tooltipQuickType"></span>
                    </div>
                    <div class="tooltip-content">
                        <p class="tooltip-description" id="tooltipQuickDescription"></p>
                    </div>
                </div>
                
                <!-- Detailed Tooltip -->
                <div class="tooltip-detailed" id="tooltipDetailed">
                    <div class="tooltip-header">
                        <div class="tooltip-title-section">
                            <h3 class="tooltip-title" id="tooltipDetailedTitle"></h3>
                            <div class="tooltip-badges">
                                <span class="md-code-badge" id="tooltipMdCode"></span>
                                <span class="severity-badge" id="tooltipSeverity"></span>
                            </div>
                        </div>
                        <button class="tooltip-close" id="tooltipClose">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="tooltip-body">
                        <!-- Medical Details -->
                        <div class="medical-details" id="medicalDetails">
                            <div class="detail-grid">
                                <!-- Injection Point Details -->
                                <div class="detail-section injection-details" id="injectionDetails" style="display: none;">
                                    <div class="detail-row">
                                        <span class="detail-label">Technique:</span>
                                        <span class="detail-value" id="detailTechnique">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Depth:</span>
                                        <span class="detail-value" id="detailDepth">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Volume:</span>
                                        <span class="detail-value" id="detailVolume">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Tool:</span>
                                        <span class="detail-value" id="detailTool">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Confidence:</span>
                                        <div class="confidence-meter">
                                            <div class="confidence-bar">
                                                <div class="confidence-fill" id="detailConfidenceFill"></div>
                                            </div>
                                            <span class="confidence-text" id="detailConfidenceText">-</span>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Risk Zone Details -->
                                <div class="detail-section risk-details" id="riskDetails" style="display: none;">
                                    <div class="detail-row">
                                        <span class="detail-label">Risk Level:</span>
                                        <span class="detail-value risk-level" id="detailRiskLevel">-</span>
                                    </div>
                                    <div class="detail-row">
                                        <span class="detail-label">Anatomy:</span>
                                        <span class="detail-value" id="detailAnatomy">-</span>
                                    </div>
                                    <div class="detail-row full-width">
                                        <span class="detail-label">Rationale:</span>
                                        <p class="detail-description" id="detailRationale">-</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Clinical Notes -->
                        <div class="clinical-notes" id="clinicalNotes" style="display: none;">
                            <h4>Clinical Notes</h4>
                            <p class="notes-content" id="notesContent"></p>
                        </div>
                        
                        <!-- Safety Information -->
                        <div class="safety-information" id="safetyInformation" style="display: none;">
                            <h4>Safety Recommendations</h4>
                            <ul class="safety-list" id="safetyList"></ul>
                        </div>
                        
                        <!-- Warnings -->
                        <div class="warnings-section" id="warningsSection" style="display: none;">
                            <h4><i class="fas fa-exclamation-triangle"></i> Warnings</h4>
                            <ul class="warnings-list" id="warningsList"></ul>
                        </div>
                        
                        <!-- Consequences -->
                        <div class="consequences-section" id="consequencesSection" style="display: none;">
                            <h4><i class="fas fa-skull-crossbones"></i> Potential Complications</h4>
                            <ul class="consequences-list" id="consequencesList"></ul>
                        </div>
                        
                        <!-- Medical Reference -->
                        <div class="medical-reference" id="medicalReference" style="display: none;">
                            <h4>Medical Reference</h4>
                            <div class="reference-content">
                                <p class="reference-text" id="referenceText"></p>
                                <div class="reference-source" id="referenceSource"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Tooltip Arrow -->
                <div class="tooltip-arrow" id="tooltipArrow"></div>
            </div>
        `;
        
        document.body.appendChild(container);
        this.tooltipContainer = container;
        
        // Add styles
        this.injectStyles();
        
        // Attach container event listeners
        this.attachContainerListeners();
    }
    
    injectStyles() {
        const styleId = 'medicalTooltipStyles';
        if (document.getElementById(styleId)) return;
        
        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .medical-tooltip-container {
                position: fixed;
                top: 0;
                left: 0;
                pointer-events: none;
                z-index: 20000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .medical-tooltip {
                position: absolute;
                background: rgba(255, 255, 255, 0.98);
                backdrop-filter: blur(20px);
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(255,255,255,0.2);
                border: 1px solid rgba(0,0,0,0.08);
                opacity: 0;
                visibility: hidden;
                transform: translateY(10px) scale(0.95);
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: auto;
                max-width: 320px;
                min-width: 280px;
            }
            
            .medical-tooltip.visible {
                opacity: 1;
                visibility: visible;
                transform: translateY(0) scale(1);
            }
            
            .medical-tooltip.detailed {
                max-width: 420px;
                min-width: 380px;
            }
            
            .tooltip-header {
                padding: 16px 20px 12px;
                border-bottom: 1px solid rgba(0,0,0,0.08);
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
            }
            
            .tooltip-title-section {
                flex: 1;
            }
            
            .tooltip-title {
                margin: 0 0 8px 0;
                font-size: 16px;
                font-weight: 600;
                color: #1f2937;
                line-height: 1.2;
            }
            
            .tooltip-quick .tooltip-title {
                font-size: 14px;
                margin-bottom: 4px;
            }
            
            .tooltip-type {
                display: inline-block;
                padding: 2px 8px;
                background: #e0f2fe;
                color: #0277bd;
                font-size: 11px;
                font-weight: 500;
                border-radius: 4px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .tooltip-badges {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .md-code-badge {
                padding: 4px 8px;
                background: #3b82f6;
                color: white;
                font-size: 11px;
                font-weight: 600;
                border-radius: 6px;
                letter-spacing: 0.5px;
            }
            
            .severity-badge {
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
                border-radius: 6px;
                text-transform: capitalize;
            }
            
            .severity-badge.low {
                background: #fef3c7;
                color: #92400e;
            }
            
            .severity-badge.moderate {
                background: #fed7aa;
                color: #c2410c;
            }
            
            .severity-badge.high {
                background: #fecaca;
                color: #dc2626;
            }
            
            .severity-badge.critical {
                background: #dc2626;
                color: white;
            }
            
            .tooltip-close {
                width: 24px;
                height: 24px;
                border: none;
                background: rgba(0,0,0,0.05);
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                color: #6b7280;
                margin-left: 12px;
                flex-shrink: 0;
                transition: all 0.2s ease;
            }
            
            .tooltip-close:hover {
                background: #ef4444;
                color: white;
            }
            
            .tooltip-content, .tooltip-body {
                padding: 16px 20px;
            }
            
            .tooltip-quick .tooltip-content {
                padding: 12px 20px 16px;
            }
            
            .tooltip-description {
                margin: 0;
                color: #4b5563;
                font-size: 13px;
                line-height: 1.4;
            }
            
            .detail-grid {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .detail-section h4 {
                margin: 0 0 12px 0;
                font-size: 13px;
                font-weight: 600;
                color: #374151;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .detail-section h4 i {
                font-size: 14px;
                color: #ef4444;
            }
            
            .detail-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            
            .detail-row.full-width {
                flex-direction: column;
                align-items: flex-start;
                gap: 6px;
            }
            
            .detail-label {
                font-size: 12px;
                font-weight: 500;
                color: #6b7280;
                min-width: 80px;
            }
            
            .detail-value {
                font-size: 12px;
                color: #1f2937;
                font-weight: 500;
                text-align: right;
            }
            
            .detail-description {
                font-size: 12px;
                color: #4b5563;
                line-height: 1.4;
                margin: 0;
            }
            
            .risk-level.low { color: #059669; }
            .risk-level.moderate { color: #d97706; }
            .risk-level.high { color: #dc2626; }
            .risk-level.critical { color: #7c2d12; font-weight: 600; }
            
            .confidence-meter {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .confidence-bar {
                width: 60px;
                height: 4px;
                background: #e5e7eb;
                border-radius: 2px;
                overflow: hidden;
            }
            
            .confidence-fill {
                height: 100%;
                border-radius: 2px;
                transition: width 0.3s ease;
                background: linear-gradient(90deg, #ef4444, #f97316, #eab308, #22c55e);
            }
            
            .confidence-text {
                font-size: 11px;
                font-weight: 600;
                color: #374151;
                min-width: 30px;
            }
            
            .clinical-notes,
            .safety-information,
            .warnings-section,
            .consequences-section,
            .medical-reference {
                margin-top: 16px;
                padding-top: 16px;
                border-top: 1px solid rgba(0,0,0,0.08);
            }
            
            .notes-content {
                font-size: 12px;
                color: #4b5563;
                line-height: 1.5;
                margin: 8px 0 0 0;
            }
            
            .safety-list,
            .warnings-list,
            .consequences-list {
                margin: 8px 0 0 0;
                padding-left: 16px;
            }
            
            .safety-list li,
            .warnings-list li,
            .consequences-list li {
                font-size: 12px;
                line-height: 1.4;
                margin-bottom: 4px;
                color: #4b5563;
            }
            
            .warnings-list li {
                color: #dc2626;
            }
            
            .consequences-list li {
                color: #7c2d12;
            }
            
            .reference-content {
                margin-top: 8px;
            }
            
            .reference-text {
                font-size: 12px;
                color: #4b5563;
                line-height: 1.4;
                margin: 0 0 8px 0;
                font-style: italic;
            }
            
            .reference-source {
                font-size: 11px;
                color: #9ca3af;
                font-weight: 500;
            }
            
            .tooltip-arrow {
                position: absolute;
                width: 12px;
                height: 12px;
                background: rgba(255, 255, 255, 0.98);
                border: 1px solid rgba(0,0,0,0.08);
                transform: rotate(45deg);
                z-index: -1;
            }
            
            /* Arrow positioning */
            .medical-tooltip.arrow-top .tooltip-arrow {
                top: -7px;
                left: 50%;
                margin-left: -6px;
            }
            
            .medical-tooltip.arrow-bottom .tooltip-arrow {
                bottom: -7px;
                left: 50%;
                margin-left: -6px;
            }
            
            .medical-tooltip.arrow-left .tooltip-arrow {
                left: -7px;
                top: 50%;
                margin-top: -6px;
            }
            
            .medical-tooltip.arrow-right .tooltip-arrow {
                right: -7px;
                top: 50%;
                margin-top: -6px;
            }
            
            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .medical-tooltip {
                    max-width: calc(100vw - 32px);
                    min-width: 280px;
                }
                
                .medical-tooltip.detailed {
                    max-width: calc(100vw - 32px);
                    min-width: 300px;
                }
            }
            
            /* Scrollbar styling */
            .tooltip-body {
                max-height: 400px;
                overflow-y: auto;
                scrollbar-width: thin;
                scrollbar-color: #d1d5db transparent;
            }
            
            .tooltip-body::-webkit-scrollbar {
                width: 6px;
            }
            
            .tooltip-body::-webkit-scrollbar-track {
                background: transparent;
            }
            
            .tooltip-body::-webkit-scrollbar-thumb {
                background: #d1d5db;
                border-radius: 3px;
            }
            
            .tooltip-body::-webkit-scrollbar-thumb:hover {
                background: #9ca3af;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    attachGlobalListeners() {
        // Close tooltips on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideTooltip();
            }
        });
        
        // Close tooltips when clicking outside
        document.addEventListener('click', (e) => {
            if (this.activeTooltip && !e.target.closest('.medical-tooltip')) {
                this.hideTooltip();
            }
        });
    }
    
    attachContainerListeners() {
        const closeBtn = document.getElementById('tooltipClose');
        closeBtn.addEventListener('click', () => this.hideTooltip());
        
        // Prevent tooltip from closing when clicking inside it
        this.tooltipContainer.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
    
    showQuickTooltip(element, x, y) {
        this.clearTimers();
        
        this.showTimer = setTimeout(() => {
            this.displayQuickTooltip(element, x, y);
        }, this.showDelay);
    }
    
    displayQuickTooltip(element, x, y) {
        const tooltip = document.getElementById('medicalTooltip');
        const quickTooltip = document.getElementById('tooltipQuick');
        const detailedTooltip = document.getElementById('tooltipDetailed');
        
        // Show quick tooltip, hide detailed
        quickTooltip.style.display = 'block';
        detailedTooltip.style.display = 'none';
        tooltip.classList.remove('detailed');
        
        // Populate quick tooltip content
        this.populateQuickTooltip(element);
        
        // Position and show
        this.positionTooltip(x, y);
        tooltip.classList.add('visible');
        
        this.activeTooltip = 'quick';
        
        console.log('💬 Quick tooltip shown for:', element.type);
    }
    
    showDetailedTooltip(element, x, y) {
        this.clearTimers();
        
        const tooltip = document.getElementById('medicalTooltip');
        const quickTooltip = document.getElementById('tooltipQuick');
        const detailedTooltip = document.getElementById('tooltipDetailed');
        
        // Show detailed tooltip, hide quick
        quickTooltip.style.display = 'none';
        detailedTooltip.style.display = 'block';
        tooltip.classList.add('detailed');
        
        // Populate detailed tooltip content
        this.populateDetailedTooltip(element);
        
        // Position and show
        this.positionTooltip(x, y);
        tooltip.classList.add('visible');
        
        this.activeTooltip = 'detailed';
        
        console.log('📋 Detailed tooltip shown for:', element.type);
    }
    
    populateQuickTooltip(element) {
        const data = element.data;
        const type = element.type;
        
        document.getElementById('tooltipQuickTitle').textContent = 
            data.label || data.name || 'Medical Information';
        
        document.getElementById('tooltipQuickType').textContent = 
            type === 'injectionPoint' ? 'Injection Point' : 'Risk Zone';
        
        let description = '';
        if (type === 'injectionPoint') {
            description = data.notes || 
                         `${data.technique || 'Standard'} technique at ${data.depth || 'dermal'} depth`;
        } else {
            description = data.tooltip || data.rationale || 'Anatomical risk zone';
        }
        
        document.getElementById('tooltipQuickDescription').textContent = description;
    }
    
    populateDetailedTooltip(element) {
        const data = element.data;
        const type = element.type;
        
        // Header information
        document.getElementById('tooltipDetailedTitle').textContent = 
            data.label || data.name || 'Medical Information';
        
        // Badges
        const mdCodeBadge = document.getElementById('tooltipMdCode');
        const severityBadge = document.getElementById('tooltipSeverity');
        
        if (data.code || data.md_code) {
            mdCodeBadge.textContent = data.code || data.md_code;
            mdCodeBadge.style.display = 'inline-block';
        } else {
            mdCodeBadge.style.display = 'none';
        }
        
        if (data.severity) {
            severityBadge.textContent = data.severity;
            severityBadge.className = `severity-badge ${data.severity}`;
            severityBadge.style.display = 'inline-block';
        } else {
            severityBadge.style.display = 'none';
        }
        
        // Show appropriate detail sections
        this.populateDetailSection(type, data);
        this.populateAdditionalSections(data);
    }
    
    populateDetailSection(type, data) {
        const injectionDetails = document.getElementById('injectionDetails');
        const riskDetails = document.getElementById('riskDetails');
        
        if (type === 'injectionPoint') {
            injectionDetails.style.display = 'block';
            riskDetails.style.display = 'none';
            
            document.getElementById('detailTechnique').textContent = data.technique || '-';
            document.getElementById('detailDepth').textContent = data.depth || '-';
            document.getElementById('detailVolume').textContent = data.volume || '-';
            document.getElementById('detailTool').textContent = data.tool || '-';
            
            // Confidence meter
            const confidence = data.confidence || 0;
            const confidenceFill = document.getElementById('detailConfidenceFill');
            const confidenceText = document.getElementById('detailConfidenceText');
            
            confidenceFill.style.width = `${confidence * 100}%`;
            confidenceText.textContent = `${Math.round(confidence * 100)}%`;
            
        } else {
            injectionDetails.style.display = 'none';
            riskDetails.style.display = 'block';
            
            document.getElementById('detailRiskLevel').textContent = data.severity || '-';
            document.getElementById('detailRiskLevel').className = `detail-value risk-level ${data.severity || ''}`;
            document.getElementById('detailAnatomy').textContent = data.medical_reference || '-';
            document.getElementById('detailRationale').textContent = data.rationale || '-';
        }
    }
    
    populateAdditionalSections(data) {
        // Clinical Notes
        const clinicalNotes = document.getElementById('clinicalNotes');
        const notesContent = document.getElementById('notesContent');
        
        if (data.notes) {
            notesContent.textContent = data.notes;
            clinicalNotes.style.display = 'block';
        } else {
            clinicalNotes.style.display = 'none';
        }
        
        // Safety Information
        const safetyInfo = document.getElementById('safetyInformation');
        const safetyList = document.getElementById('safetyList');
        
        if (data.safety_recommendations && data.safety_recommendations.length > 0) {
            safetyList.innerHTML = '';
            data.safety_recommendations.forEach(recommendation => {
                const li = document.createElement('li');
                li.textContent = recommendation;
                safetyList.appendChild(li);
            });
            safetyInfo.style.display = 'block';
        } else {
            safetyInfo.style.display = 'none';
        }
        
        // Warnings
        const warningsSection = document.getElementById('warningsSection');
        const warningsList = document.getElementById('warningsList');
        
        if (data.warnings && data.warnings.length > 0) {
            warningsList.innerHTML = '';
            data.warnings.forEach(warning => {
                const li = document.createElement('li');
                li.textContent = warning;
                warningsList.appendChild(li);
            });
            warningsSection.style.display = 'block';
        } else {
            warningsSection.style.display = 'none';
        }
        
        // Consequences
        const consequencesSection = document.getElementById('consequencesSection');
        const consequencesList = document.getElementById('consequencesList');
        
        if (data.consequences && data.consequences.length > 0) {
            consequencesList.innerHTML = '';
            data.consequences.forEach(consequence => {
                const li = document.createElement('li');
                li.textContent = consequence;
                consequencesList.appendChild(li);
            });
            consequencesSection.style.display = 'block';
        } else {
            consequencesSection.style.display = 'none';
        }
        
        // Medical Reference
        const medicalReference = document.getElementById('medicalReference');
        const referenceText = document.getElementById('referenceText');
        const referenceSource = document.getElementById('referenceSource');
        
        if (data.medical_reference) {
            referenceText.textContent = data.medical_reference;
            
            // Show source if available
            if (data.source) {
                let sourceText = '';
                if (data.source.md_code) sourceText += `MD Code: ${data.source.md_code}`;
                if (data.source.ref) sourceText += sourceText ? `, ${data.source.ref}` : data.source.ref;
                referenceSource.textContent = sourceText || 'Medical literature';
            } else {
                referenceSource.textContent = 'Medical literature';
            }
            
            medicalReference.style.display = 'block';
        } else {
            medicalReference.style.display = 'none';
        }
    }
    
    positionTooltip(x, y) {
        const tooltip = document.getElementById('medicalTooltip');
        const arrow = document.getElementById('tooltipArrow');
        
        // Get tooltip dimensions
        tooltip.style.visibility = 'hidden';
        tooltip.style.opacity = '1';
        const rect = tooltip.getBoundingClientRect();
        tooltip.style.visibility = 'visible';
        tooltip.style.opacity = '0';
        
        // Get viewport dimensions
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Calculate best position
        let tooltipX = x;
        let tooltipY = y - rect.height - 15;
        let arrowPosition = 'top';
        
        // Check if tooltip fits above
        if (tooltipY < 10) {
            tooltipY = y + 15;
            arrowPosition = 'bottom';
        }
        
        // Check if tooltip fits horizontally
        if (tooltipX + rect.width > viewportWidth - 10) {
            tooltipX = viewportWidth - rect.width - 10;
        }
        if (tooltipX < 10) {
            tooltipX = 10;
        }
        
        // Check if we need to position to the side
        if (tooltipY + rect.height > viewportHeight - 10 && arrowPosition === 'bottom') {
            // Try positioning to the right
            tooltipX = x + 15;
            tooltipY = y - rect.height / 2;
            arrowPosition = 'left';
            
            // Check if it fits to the right
            if (tooltipX + rect.width > viewportWidth - 10) {
                // Position to the left instead
                tooltipX = x - rect.width - 15;
                arrowPosition = 'right';
            }
            
            // Ensure it doesn't go off screen vertically
            if (tooltipY < 10) {
                tooltipY = 10;
            } else if (tooltipY + rect.height > viewportHeight - 10) {
                tooltipY = viewportHeight - rect.height - 10;
            }
        }
        
        // Apply position
        tooltip.style.left = `${tooltipX}px`;
        tooltip.style.top = `${tooltipY}px`;
        
        // Update arrow classes
        tooltip.className = `medical-tooltip arrow-${arrowPosition}`;
        
        console.log(`📍 Positioned tooltip at ${tooltipX}, ${tooltipY} with arrow ${arrowPosition}`);
    }
    
    hideTooltip() {
        this.clearTimers();
        
        const tooltip = document.getElementById('medicalTooltip');
        if (tooltip) {
            tooltip.classList.remove('visible');
            this.activeTooltip = null;
        }
        
        console.log('👻 Tooltip hidden');
    }
    
    scheduleHide() {
        this.clearTimers();
        
        this.hideTimer = setTimeout(() => {
            this.hideTooltip();
        }, this.hideDelay);
    }
    
    clearTimers() {
        if (this.showTimer) {
            clearTimeout(this.showTimer);
            this.showTimer = null;
        }
        
        if (this.hideTimer) {
            clearTimeout(this.hideTimer);
            this.hideTimer = null;
        }
    }
    
    // Public API methods
    
    showTooltipForElement(element, x, y, detailed = false) {
        if (detailed) {
            this.showDetailedTooltip(element, x, y);
        } else {
            this.showQuickTooltip(element, x, y);
        }
    }
    
    hide() {
        this.hideTooltip();
    }
    
    isVisible() {
        return this.activeTooltip !== null;
    }
    
    destroy() {
        this.clearTimers();
        
        if (this.tooltipContainer) {
            this.tooltipContainer.remove();
        }
        
        const styles = document.getElementById('medicalTooltipStyles');
        if (styles) {
            styles.remove();
        }
        
        console.log('🗑️ Medical Tooltip System destroyed');
    }
}