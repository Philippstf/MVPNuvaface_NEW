"""
Knowledge Loader for Medical AI Assistant

Loads and manages YAML knowledge base files containing MD Codes,
injection points, risk zones, and medical guidelines.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass
import asyncio
from datetime import datetime

from models.schemas import AreaKnowledge, FallbackTemplate, TreatmentArea

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeEntry:
    """Single knowledge base entry."""
    area: str
    type: str  # 'injection_points', 'risk_zones', 'anatomy', etc.
    data: Dict[str, Any]
    file_path: str
    last_modified: float
    version: str = "1.0"

class KnowledgeLoader:
    """Service for loading and managing medical knowledge base."""
    
    def __init__(self, knowledge_base_path: str = None):
        """Initialize knowledge loader."""
        if knowledge_base_path is None:
            # Default to assets/knowledge in project root
            project_root = Path(__file__).parent.parent.parent
            self.knowledge_base_path = project_root / "assets" / "knowledge"
        else:
            self.knowledge_base_path = Path(knowledge_base_path)
        
        self.knowledge_cache: Dict[str, KnowledgeEntry] = {}
        self.area_knowledge_cache: Dict[str, AreaKnowledge] = {}
        self.fallback_templates: Dict[str, FallbackTemplate] = {}
        
        # Supported treatment areas
        self.supported_areas = ["lips", "cheeks", "chin", "forehead"]
        
        # File type mappings
        self.file_types = {
            "injection_points.yaml": "injection_points",
            "risk_zones.yaml": "risk_zones",
            "md_codes.yaml": "md_codes",
            "anatomy.yaml": "anatomy",
            "safety.yaml": "safety"
        }
        
        logger.info(f"✅ KnowledgeLoader initialized with path: {self.knowledge_base_path}")
    
    def is_healthy(self) -> bool:
        """Check if knowledge loader is healthy."""
        return (
            self.knowledge_base_path.exists() and 
            self.knowledge_base_path.is_dir() and
            len(self.area_knowledge_cache) > 0
        )
    
    async def warm_up(self):
        """Warm up by loading all knowledge base files."""
        try:
            logger.info("🔥 Warming up knowledge base...")
            
            # Load common knowledge
            await self._load_common_knowledge()
            
            # Load area-specific knowledge
            for area in self.supported_areas:
                await self._load_area_knowledge(area)
            
            # Load fallback templates
            await self._load_fallback_templates()
            
            logger.info(f"✅ Knowledge base warmed up: {len(self.area_knowledge_cache)} areas loaded")
            
        except Exception as e:
            logger.error(f"❌ Knowledge base warm-up failed: {str(e)}")
            raise
    
    async def load_area_knowledge(self, area: str) -> Optional[AreaKnowledge]:
        """
        Load knowledge base for specific treatment area.
        
        Args:
            area: Treatment area name (lips, cheeks, chin, forehead)
            
        Returns:
            AreaKnowledge object or None if not found
        """
        if area not in self.supported_areas:
            logger.warning(f"⚠️ Unsupported area: {area}")
            return None
        
        # Check cache first
        if area in self.area_knowledge_cache:
            return self.area_knowledge_cache[area]
        
        # Load from files
        try:
            knowledge = await self._load_area_knowledge(area)
            return knowledge
        except Exception as e:
            logger.error(f"❌ Failed to load knowledge for {area}: {str(e)}")
            return None
    
    async def load_fallback_templates(self, area: str) -> Optional[FallbackTemplate]:
        """
        Load fallback templates for when landmark detection fails.
        
        Args:
            area: Treatment area name
            
        Returns:
            FallbackTemplate object or None if not found
        """
        if area in self.fallback_templates:
            return self.fallback_templates[area]
        
        try:
            # Try to load from fallback template file
            template_path = self.knowledge_base_path / area / "fallback_template.yaml"
            
            if template_path.exists():
                template_data = await self._load_yaml_file(template_path)
                
                fallback_template = FallbackTemplate(
                    area=TreatmentArea(area),
                    injection_points=template_data.get("injection_points", []),
                    confidence_penalty=template_data.get("confidence_penalty", 0.5)
                )
                
                self.fallback_templates[area] = fallback_template
                return fallback_template
            else:
                # Generate basic fallback template
                logger.info(f"🔄 Generating basic fallback template for {area}")
                return self._generate_basic_fallback_template(area)
                
        except Exception as e:
            logger.error(f"❌ Failed to load fallback template for {area}: {str(e)}")
            return None
    
    async def _load_common_knowledge(self):
        """Load common knowledge files (anatomy, safety, etc.)."""
        common_path = self.knowledge_base_path / "common"
        
        if not common_path.exists():
            logger.warning("⚠️ Common knowledge directory not found")
            return
        
        common_files = [
            "anatomy_references.yaml",
            "safety_guidelines.yaml", 
            "md_codes_index.yaml"
        ]
        
        for filename in common_files:
            file_path = common_path / filename
            if file_path.exists():
                try:
                    data = await self._load_yaml_file(file_path)
                    
                    entry = KnowledgeEntry(
                        area="common",
                        type=filename.replace(".yaml", ""),
                        data=data,
                        file_path=str(file_path),
                        last_modified=file_path.stat().st_mtime
                    )
                    
                    cache_key = f"common_{entry.type}"
                    self.knowledge_cache[cache_key] = entry
                    
                    logger.debug(f"📚 Loaded common knowledge: {filename}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to load {filename}: {str(e)}")
    
    async def _load_area_knowledge(self, area: str) -> Optional[AreaKnowledge]:
        """Load knowledge for specific treatment area."""
        area_path = self.knowledge_base_path / area
        
        if not area_path.exists():
            logger.warning(f"⚠️ Knowledge directory not found for {area}")
            return None
        
        injection_points = []
        risk_zones = []
        
        # Load injection points
        injection_points_file = area_path / "injection_points.yaml"
        if injection_points_file.exists():
            try:
                data = await self._load_yaml_file(injection_points_file)
                injection_points = data.get("points", [])
                logger.debug(f"💉 Loaded {len(injection_points)} injection points for {area}")
            except Exception as e:
                logger.error(f"❌ Failed to load injection points for {area}: {str(e)}")
        
        # Load risk zones
        risk_zones_file = area_path / "risk_zones.yaml"
        if risk_zones_file.exists():
            try:
                data = await self._load_yaml_file(risk_zones_file)
                risk_zones = data.get("zones", [])
                logger.debug(f"🚨 Loaded {len(risk_zones)} risk zones for {area}")
            except Exception as e:
                logger.error(f"❌ Failed to load risk zones for {area}: {str(e)}")
        
        # Create AreaKnowledge object
        area_knowledge = AreaKnowledge(
            area=TreatmentArea(area),
            injection_points=injection_points,
            risk_zones=risk_zones,
            version="1.0",
            last_updated=int(datetime.now().timestamp())
        )
        
        # Cache the result
        self.area_knowledge_cache[area] = area_knowledge
        
        logger.info(f"📚 Loaded knowledge for {area}: {len(injection_points)} points, {len(risk_zones)} zones")
        return area_knowledge
    
    async def _load_fallback_templates(self):
        """Load fallback templates for all areas."""
        for area in self.supported_areas:
            try:
                template = await self.load_fallback_templates(area)
                if template:
                    self.fallback_templates[area] = template
            except Exception as e:
                logger.error(f"❌ Failed to load fallback template for {area}: {str(e)}")
    
    def _generate_basic_fallback_template(self, area: str) -> FallbackTemplate:
        """Generate basic fallback template when no template file exists."""
        
        # Basic template points based on standard facial proportions
        basic_templates = {
            "lips": [
                {
                    "label": "Upper Lip Center (Template)",
                    "x_offset": 0.0,
                    "y_offset": 0.1,
                    "depth": "dermal",
                    "technique": "linear threading",
                    "volume": "0.1-0.2 ml",
                    "code": "LP2"
                },
                {
                    "label": "Lower Lip Center (Template)", 
                    "x_offset": 0.0,
                    "y_offset": 0.15,
                    "depth": "subcutaneous",
                    "technique": "linear threading",
                    "volume": "0.2-0.3 ml",
                    "code": "LP3"
                }
            ],
            "cheeks": [
                {
                    "label": "Left High Malar (Template)",
                    "x_offset": -0.12,
                    "y_offset": -0.05,
                    "depth": "supraperiosteal",
                    "technique": "bolus injection",
                    "volume": "0.3-0.5 ml",
                    "code": "CK1"
                },
                {
                    "label": "Right High Malar (Template)",
                    "x_offset": 0.12,
                    "y_offset": -0.05,
                    "depth": "supraperiosteal",
                    "technique": "bolus injection",
                    "volume": "0.3-0.5 ml",
                    "code": "CK1"
                }
            ],
            "chin": [
                {
                    "label": "Central Pogonion (Template)",
                    "x_offset": 0.0,
                    "y_offset": 0.25,
                    "depth": "supraperiosteal",
                    "technique": "bolus injection", 
                    "volume": "0.3-0.8 ml",
                    "code": "CH1"
                }
            ],
            "forehead": [
                {
                    "label": "Left Medial Frontalis (Template)",
                    "x_offset": -0.08,
                    "y_offset": -0.15,
                    "depth": "muscle belly",
                    "technique": "intramuscular injection",
                    "volume": "4-6 units",
                    "code": "FH2"
                },
                {
                    "label": "Right Medial Frontalis (Template)",
                    "x_offset": 0.08,
                    "y_offset": -0.15,
                    "depth": "muscle belly",
                    "technique": "intramuscular injection",
                    "volume": "4-6 units",
                    "code": "FH2"
                }
            ]
        }
        
        template_points = basic_templates.get(area, [])
        
        fallback_template = FallbackTemplate(
            area=TreatmentArea(area),
            injection_points=template_points,
            confidence_penalty=0.7  # Higher penalty for generated templates
        )
        
        logger.info(f"🔄 Generated basic fallback template for {area} with {len(template_points)} points")
        return fallback_template
    
    async def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                return data if data is not None else {}
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parsing error in {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to read {file_path}: {str(e)}")
            raise
    
    def get_md_codes_for_area(self, area: str) -> Dict[str, Any]:
        """Get MD codes specific to treatment area."""
        # First check area-specific MD codes
        area_md_codes = self.knowledge_cache.get(f"{area}_md_codes")
        if area_md_codes:
            return area_md_codes.data
        
        # Fall back to common MD codes index
        common_md_codes = self.knowledge_cache.get("common_md_codes_index")
        if common_md_codes:
            area_codes = {}
            for code_type in [f"{area}_md_codes", f"{area.upper()}_codes"]:
                if code_type in common_md_codes.data:
                    area_codes.update(common_md_codes.data[code_type])
            return area_codes
        
        return {}
    
    def get_safety_guidelines(self, area: str = None) -> Dict[str, Any]:
        """Get safety guidelines, optionally filtered by area."""
        safety_guidelines = self.knowledge_cache.get("common_safety_guidelines")
        
        if not safety_guidelines:
            return {}
        
        if area:
            # Return area-specific guidelines
            area_guidelines = safety_guidelines.data.get(f"{area}_guidelines", {})
            general_guidelines = safety_guidelines.data.get("general_rules", {})
            
            return {
                "general": general_guidelines,
                "area_specific": area_guidelines
            }
        
        return safety_guidelines.data
    
    def get_anatomy_references(self, area: str = None) -> Dict[str, Any]:
        """Get anatomical references, optionally filtered by area."""
        anatomy_refs = self.knowledge_cache.get("common_anatomy_references")
        
        if not anatomy_refs:
            return {}
        
        if area:
            # Filter for area-specific anatomy
            area_anatomy = {}
            for key, value in anatomy_refs.data.items():
                if area in key.lower() or "general" in key.lower() or "common" in key.lower():
                    area_anatomy[key] = value
            return area_anatomy
        
        return anatomy_refs.data
    
    async def reload_knowledge_base(self, area: str = None):
        """Reload knowledge base files (useful for development)."""
        if area:
            # Reload specific area
            if area in self.area_knowledge_cache:
                del self.area_knowledge_cache[area]
            if area in self.fallback_templates:
                del self.fallback_templates[area]
            
            await self._load_area_knowledge(area)
            await self.load_fallback_templates(area)
            
            logger.info(f"🔄 Reloaded knowledge base for {area}")
        else:
            # Reload all
            self.knowledge_cache.clear()
            self.area_knowledge_cache.clear()
            self.fallback_templates.clear()
            
            await self.warm_up()
            logger.info("🔄 Reloaded entire knowledge base")
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded knowledge base."""
        stats = {
            "areas_loaded": len(self.area_knowledge_cache),
            "common_files": len([k for k in self.knowledge_cache.keys() if k.startswith("common_")]),
            "fallback_templates": len(self.fallback_templates),
            "knowledge_base_path": str(self.knowledge_base_path),
            "supported_areas": self.supported_areas,
            "area_details": {}
        }
        
        for area, knowledge in self.area_knowledge_cache.items():
            stats["area_details"][area] = {
                "injection_points": len(knowledge.injection_points),
                "risk_zones": len(knowledge.risk_zones),
                "version": knowledge.version,
                "last_updated": knowledge.last_updated
            }
        
        return stats
    
    def validate_knowledge_integrity(self) -> Dict[str, List[str]]:
        """Validate knowledge base integrity and return any issues."""
        issues = {
            "missing_files": [],
            "invalid_yaml": [],
            "missing_required_fields": [],
            "warnings": []
        }
        
        # Check required directories
        for area in self.supported_areas:
            area_path = self.knowledge_base_path / area
            if not area_path.exists():
                issues["missing_files"].append(f"Directory missing: {area}")
                continue
            
            # Check required files
            required_files = ["injection_points.yaml", "risk_zones.yaml"]
            for filename in required_files:
                file_path = area_path / filename
                if not file_path.exists():
                    issues["missing_files"].append(f"File missing: {area}/{filename}")
        
        # Check common directory
        common_path = self.knowledge_base_path / "common"
        if not common_path.exists():
            issues["missing_files"].append("Common knowledge directory missing")
        
        # Validate loaded knowledge
        for area, knowledge in self.area_knowledge_cache.items():
            if len(knowledge.injection_points) == 0:
                issues["warnings"].append(f"No injection points defined for {area}")
            
            if len(knowledge.risk_zones) == 0:
                issues["warnings"].append(f"No risk zones defined for {area}")
        
        return issues