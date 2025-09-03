"""
Coordinate Mapper for Medical AI Assistant

Handles coordinate transformations, safety validations, and template scaling
for injection points and risk zones.
"""

import numpy as np
import math
from typing import List, Dict, Any, Optional, Tuple
import logging

from models.schemas import (
    Point, 
    InjectionPoint, 
    RiskZone, 
    ValidationResult
)

logger = logging.getLogger(__name__)

class CoordinateMapper:
    """Service for coordinate transformations and safety validations."""
    
    def __init__(self):
        """Initialize coordinate mapper with safety rules."""
        self.min_distance_to_danger = {
            "high": 15.0,      # High risk zones - 15px minimum
            "critical": 20.0,  # Critical zones - 20px minimum  
            "moderate": 8.0,   # Moderate zones - 8px minimum
            "low": 0.0         # Low risk zones - no restriction
        }
        
        self.safety_rules = {
            "lips": {
                "max_points": 8,
                "min_point_distance": 5.0,
                "boundary_buffer": 3.0
            },
            "cheeks": {
                "max_points": 10,
                "min_point_distance": 8.0,
                "boundary_buffer": 5.0
            },
            "chin": {
                "max_points": 6,
                "min_point_distance": 10.0,
                "boundary_buffer": 5.0
            },
            "forehead": {
                "max_points": 8,
                "min_point_distance": 12.0,
                "boundary_buffer": 8.0
            }
        }
        
        logger.info("✅ CoordinateMapper initialized with safety rules")
    
    def validate_injection_safety(
        self, 
        injection_points: List[InjectionPoint],
        risk_zones: List[RiskZone],
        area: str
    ) -> List[InjectionPoint]:
        """
        Validate injection points against risk zones and safety rules.
        
        Args:
            injection_points: List of proposed injection points
            risk_zones: List of identified risk zones
            area: Treatment area name
            
        Returns:
            Filtered list of safe injection points
        """
        if not injection_points:
            return []
        
        validated_points = []
        safety_violations = []
        
        area_rules = self.safety_rules.get(area, self.safety_rules["lips"])
        
        for point in injection_points:
            try:
                # Check distance to danger zones
                is_safe, violations = self._check_danger_zone_distance(point, risk_zones)
                
                if not is_safe:
                    safety_violations.extend(violations)
                    logger.warning(f"⚠️ Point {point.label} violates safety rules: {violations}")
                    
                    # Add warnings to point instead of removing completely
                    point.warnings.extend(violations)
                    point.confidence *= 0.5  # Reduce confidence for unsafe points
                
                # Check minimum distance to other points
                if self._check_point_spacing(point, validated_points, area_rules["min_point_distance"]):
                    validated_points.append(point)
                else:
                    logger.debug(f"🔍 Point {point.label} too close to existing points")
            
            except Exception as e:
                logger.error(f"❌ Safety validation failed for {point.label}: {str(e)}")
                continue
        
        # Apply maximum point limit
        if len(validated_points) > area_rules["max_points"]:
            # Sort by confidence and take top points
            validated_points.sort(key=lambda p: p.confidence, reverse=True)
            validated_points = validated_points[:area_rules["max_points"]]
            logger.info(f"🔢 Limited to {area_rules['max_points']} points for {area}")
        
        logger.info(f"🛡️ Validated {len(validated_points)}/{len(injection_points)} injection points")
        return validated_points
    
    def _check_danger_zone_distance(
        self, 
        point: InjectionPoint, 
        risk_zones: List[RiskZone]
    ) -> Tuple[bool, List[str]]:
        """Check if injection point maintains safe distance from danger zones."""
        violations = []
        
        for zone in risk_zones:
            min_distance = self.min_distance_to_danger.get(zone.severity, 10.0)
            
            # Calculate distance from point to polygon
            distance = self._point_to_polygon_distance(point.position, zone.polygon)
            
            if distance < min_distance:
                violation_msg = f"Too close to {zone.name} ({distance:.1f}px < {min_distance}px required)"
                violations.append(violation_msg)
        
        return len(violations) == 0, violations
    
    def _check_point_spacing(
        self, 
        new_point: InjectionPoint,
        existing_points: List[InjectionPoint],
        min_distance: float
    ) -> bool:
        """Check if new point maintains minimum distance from existing points."""
        for existing_point in existing_points:
            distance = self._point_distance(new_point.position, existing_point.position)
            if distance < min_distance:
                return False
        return True
    
    def _point_distance(self, p1: Point, p2: Point) -> float:
        """Calculate Euclidean distance between two points."""
        dx = p1.x - p2.x
        dy = p1.y - p2.y
        return math.sqrt(dx * dx + dy * dy)
    
    def _point_to_polygon_distance(self, point: Point, polygon: List[Point]) -> float:
        """Calculate minimum distance from point to polygon edge."""
        if len(polygon) < 3:
            return float('inf')
        
        min_distance = float('inf')
        
        # Check distance to each edge of the polygon
        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]
            
            # Calculate distance from point to line segment
            edge_distance = self._point_to_line_segment_distance(point, p1, p2)
            min_distance = min(min_distance, edge_distance)
        
        return min_distance
    
    def _point_to_line_segment_distance(self, point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate distance from point to line segment."""
        # Vector from line_start to line_end
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        
        if dx == 0 and dy == 0:
            # Degenerate line segment - just point to point distance
            return self._point_distance(point, line_start)
        
        # Parameter t for projection of point onto line
        t = ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / (dx * dx + dy * dy)
        
        # Clamp t to [0, 1] to stay within line segment
        t = max(0, min(1, t))
        
        # Find closest point on line segment
        closest_x = line_start.x + t * dx
        closest_y = line_start.y + t * dy
        
        # Calculate distance
        closest_point = Point(x=closest_x, y=closest_y)
        return self._point_distance(point, closest_point)
    
    def scale_template_to_image(
        self,
        template_points: List[Dict[str, Any]],
        image_shape: Tuple[int, int]
    ) -> List[InjectionPoint]:
        """
        Scale template injection points to fit image dimensions.
        
        Args:
            template_points: Template point definitions with relative coordinates
            image_shape: Target image dimensions (height, width)
            
        Returns:
            Scaled injection points with pixel coordinates
        """
        if not template_points:
            return []
        
        h, w = image_shape
        scaled_points = []
        
        # Assume standard face proportions for template scaling
        face_width = w * 0.3   # Face typically 30% of image width
        face_height = h * 0.4  # Face typically 40% of image height
        face_center_x = w // 2
        face_center_y = h // 2
        
        for template_point in template_points:
            try:
                # Extract template coordinates (should be relative to face center)
                template_x = template_point.get("x_offset", 0.0)
                template_y = template_point.get("y_offset", 0.0)
                
                # Scale to image coordinates
                pixel_x = face_center_x + (template_x * face_width)
                pixel_y = face_center_y + (template_y * face_height)
                
                # Clamp to image boundaries
                pixel_x = max(10, min(w - 10, pixel_x))
                pixel_y = max(10, min(h - 10, pixel_y))
                
                # Create scaled injection point
                scaled_point = InjectionPoint(
                    label=f"{template_point.get('label', 'Template Point')} (approximated)",
                    position=Point(x=pixel_x, y=pixel_y),
                    code=template_point.get("code"),
                    depth=template_point.get("depth", "dermal"),
                    technique=template_point.get("technique", "standard"),
                    volume=template_point.get("volume", "as recommended"),
                    tool=template_point.get("tool", "needle"),
                    confidence=0.3,  # Low confidence for templates
                    warnings=[
                        "Template-based positioning - verification required",
                        "Anatomical landmarks not detected"
                    ],
                    notes="Scaled from fallback template"
                )
                
                scaled_points.append(scaled_point)
                
            except Exception as e:
                logger.error(f"❌ Failed to scale template point: {str(e)}")
                continue
        
        logger.info(f"📐 Scaled {len(scaled_points)} template points to image size {w}x{h}")
        return scaled_points
    
    def transform_coordinates(
        self,
        points: List[Point],
        source_shape: Tuple[int, int],
        target_shape: Tuple[int, int]
    ) -> List[Point]:
        """
        Transform coordinates between different image sizes.
        
        Args:
            points: List of points to transform
            source_shape: Original image dimensions (height, width)
            target_shape: Target image dimensions (height, width)
            
        Returns:
            Transformed points
        """
        if not points or source_shape == target_shape:
            return points
        
        source_h, source_w = source_shape
        target_h, target_w = target_shape
        
        # Calculate scaling factors
        scale_x = target_w / source_w
        scale_y = target_h / source_h
        
        transformed_points = []
        
        for point in points:
            new_x = point.x * scale_x
            new_y = point.y * scale_y
            
            # Ensure points stay within bounds
            new_x = max(0, min(target_w - 1, new_x))
            new_y = max(0, min(target_h - 1, new_y))
            
            transformed_points.append(Point(x=new_x, y=new_y))
        
        return transformed_points
    
    def snap_to_grid(self, points: List[Point], grid_size: int = 2) -> List[Point]:
        """
        Snap points to grid for visual consistency.
        
        Args:
            points: Points to snap
            grid_size: Grid spacing in pixels
            
        Returns:
            Grid-snapped points
        """
        snapped_points = []
        
        for point in points:
            snapped_x = round(point.x / grid_size) * grid_size
            snapped_y = round(point.y / grid_size) * grid_size
            
            snapped_points.append(Point(x=snapped_x, y=snapped_y))
        
        return snapped_points
    
    def calculate_face_measurements(self, landmarks: Dict[str, Point]) -> Dict[str, float]:
        """
        Calculate standard facial measurements for proportion validation.
        
        Args:
            landmarks: Dictionary of named landmarks
            
        Returns:
            Dictionary of facial measurements
        """
        measurements = {}
        
        try:
            # Inter-pupillary distance
            if "left_eye_center" in landmarks and "right_eye_center" in landmarks:
                ipd = self._point_distance(
                    landmarks["left_eye_center"],
                    landmarks["right_eye_center"]
                )
                measurements["inter_pupillary_distance"] = ipd
            
            # Eye to mouth distance
            if "left_eye_center" in landmarks and "upper_lip_center" in landmarks:
                eye_mouth_distance = self._point_distance(
                    landmarks["left_eye_center"],
                    landmarks["upper_lip_center"]
                )
                measurements["eye_to_mouth"] = eye_mouth_distance
            
            # Mouth width
            if "left_mouth_corner" in landmarks and "right_mouth_corner" in landmarks:
                mouth_width = self._point_distance(
                    landmarks["left_mouth_corner"],
                    landmarks["right_mouth_corner"]
                )
                measurements["mouth_width"] = mouth_width
            
            # Face width (eye outer corners)
            if "left_eye_outer" in landmarks and "right_eye_outer" in landmarks:
                face_width = self._point_distance(
                    landmarks["left_eye_outer"],
                    landmarks["right_eye_outer"]
                )
                measurements["face_width"] = face_width
            
            # Nose width
            if "left_alae" in landmarks and "right_alae" in landmarks:
                nose_width = self._point_distance(
                    landmarks["left_alae"],
                    landmarks["right_alae"]
                )
                measurements["nose_width"] = nose_width
            
        except Exception as e:
            logger.error(f"❌ Face measurement calculation failed: {str(e)}")
        
        return measurements
    
    def validate_proportions(self, measurements: Dict[str, float]) -> Dict[str, bool]:
        """
        Validate facial proportions against standard ranges.
        
        Args:
            measurements: Facial measurements dictionary
            
        Returns:
            Dictionary of proportion validation results
        """
        validations = {}
        
        try:
            # Golden ratio checks
            if "mouth_width" in measurements and "nose_width" in measurements:
                mouth_nose_ratio = measurements["mouth_width"] / measurements["nose_width"]
                validations["mouth_nose_ratio_ok"] = 1.4 <= mouth_nose_ratio <= 1.8
            
            # Inter-pupillary to face width ratio
            if "inter_pupillary_distance" in measurements and "face_width" in measurements:
                ipd_face_ratio = measurements["inter_pupillary_distance"] / measurements["face_width"]
                validations["ipd_face_ratio_ok"] = 0.25 <= ipd_face_ratio <= 0.35
            
            # Eye to mouth proportion
            if "eye_to_mouth" in measurements and "inter_pupillary_distance" in measurements:
                eye_mouth_ipd_ratio = measurements["eye_to_mouth"] / measurements["inter_pupillary_distance"]
                validations["eye_mouth_proportion_ok"] = 0.8 <= eye_mouth_ipd_ratio <= 1.2
            
        except Exception as e:
            logger.error(f"❌ Proportion validation failed: {str(e)}")
        
        return validations
    
    def filter_overlapping_zones(self, risk_zones: List[RiskZone]) -> List[RiskZone]:
        """
        Remove or merge overlapping risk zones to reduce visual clutter.
        
        Args:
            risk_zones: List of risk zones to filter
            
        Returns:
            Filtered list without significant overlaps
        """
        if len(risk_zones) <= 1:
            return risk_zones
        
        filtered_zones = []
        
        # Sort by severity (critical first)
        severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
        sorted_zones = sorted(
            risk_zones,
            key=lambda z: severity_order.get(z.severity, 3)
        )
        
        for zone in sorted_zones:
            # Check if this zone significantly overlaps with any already added zone
            overlaps_significantly = False
            
            for existing_zone in filtered_zones:
                if self._zones_overlap_significantly(zone, existing_zone):
                    overlaps_significantly = True
                    break
            
            if not overlaps_significantly:
                filtered_zones.append(zone)
            else:
                logger.debug(f"🔍 Filtered overlapping zone: {zone.name}")
        
        return filtered_zones
    
    def _zones_overlap_significantly(self, zone1: RiskZone, zone2: RiskZone, threshold: float = 0.5) -> bool:
        """Check if two zones overlap significantly."""
        try:
            # Simplified overlap detection using bounding boxes
            bbox1 = self._get_polygon_bbox(zone1.polygon)
            bbox2 = self._get_polygon_bbox(zone2.polygon)
            
            # Calculate intersection area
            intersect_x1 = max(bbox1["x"], bbox2["x"])
            intersect_y1 = max(bbox1["y"], bbox2["y"])
            intersect_x2 = min(bbox1["x"] + bbox1["width"], bbox2["x"] + bbox2["width"])
            intersect_y2 = min(bbox1["y"] + bbox1["height"], bbox2["y"] + bbox2["height"])
            
            if intersect_x1 >= intersect_x2 or intersect_y1 >= intersect_y2:
                return False  # No intersection
            
            intersect_area = (intersect_x2 - intersect_x1) * (intersect_y2 - intersect_y1)
            
            # Calculate areas
            area1 = bbox1["width"] * bbox1["height"]
            area2 = bbox2["width"] * bbox2["height"]
            
            # Check if intersection is significant relative to smaller zone
            smaller_area = min(area1, area2)
            overlap_ratio = intersect_area / smaller_area
            
            return overlap_ratio > threshold
            
        except Exception:
            return False
    
    def _get_polygon_bbox(self, polygon: List[Point]) -> Dict[str, float]:
        """Get bounding box of polygon."""
        if not polygon:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        min_x = min(p.x for p in polygon)
        max_x = max(p.x for p in polygon)
        min_y = min(p.y for p in polygon)
        max_y = max(p.y for p in polygon)
        
        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y
        }