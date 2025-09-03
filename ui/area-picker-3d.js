// 3D Area Picker Component for NuvaFace
// Uses Three.js for 3D model loading and interaction

class AreaPicker3D {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null; // Add OrbitControls
        this.model = null;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.selectedArea = null;
        this.hoveredArea = null;
        this.isMobile = window.innerWidth <= 768;
        this.isTouch = 'ontouchstart' in window;
        
        // Initialize submesh system
        this.submeshes = {};
        this.originalMaterials = {};
        
        // Define clickable areas as anatomical overlays with precise positioning
        // Using unified hover color #ff99aa as requested
        this.areas = {
            lips: { 
                color: 0xff4757,          // Red for lips
                hoverColor: 0xff99aa,     // Unified hover color as requested
                defaultColor: 0xff9999,   // Light red default (lips are naturally reddish)
                position: { x: 0, y: -0.15, z: 0.85 }, // Much closer to face, at mouth level
                name: 'Lippen'
            },
            chin: { 
                color: 0x5f27cd,          // Purple for chin
                hoverColor: 0xff99aa,     // Unified hover color as requested
                defaultColor: 0xf0f0f0,   // Light gray default
                position: { x: 0, y: -0.45, z: 0.75 }, // Lower, much closer to face
                name: 'Kinn'
            },
            cheeks: { 
                color: 0xffa502,          // Orange for cheeks
                hoverColor: 0xff99aa,     // Unified hover color as requested
                defaultColor: 0xf5f5f5,   // Very light gray default
                position: { x: 0.25, y: -0.08, z: 0.75 }, // Cheek bone area, much closer
                name: 'Wangen'
            },
            forehead: { 
                color: 0x3742fa,          // Blue for forehead
                hoverColor: 0xff99aa,     // Unified hover color as requested
                defaultColor: 0xf8f8f8,   // Almost white default
                position: { x: 0, y: 0.15, z: 0.80 }, // Forehead area, much closer to face
                name: 'Stirn'
            }
        };
        
        this.currentHoveredArea = null;
        this.selectedAreaMarker = null;
        
        this.init();
    }
    
    init() {
        this.setupScene();
        this.setupCamera();
        this.setupRenderer();
        this.setupControls(); // Add OrbitControls
        this.setupLights();
        this.setupEventListeners();
        this.loadModel();
        this.animate();
    }
    
    setupScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf8f9fa);
    }
    
    setupCamera() {
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
        
        // Mobile-optimized camera position
        if (this.isMobile) {
            this.camera.position.set(0, 0.3, 2.5); // Closer for mobile
        } else {
            this.camera.position.set(0, 0.5, 3); // Position for desktop
        }
        this.camera.lookAt(0, 0, 0);
    }
    
    setupRenderer() {
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: false 
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.setClearColor(0xf8f9fa, 1); // Light background
        this.container.appendChild(this.renderer.domElement);
    }
    
    setupControls() {
        // Add OrbitControls for mouse/touch interaction
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        
        // Mobile-optimized controls
        if (this.isMobile) {
            this.controls.rotateSpeed = 0.6;  // Slower rotation for better control on mobile
            this.controls.zoomSpeed = 0.8;    // Slower zoom for mobile
            this.controls.minDistance = 1.2;  // Closer minimum distance
            this.controls.maxDistance = 4;    // Closer maximum distance
            this.controls.enableZoom = true;  // Enable pinch zoom on mobile
            this.controls.enableRotate = true; // Enable touch rotation
        } else {
            this.controls.rotateSpeed = 0.8;
            this.controls.zoomSpeed = 1.2;
            this.controls.minDistance = 1.5;
            this.controls.maxDistance = 5;
        }
        
        this.controls.panSpeed = 0.8;
        this.controls.enablePan = false; // Disable panning for both
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }
    
    setupLights() {
        // Brighter ambient light for better visibility
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
        this.scene.add(ambientLight);
        
        // Key light from above
        const keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
        keyLight.position.set(2, 3, 2);
        keyLight.castShadow = true;
        keyLight.shadow.camera.near = 0.1;
        keyLight.shadow.camera.far = 50;
        keyLight.shadow.camera.left = -10;
        keyLight.shadow.camera.right = 10;
        keyLight.shadow.camera.top = 10;
        keyLight.shadow.camera.bottom = -10;
        this.scene.add(keyLight);
        
        // Fill light from left
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.6);
        fillLight.position.set(-2, 1, 1);
        this.scene.add(fillLight);
        
        // Back light for rim lighting
        const backLight = new THREE.DirectionalLight(0xffffff, 0.4);
        backLight.position.set(0, 1, -2);
        this.scene.add(backLight);
    }
    
    async loadModel() {
        try {
            const loader = new THREE.GLTFLoader();
            // Try new segmented model first, fallback to old model
            const modelPaths = ['assets/models/female_head_areas.glb', 'assets/models/angelica.glb'];
            
            for (const modelPath of modelPaths) {
                try {
                    console.log('🔍 DEBUG: Attempting to load GLB from:', modelPath);
                    const gltf = await this.loadGLTF(loader, modelPath);
                    console.log('✅ DEBUG: GLB loaded successfully from:', modelPath);
                    this.setupModel(gltf.scene, modelPath.includes('areas'));
                    
                    // Hide loading spinner
                    const loading = document.querySelector('.loading-3d');
                    if (loading) {
                        loading.style.display = 'none';
                    }
                    
                    // Debug output for user
                    if (modelPath.includes('areas')) {
                        console.log('🎯 DEBUG: Using NEW submesh model system!');
                    } else {
                        console.log('⚠️  DEBUG: Using FALLBACK overlay system!');
                    }
                    return; // Success, exit loop
                } catch (error) {
                    console.warn(`❌ DEBUG: GLB model ${modelPath} failed:`, error.message);
                    continue; // Try next model
                }
            }
            
            // If all models fail, create placeholder
            console.warn('All GLB models failed, creating placeholder');
            this.createPlaceholderModel();
            
        } catch (error) {
            console.error('Error loading 3D model:', error.message);
            this.createPlaceholderModel();
        }
    }
    
    loadGLTF(loader, path) {
        return new Promise((resolve, reject) => {
            loader.load(
                path, 
                (gltf) => {
                    // Success callback - avoid logging the entire gltf object to prevent stack overflow
                    resolve(gltf);
                },
                (progress) => {
                    // Progress callback (optional)
                    if (progress.lengthComputable) {
                        const percentComplete = progress.loaded / progress.total * 100;
                        console.log('Model loading progress:', Math.round(percentComplete) + '%');
                    }
                },
                (error) => {
                    // Error callback
                    console.error('GLB loading failed:', error.message || error);
                    reject(error);
                }
            );
        });
    }
    
    setupModel(model, hasSubmeshes = false) {
        console.log('Setting up GLB model, hasSubmeshes:', hasSubmeshes);
        
        // Clear existing submesh references (don't re-initialize, just clear)
        this.submeshes = {};
        this.originalMaterials = {};
        
        let meshCount = 0;
        let meshNames = [];
        
        try {
            model.traverse((child) => {
                if (child.isMesh) {
                    meshCount++;
                    meshNames.push(child.name || 'unnamed');
                    
                    // Ensure proper material setup and create individual material instances
                    if (child.material) {
                        child.material.side = THREE.DoubleSide;
                        child.material.needsUpdate = true;
                        
                        // IMPORTANT: Clone material to avoid shared material references
                        const originalMaterial = child.material.clone();
                        this.originalMaterials[child.name || 'unnamed'] = originalMaterial;
                        
                        // Assign individual material copy to this mesh
                        child.material = originalMaterial.clone();
                        child.material.needsUpdate = true;
                        
                        console.log(`📦 Created individual material for: ${child.name}`);
                    }
                    child.castShadow = true;
                    child.receiveShadow = true;
                    
                    // If this model has submeshes, store references by name
                    if (hasSubmeshes && child.name) {
                        const areaName = child.name.toLowerCase();
                        // Check for various possible submesh names
                        let detectedArea = null;
                        
                        if (areaName.includes('lip') || areaName === 'lips') {
                            detectedArea = 'lips';
                        } else if (areaName.includes('chin') || areaName === 'chin') {
                            detectedArea = 'chin';
                        } else if (areaName.includes('cheek') || areaName === 'cheeks' || areaName.includes('wange')) {
                            detectedArea = 'cheeks';
                        } else if (areaName.includes('forehead') || areaName === 'forehead' || areaName.includes('stirn')) {
                            detectedArea = 'forehead';
                        }
                        
                        if (detectedArea) {
                            this.submeshes[detectedArea] = child;
                            console.log(`✅ Found submesh: ${detectedArea} (original name: ${child.name})`);
                        } else {
                            console.log(`❓ Unknown submesh: ${child.name}`);
                        }
                    }
                }
            });
            
            console.log(`Found ${meshCount} meshes:`, meshNames.slice(0, 10));
            console.log('Submeshes found:', Object.keys(this.submeshes));
            
            if (meshCount === 0) {
                console.warn('No meshes found in model! Creating placeholder.');
                this.createPlaceholderModel();
                return;
            }
            
            // Calculate bounding box and scale model
            const box = new THREE.Box3().setFromObject(model);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            
            console.log('Model bounds - center:', [
                Math.round(center.x * 100) / 100,
                Math.round(center.y * 100) / 100,
                Math.round(center.z * 100) / 100
            ]);
            
            // Scale and position the model
            if (size.x === 0 || size.y === 0 || size.z === 0) {
                console.log('Model has zero size, applying default scale');
                model.scale.setScalar(0.02);
            } else {
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 2.0 / maxDim;
                model.scale.setScalar(scale);
                
                // Center the model
                model.position.x = -center.x * scale;
                model.position.y = -center.y * scale - 0.3;
                model.position.z = -center.z * scale;
            }
            
            this.model = model;
            this.scene.add(model);
            
            // Check if we found submeshes
            if (Object.keys(this.submeshes).length > 0) {
                console.log('✅ Using submeshes for area detection');
            } else {
                console.log('⚠️ No submeshes found - model may not be segmented');
            }
            
            console.log('GLB model loaded successfully with scale:', Math.round(model.scale.x * 1000) / 1000);
            
        } catch (error) {
            console.error('Error setting up GLB model:', error.message);
            console.log('Falling back to placeholder model');
            this.createPlaceholderModel();
        }
    }
    
    createPlaceholderModel() {
        // Create a simple placeholder head shape
        const headGeometry = new THREE.SphereGeometry(0.3, 32, 24);
        headGeometry.scale(1, 1.2, 0.8); // Make it more head-like
        
        const headMaterial = new THREE.MeshLambertMaterial({ 
            color: 0xfdbcb4, // Skin tone
            transparent: true,
            opacity: 0.9
        });
        
        const head = new THREE.Mesh(headGeometry, headMaterial);
        head.position.set(0, 0, 0);
        head.castShadow = true;
        head.receiveShadow = true;
        
        this.model = head;
        this.scene.add(head);
        this.createAreaMarkers();
        
        // Hide loading spinner
        const loading = document.querySelector('.loading-3d');
        if (loading) {
            loading.style.display = 'none';
        }
        
        console.info('Using placeholder 3D head model. To use real model:');
        console.info('1. Download: https://download.blender.org/demo/asset-bundles/human-base-meshes/');
        console.info('2. Export female head as GLB from Blender');
        console.info('3. Save as: ./assets/models/angelica.glb');
    }
    
    
    setupEventListeners() {
        // Mobile-first event handling
        if (this.isTouch) {
            // Touch events for mobile
            this.container.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: false });
            this.container.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
            this.container.addEventListener('touchend', this.onTouchEnd.bind(this), { passive: false });
        }
        
        // Mouse events for desktop (always available as fallback)
        this.container.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.container.addEventListener('click', this.onMouseClick.bind(this));
        
        // Resize handler (mobile-responsive)
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    // Mobile-responsive resize handler
    handleResize() {
        if (!this.camera || !this.renderer) return;
        
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        // Update camera aspect ratio
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        
        // Update renderer size
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        
        // Update mobile state
        this.isMobile = window.innerWidth <= 768;
        
        // Adjust camera position for mobile
        if (this.isMobile) {
            this.camera.position.setLength(2.5);
        } else {
            this.camera.position.setLength(3);
        }
        
        // Update controls for mobile
        if (this.controls) {
            if (this.isMobile) {
                this.controls.rotateSpeed = 0.6;
                this.controls.zoomSpeed = 0.8;
                this.controls.minDistance = 1.2;
                this.controls.maxDistance = 4;
            } else {
                this.controls.rotateSpeed = 0.8;
                this.controls.zoomSpeed = 1.2;
                this.controls.minDistance = 1.5;
                this.controls.maxDistance = 5;
            }
        }
        
        // Legacy support
        this.onWindowResize && this.onWindowResize();
    }
    
    onMouseMove(event) {
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Update tooltip position
        const tooltip = document.getElementById('area-tooltip-3d');
        if (tooltip && tooltip.style.opacity === '1') {
            tooltip.style.left = event.clientX + 'px';
            tooltip.style.top = (event.clientY - 10) + 'px';
        }
        
        this.checkIntersections();
    }
    
    onMouseClick(event) {
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.selectArea();
    }
    
    onTouchStart(event) {
        event.preventDefault();
        const touch = event.touches[0];
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Store start position for tap detection
        this.touchStartPos = {
            x: this.mouse.x,
            y: this.mouse.y,
            time: Date.now()
        };
        
        // Check for hover effect on touch start (immediate feedback)
        this.checkIntersections();
    }
    
    onTouchMove(event) {
        event.preventDefault();
        const touch = event.touches[0];
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((touch.clientY - rect.top) / rect.height) * 2 + 1;
        
        // Check if this is rotation (OrbitControls handles this) or area selection
        if (this.touchStartPos) {
            const moveDistance = Math.abs(this.mouse.x - this.touchStartPos.x) + 
                                 Math.abs(this.mouse.y - this.touchStartPos.y);
            
            // Only check intersections if not rotating (small movement)
            if (moveDistance < 0.08) {
                this.checkIntersections();
            }
        }
    }
    
    onTouchEnd(event) {
        event.preventDefault();
        
        // Check if this was a tap (not a drag/rotation)
        if (this.touchStartPos) {
            const currentTime = Date.now();
            const timeDiff = currentTime - this.touchStartPos.time;
            const moveDistance = Math.abs(this.mouse.x - this.touchStartPos.x) + 
                                Math.abs(this.mouse.y - this.touchStartPos.y);
            
            // Consider it a tap if quick and small movement (mobile-optimized thresholds)
            if (timeDiff < 500 && moveDistance < 0.08) {
                this.selectArea();
            }
        }
        
        this.touchStartPos = null;
        
        // Clear any hover states on touch end
        if (this.hoveredArea) {
            this.clearAreaHover(this.hoveredArea);
            this.hoveredArea = null;
            if (this.areaLeaveCallback) {
                this.areaLeaveCallback();
            }
        }
    }
    
    checkIntersections() {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        let intersectedArea = null;
        
        // Only use submesh system (no fallback overlays)
        if (Object.keys(this.submeshes).length > 0) {
            const submeshObjects = Object.values(this.submeshes);
            const intersects = this.raycaster.intersectObjects(submeshObjects, true);
            
            if (intersects.length > 0) {
                const hitMesh = intersects[0].object;
                // Find area name by looking up the mesh in submeshes
                for (const [areaName, mesh] of Object.entries(this.submeshes)) {
                    if (mesh === hitMesh) {
                        intersectedArea = areaName;
                        break;
                    }
                }
            }
        }
        
        // Handle hover state changes
        if (intersectedArea && this.hoveredArea !== intersectedArea) {
            this.onAreaHover(intersectedArea);
        } else if (!intersectedArea && this.hoveredArea) {
            this.onAreaLeave();
        }
    }
    
    onAreaHover(areaName) {
        if (this.currentHoveredArea === areaName) return;
        
        // Clear previous hover
        if (this.currentHoveredArea) {
            this.clearAreaHover(this.currentHoveredArea);
        }
        
        this.hoveredArea = areaName;
        this.currentHoveredArea = areaName;
        this.container.style.cursor = 'pointer';
        
        // Only highlight if this area is not already selected via button
        if (this.selectedArea !== areaName) {
            this.highlightArea(areaName, true);
        }
        
        // Highlight corresponding button (deaktiviert für UI-Vereinfachung)
        // this.highlightButton(areaName, true);
        
        // Show area info tooltip
        this.showAreaTooltip(areaName);
        
        // Trigger external hover callback if exists
        if (this.onAreaHoverCallback) {
            this.onAreaHoverCallback(areaName);
        }
    }
    
    onAreaLeave() {
        if (this.currentHoveredArea) {
            // Only clear hover highlight if the area is not permanently selected
            if (this.selectedArea !== this.currentHoveredArea) {
                this.clearAreaHover(this.currentHoveredArea);
            }
        }
        
        this.hoveredArea = null;
        this.currentHoveredArea = null;
        this.container.style.cursor = 'default';
        
        // Hide tooltip
        this.hideAreaTooltip();
        
        // Trigger external leave callback if exists
        if (this.onAreaLeaveCallback) {
            this.onAreaLeaveCallback();
        }
    }
    
    selectArea() {
        if (this.hoveredArea) {
            this.selectedArea = this.hoveredArea;
            
            // Update UI to show selection
            this.showSelection(this.hoveredArea);
            
            // Update button selection
            this.selectButton(this.hoveredArea);
            
            // Trigger external selection callback
            if (this.onAreaSelectCallback) {
                this.onAreaSelectCallback(this.hoveredArea);
            }
        }
    }
    
    highlightArea(areaName, highlight) {
        // Only use submesh system - no fallback
        if (!this.submeshes[areaName]) {
            console.warn(`❌ No submesh found for area: ${areaName}`);
            return;
        }
        
        const mesh = this.submeshes[areaName];
        const originalMaterial = this.originalMaterials[mesh.name];
        
        if (!mesh || !mesh.material || !originalMaterial) {
            console.warn(`❌ Invalid mesh or material for area: ${areaName}`, {
                hasMesh: !!mesh,
                hasMaterial: !!(mesh && mesh.material),
                hasOriginal: !!originalMaterial,
                meshName: mesh ? mesh.name : 'no mesh'
            });
            return;
        }
        
        // Stop any existing animations on THIS SPECIFIC MATERIAL
        gsap.killTweensOf(mesh.material.color);
        gsap.killTweensOf(mesh.material.emissive);
        
        if (highlight) {
            console.log(`🎯 Highlighting ${areaName} (${mesh.name}) with white glow`);
            console.log(`📦 Material UUID: ${mesh.material.uuid}`);
            
            // GSAP smooth transition to white highlight ON THIS SPECIFIC MATERIAL
            gsap.to(mesh.material.color, {
                r: 1, g: 1, b: 1, // White color
                duration: 0.3,
                ease: "power2.out"
            });
            
            gsap.to(mesh.material.emissive, {
                r: 0.3, g: 0.3, b: 0.3, // Subtle white glow
                duration: 0.3,
                ease: "power2.out"
            });
            
            mesh.material.emissiveIntensity = 0.4;
            
        } else {
            console.log(`↩️ Resetting ${areaName} (${mesh.name}) to original colors`);
            console.log(`📦 Original color:`, originalMaterial.color);
            
            // Return to original colors
            const origColor = originalMaterial.color;
            const origEmissive = originalMaterial.emissive || new THREE.Color(0x000000);
            
            gsap.to(mesh.material.color, {
                r: origColor.r, g: origColor.g, b: origColor.b,
                duration: 0.3,
                ease: "power2.out"
            });
            
            gsap.to(mesh.material.emissive, {
                r: origEmissive.r, g: origEmissive.g, b: origEmissive.b,
                duration: 0.3,
                ease: "power2.out"
            });
            
            mesh.material.emissiveIntensity = originalMaterial.emissiveIntensity || 0.0;
        }
        
        // Force material update
        mesh.material.needsUpdate = true;
        console.log(`🔄 Material updated for ${areaName}, UUID: ${mesh.material.uuid}`);
    }
    
    clearAreaHover(areaName) {
        // Just call highlightArea with false to handle the cleanup properly
        this.highlightArea(areaName, false);
    }
    
    highlightButton(areaName, highlight) {
        const button = document.querySelector(`[data-area="${areaName}"]`);
        if (button) {
            if (highlight) {
                button.classList.add('hover-from-3d');
            } else {
                button.classList.remove('hover-from-3d');
            }
        }
    }
    
    selectButton(areaName) {
        // Clear all selections
        document.querySelectorAll('.area-select-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        // Select the corresponding button
        const button = document.querySelector(`[data-area="${areaName}"]`);
        if (button) {
            button.classList.add('selected');
            
            // Enable proceed button
            const proceedBtn = document.getElementById('proceedToUpload');
            if (proceedBtn) {
                proceedBtn.disabled = false;
            }
        }
    }
    
    showAreaTooltip(areaName) {
        const areaData = this.areas[areaName];
        if (!areaData) return;
        
        // Create or update tooltip
        let tooltip = document.getElementById('area-tooltip-3d');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'area-tooltip-3d';
            tooltip.className = 'area-tooltip-3d';
            document.body.appendChild(tooltip);
        }
        
        tooltip.innerHTML = `
            <div class="tooltip-content">
                <h4>${areaData.name}</h4>
                <p>Klicken zum Auswählen</p>
            </div>
        `;
        
        // Position tooltip near mouse
        tooltip.style.opacity = '1';
        tooltip.style.transform = 'translate(-50%, -100%)';
    }
    
    hideAreaTooltip() {
        const tooltip = document.getElementById('area-tooltip-3d');
        if (tooltip) {
            tooltip.style.opacity = '0';
        }
    }
    
    showSelection(areaName) {
        console.log(`📍 Showing selection for: ${areaName}`);
        
        // For submesh system, just mark as selected (visual feedback handled by highlightArea)
        this.selectedAreaMarker = areaName;
        
        // Clear any previous selections in the internal tracking
        this.clearAllSelections();
        
        console.log(`✅ Selected area: ${areaName}`);
    }
    
    clearAllSelections() {
        // For submesh system, just clear internal tracking
        this.selectedAreaMarker = null;
        this.selectedArea = null;
        console.log(`🗑️ Cleared all selections`);
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    animate() {
        requestAnimationFrame(this.animate.bind(this));
        
        // Update controls for smooth interaction
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    // Public methods for external integration
    setAreaHoverCallback(callback) {
        this.onAreaHoverCallback = callback;
    }
    
    setAreaLeaveCallback(callback) {
        this.onAreaLeaveCallback = callback;
    }
    
    setAreaSelectCallback(callback) {
        this.onAreaSelectCallback = callback;
    }
    
    getSelectedArea() {
        return this.selectedArea;
    }
    
    resetSelection() {
        this.clearAllSelections();
        this.selectedArea = null;
        this.selectedAreaMarker = null;
    }
    
    // Public method to select area from external button
    selectAreaFromButton(areaName) {
        console.log(`🎯 Button selected area: ${areaName}`);
        
        // Clear previous selection highlighting
        if (this.selectedArea && this.selectedArea !== areaName) {
            this.highlightArea(this.selectedArea, false);
        }
        
        // Set new selection
        this.selectedArea = areaName;
        this.showSelection(areaName);
        
        // Highlight the selected area permanently
        this.highlightArea(areaName, true);
    }
    
    // Public method for manual area highlighting (for button clicks)
    highlightAreaFromButton(areaName) {
        console.log(`🎯 Button triggered permanent highlight for: ${areaName}`);
        
        // Clear any existing highlights first
        Object.keys(this.submeshes).forEach(area => {
            this.highlightArea(area, false);
        });
        
        // Highlight the requested area permanently
        this.highlightArea(areaName, true);
        
        // Store as selected area for persistence
        this.selectedArea = areaName;
    }
    
    // Public method to clear button selection
    clearButtonSelection() {
        console.log(`🗑️ Clearing button selection`);
        
        if (this.selectedArea) {
            this.highlightArea(this.selectedArea, false);
            this.selectedArea = null;
        }
        
        this.clearAllSelections();
    }
    
    dispose() {
        // Clean up resources
        this.container.removeEventListener('mousemove', this.onMouseMove);
        this.container.removeEventListener('click', this.onMouseClick);
        this.container.removeEventListener('touchstart', this.onTouchStart);
        this.container.removeEventListener('touchmove', this.onTouchMove);
        window.removeEventListener('resize', this.onWindowResize);
        
        if (this.renderer) {
            this.renderer.dispose();
            this.container.removeChild(this.renderer.domElement);
        }
    }
}

// Export for use in main app
window.AreaPicker3D = AreaPicker3D;