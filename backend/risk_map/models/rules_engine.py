"""
Rules Engine for Medical AI Assistant

Converts YAML rule definitions into pixel coordinates for injection points
and risk zones using facial landmarks as anchors.
"""

import numpy as np
import cv2
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import math

from models.schemas import (
    Point, 
    RiskZone, 
    InjectionPoint, 
    NormalizedFace, 
    RuleDefinition
)

logger = logging.getLogger(__name__)

@dataclass
class RuleContext:
    """Context information for rule execution."""
    landmarks: Dict[str, Point]
    face_bbox: Dict[str, float]
    image_shape: Tuple[int, int]
    area: str
    confidence: float

class RulesEngine:
    """Engine for applying YAML rules to generate coordinates."""
    
    def __init__(self):
        """Initialize the rules engine with supported rule types."""
        self.supported_rule_types = {
            "landmark_vector_offset": self._apply_landmark_vector_offset,
            "polyline_buffer_from_landmarks": self._apply_polyline_buffer,
            "circle_around_landmark": self._apply_circle_around_landmark,
            "ellipse_around_landmarks": self._apply_ellipse_around_landmarks,
            "polygon_from_landmarks": self._apply_polygon_from_landmarks,
            "bone_point": self._apply_bone_point,
            "mask_from_landmark_loop": self._apply_mask_from_landmarks
        }
        
        logger.info("✅ Rules engine initialized with {} rule types".format(len(self.supported_rule_types)))
    
    def is_healthy(self) -> bool:
        """Check if the rules engine is healthy."""
        return len(self.supported_rule_types) > 0
    
    def apply_injection_point_rules(
        self, 
        point_definitions: List[Dict[str, Any]], 
        normalized_face: NormalizedFace,
        image_shape: Tuple[int, int]
    ) -> List[InjectionPoint]:
        """
        Apply injection point rules to generate coordinates.
        
        Args:
            point_definitions: YAML injection point definitions
            normalized_face: Normalized face landmarks
            image_shape: Original image dimensions
            
        Returns:
            List of injection points with pixel coordinates
        """
        injection_points = []
        
        # Create rule context
        context = self._create_rule_context(normalized_face, image_shape)
        
        for point_def in point_definitions:
            try:
                # Extract rule definition
                rule = point_def.get("rule", {})
                rule_type = rule.get("type")
                
                if rule_type not in self.supported_rule_types:
                    logger.warning(f"⚠️ Unsupported rule type: {rule_type}")
                    continue
                
                # Apply rule to get coordinates
                coordinates = self.supported_rule_types[rule_type](rule, context)
                
                if coordinates:
                    # Create injection point
                    injection_point = InjectionPoint(
                        label=point_def.get("label", "Unknown Point"),
                        position=coordinates,
                        code=point_def.get("md_code"),
                        depth=point_def.get("depth"),
                        technique=point_def.get("technique"),
                        volume=point_def.get("volume_recommendation"),
                        tool=point_def.get("tool"),
                        notes=point_def.get("notes"),
                        confidence=context.confidence * 0.9,  # Slight reduction for rule application
                        warnings=point_def.get("warnings", []),
                        source={
                            "md_code": point_def.get("md_code"),
                            "rule_type": rule_type,
                            "id": point_def.get("id")
                        }
                    )
                    
                    injection_points.append(injection_point)
                    logger.debug(f"✅ Generated injection point: {injection_point.label}")
                
            except Exception as e:
                logger.error(f"❌ Failed to apply rule for {point_def.get('label', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"🎯 Generated {len(injection_points)} injection points")
        return injection_points
    
    def apply_risk_zone_rules(
        self,
        zone_definitions: List[Dict[str, Any]],
        normalized_face: NormalizedFace,
        image_shape: Tuple[int, int]
    ) -> List[RiskZone]:
        """
        Apply risk zone rules to generate danger area polygons.
        
        Args:
            zone_definitions: YAML risk zone definitions
            normalized_face: Normalized face landmarks
            image_shape: Original image dimensions
            
        Returns:
            List of risk zones with polygon coordinates
        """
        risk_zones = []
        
        # Create rule context
        context = self._create_rule_context(normalized_face, image_shape)
        
        for zone_def in zone_definitions:
            try:
                # Extract rule definition
                rule = zone_def.get("rule", {})
                rule_type = rule.get("type")
                
                if rule_type not in self.supported_rule_types:
                    logger.warning(f"⚠️ Unsupported rule type: {rule_type}")
                    continue
                
                # Apply rule to get polygon coordinates
                polygon_points = self.supported_rule_types[rule_type](rule, context)
                
                if polygon_points and len(polygon_points) >= 3:
                    # Create risk zone
                    risk_zone = RiskZone(
                        name=zone_def.get("name", "Unknown Zone"),
                        polygon=polygon_points if isinstance(polygon_points, list) else [polygon_points],
                        severity=zone_def.get("severity", "moderate"),
                        color=zone_def.get("color", "#FF4D4D"),
                        opacity=zone_def.get("opacity", 0.25),
                        tooltip=zone_def.get("tooltip"),
                        medical_reference=zone_def.get("medical_reference"),
                        rationale=zone_def.get("rationale"),
                        safety_recommendations=zone_def.get("safety_recommendations", []),
                        consequences=zone_def.get("consequences", []),
                        style={
                            "stroke_style": rule.get("style", "solid"),
                            "rule_type": rule_type
                        }
                    )
                    
                    risk_zones.append(risk_zone)
                    logger.debug(f"🚨 Generated risk zone: {risk_zone.name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to apply rule for {zone_def.get('name', 'unknown')}: {str(e)}")
                continue
        
        logger.info(f"🚨 Generated {len(risk_zones)} risk zones")
        return risk_zones
    
    def _create_rule_context(self, normalized_face: NormalizedFace, image_shape: Tuple[int, int]) -> RuleContext:
        """Create context for rule execution."""
        
        # Convert normalized landmarks back to pixel coordinates
        w, h = image_shape
        pixel_landmarks = {}
        
        # We need to map the normalized landmarks back to named landmarks
        # This would typically come from the landmark detector's get_key_landmarks method
        # For now, we'll create a basic mapping
        
        if len(normalized_face.landmarks) >= 468:
            # Map key landmarks by index (MediaPipe indices)
            landmark_mapping = {
                "left_eye_inner": 133,
                "left_eye_outer": 33,
                "right_eye_inner": 362,
                "right_eye_outer": 263,
                "nose_tip": 1,
                "nose_bridge_high": 6,
                "left_alae": 31,
                "right_alae": 261,
                "upper_lip_center": 13,
                "lower_lip_center": 14,
                "left_mouth_corner": 61,
                "right_mouth_corner": 291,
                "left_eyebrow_inner": 70,
                "left_eyebrow_center": 107,
                "left_eyebrow_peak": 105,
                "right_eyebrow_inner": 300,
                "right_eyebrow_center": 336,
                "right_eyebrow_peak": 334,
                "chin_tip": 175,
                "forehead_center": 9
            }
            
            # Convert normalized coordinates to pixel coordinates
            bbox = normalized_face.face_bbox
            for name, index in landmark_mapping.items():
                if index < len(normalized_face.landmarks):
                    norm_point = normalized_face.landmarks[index]
                    # Convert from normalized [0,1] space back to pixels
                    pixel_x = norm_point.x * bbox["width"] + bbox["x"]
                    pixel_y = norm_point.y * bbox["height"] + bbox["y"]
                    pixel_landmarks[name] = Point(x=pixel_x, y=pixel_y)
        
        # Calculate derived landmarks
        if "left_eye_inner" in pixel_landmarks and "left_eye_outer" in pixel_landmarks:
            left_center = Point(
                x=(pixel_landmarks["left_eye_inner"].x + pixel_landmarks["left_eye_outer"].x) / 2,
                y=(pixel_landmarks["left_eye_inner"].y + pixel_landmarks["left_eye_outer"].y) / 2
            )
            pixel_landmarks["left_eye_center"] = left_center
            
        if "right_eye_inner" in pixel_landmarks and "right_eye_outer" in pixel_landmarks:
            right_center = Point(
                x=(pixel_landmarks["right_eye_inner"].x + pixel_landmarks["right_eye_outer"].x) / 2,
                y=(pixel_landmarks["right_eye_inner"].y + pixel_landmarks["right_eye_outer"].y) / 2
            )
            pixel_landmarks["right_eye_center"] = right_center
        
        if "left_eyebrow_center" in pixel_landmarks and "right_eyebrow_center" in pixel_landmarks:
            eyebrow_midpoint = Point(
                x=(pixel_landmarks["left_eyebrow_center"].x + pixel_landmarks["right_eyebrow_center"].x) / 2,
                y=(pixel_landmarks["left_eyebrow_center"].y + pixel_landmarks["right_eyebrow_center"].y) / 2
            )
            pixel_landmarks["eyebrow_center_midpoint"] = eyebrow_midpoint
        
        return RuleContext(
            landmarks=pixel_landmarks,
            face_bbox=normalized_face.face_bbox,
            image_shape=image_shape,
            area="unknown",  # This would be set by the caller
            confidence=normalized_face.confidence
        )
    
    def _apply_landmark_vector_offset(self, rule: Dict[str, Any], context: RuleContext) -> Optional[Point]:
        """Apply landmark vector offset rule."""
        try:
            anchors = rule.get("anchors", [])
            anchor_weights = rule.get("anchor_weights", [1.0] * len(anchors))
            offset_percent = rule.get("offset_percent", {"x": 0.0, "y": 0.0})
            
            if len(anchors) == 0:
                return None
            
            # Calculate weighted average of anchor points
            total_weight = sum(anchor_weights)
            weighted_x = 0.0
            weighted_y = 0.0
            
            for i, anchor_name in enumerate(anchors):
                if anchor_name not in context.landmarks:
                    logger.warning(f"⚠️ Anchor {anchor_name} not found in landmarks")
                    continue
                
                weight = anchor_weights[i] if i < len(anchor_weights) else 1.0
                anchor_point = context.landmarks[anchor_name]
                
                weighted_x += anchor_point.x * weight
                weighted_y += anchor_point.y * weight
            
            if total_weight == 0:
                return None
            
            # Calculate base position
            base_x = weighted_x / total_weight
            base_y = weighted_y / total_weight
            
            # Apply percentage offset relative to face bounding box
            bbox = context.face_bbox
            offset_x = offset_percent["x"] * bbox["width"]
            offset_y = offset_percent["y"] * bbox["height"]
            
            final_x = base_x + offset_x
            final_y = base_y + offset_y
            
            # Clamp to image boundaries
            final_x = max(0, min(context.image_shape[1] - 1, final_x))
            final_y = max(0, min(context.image_shape[0] - 1, final_y))
            
            return Point(x=final_x, y=final_y)
            
        except Exception as e:
            logger.error(f"❌ landmark_vector_offset rule failed: {str(e)}")
            return None
    
    def _apply_polyline_buffer(self, rule: Dict[str, Any], context: RuleContext) -> Optional[List[Point]]:
        """Apply polyline buffer rule to create risk zone polygon."""
        try:
            anchors = rule.get("anchors", [])
            buffer_px = rule.get("buffer_px", 5)
            shape = rule.get("shape", "straight_line")
            
            if len(anchors) < 2:
                return None
            
            # Get anchor points
            anchor_points = []
            for anchor_name in anchors:
                if anchor_name in context.landmarks:
                    anchor_points.append(context.landmarks[anchor_name])
            
            if len(anchor_points) < 2:
                return None
            
            # Create polyline
            polyline_points = []
            if shape == "curved_polyline":
                # Use spline interpolation for smooth curves
                polyline_points = self._create_smooth_curve(anchor_points)
            else:
                # Straight line segments
                polyline_points = anchor_points
            
            # Create buffer polygon around polyline
            buffered_polygon = self._create_line_buffer(polyline_points, buffer_px)
            
            return buffered_polygon
            
        except Exception as e:
            logger.error(f"❌ polyline_buffer rule failed: {str(e)}")
            return None
    
    def _apply_circle_around_landmark(self, rule: Dict[str, Any], context: RuleContext) -> Optional[List[Point]]:
        """Apply circular rule around landmark(s)."""
        try:
            anchors = rule.get("anchors", [])
            radius_px = rule.get("radius_px", 10)
            offset_percent = rule.get("offset_percent", {"x": 0.0, "y": 0.0})
            bilateral = rule.get("bilateral", False)
            
            circles = []
            
            for anchor_name in anchors:
                if anchor_name not in context.landmarks:
                    continue
                
                center = context.landmarks[anchor_name]
                
                # Apply offset
                bbox = context.face_bbox
                offset_x = offset_percent.get("x", 0.0) * bbox["width"]
                offset_y = offset_percent.get("y", 0.0) * bbox["height"]
                
                adjusted_center = Point(
                    x=center.x + offset_x,
                    y=center.y + offset_y
                )
                
                # Create circle polygon
                circle_points = self._create_circle_polygon(adjusted_center, radius_px)
                circles.extend(circle_points)
                
                # Handle bilateral (mirror for right side)
                if bilateral and "left" in anchor_name:
                    right_anchor_name = anchor_name.replace("left", "right")
                    if right_anchor_name in context.landmarks:
                        right_center = context.landmarks[right_anchor_name]
                        right_offset_x = offset_percent.get("x_right", -offset_percent.get("x", 0.0)) * bbox["width"]
                        right_adjusted_center = Point(
                            x=right_center.x + right_offset_x,
                            y=right_center.y + offset_y
                        )
                        right_circle_points = self._create_circle_polygon(right_adjusted_center, radius_px)
                        circles.extend(right_circle_points)
            
            return circles if circles else None
            
        except Exception as e:
            logger.error(f"❌ circle_around_landmark rule failed: {str(e)}")
            return None
    
    def _apply_ellipse_around_landmarks(self, rule: Dict[str, Any], context: RuleContext) -> Optional[List[Point]]:
        """Apply elliptical rule around landmarks."""
        try:
            anchors = rule.get("anchors", [])
            width = rule.get("width", 20)
            height = rule.get("height", 15)
            
            if len(anchors) == 0:
                return None
            
            # Calculate center from anchors
            center_x = sum(context.landmarks[name].x for name in anchors if name in context.landmarks) / len(anchors)
            center_y = sum(context.landmarks[name].y for name in anchors if name in context.landmarks) / len(anchors)
            
            center = Point(x=center_x, y=center_y)
            
            # Create ellipse polygon
            ellipse_points = self._create_ellipse_polygon(center, width, height)
            
            return ellipse_points
            
        except Exception as e:
            logger.error(f"❌ ellipse_around_landmarks rule failed: {str(e)}")
            return None
    
    def _apply_polygon_from_landmarks(self, rule: Dict[str, Any], context: RuleContext) -> Optional[List[Point]]:
        """Create polygon directly from landmarks."""
        try:
            anchors = rule.get("anchors", [])
            buffer_px = rule.get("buffer_px", 0)
            
            if len(anchors) < 3:
                return None
            
            # Get polygon vertices from landmarks
            polygon_points = []
            for anchor_name in anchors:
                if anchor_name in context.landmarks:
                    polygon_points.append(context.landmarks[anchor_name])
            
            if len(polygon_points) < 3:
                return None
            
            # Apply buffer if specified
            if buffer_px > 0:
                polygon_points = self._expand_polygon(polygon_points, buffer_px)
            
            return polygon_points
            
        except Exception as e:
            logger.error(f"❌ polygon_from_landmarks rule failed: {str(e)}")
            return None
    
    def _apply_bone_point(self, rule: Dict[str, Any], context: RuleContext) -> Optional[Point]:
        """Apply bone point rule for supraperiosteal injections."""
        try:
            anchors = rule.get("anchors", [])
            bone_direction = rule.get("bone_direction", "inward")
            depth_offset = rule.get("depth_offset", 2)
            
            if len(anchors) == 0:
                return None
            
            # Use first anchor as base
            base_point = context.landmarks[anchors[0]]
            
            # Calculate direction toward bone (simplified)
            if bone_direction == "inward":
                # Move slightly toward face center
                face_center_x = context.face_bbox["x"] + context.face_bbox["width"] / 2
                face_center_y = context.face_bbox["y"] + context.face_bbox["height"] / 2
                
                direction_x = (face_center_x - base_point.x) * 0.1
                direction_y = (face_center_y - base_point.y) * 0.1
            else:
                direction_x = 0
                direction_y = 0
            
            bone_point = Point(
                x=base_point.x + direction_x,
                y=base_point.y + direction_y
            )
            
            return bone_point
            
        except Exception as e:
            logger.error(f"❌ bone_point rule failed: {str(e)}")
            return None
    
    def _apply_mask_from_landmarks(self, rule: Dict[str, Any], context: RuleContext) -> Optional[List[Point]]:
        """Create mask polygon from landmark loop."""
        try:
            anchors = rule.get("anchors", [])
            
            if len(anchors) < 3:
                return None
            
            # Create polygon from landmark loop
            mask_points = []
            for anchor_name in anchors:
                if anchor_name in context.landmarks:
                    mask_points.append(context.landmarks[anchor_name])
            
            return mask_points if len(mask_points) >= 3 else None
            
        except Exception as e:
            logger.error(f"❌ mask_from_landmarks rule failed: {str(e)}")
            return None
    
    # Helper methods for geometric operations
    
    def _create_smooth_curve(self, points: List[Point], num_interpolated: int = 20) -> List[Point]:
        """Create smooth curve between points using spline interpolation."""
        if len(points) < 2:
            return points
        
        # Simple linear interpolation for now (could be enhanced with splines)
        curve_points = []
        for i in range(len(points) - 1):
            start = points[i]
            end = points[i + 1]
            
            for j in range(num_interpolated):
                t = j / num_interpolated
                interpolated = Point(
                    x=start.x + (end.x - start.x) * t,
                    y=start.y + (end.y - start.y) * t
                )
                curve_points.append(interpolated)
        
        curve_points.append(points[-1])  # Add final point
        return curve_points
    
    def _create_line_buffer(self, line_points: List[Point], buffer_px: float) -> List[Point]:
        """Create polygon buffer around line."""
        if len(line_points) < 2:
            return []
        
        # Simplified buffer creation
        buffer_polygon = []
        
        for i, point in enumerate(line_points):
            # Calculate perpendicular direction
            if i == 0:
                # Use direction to next point
                dx = line_points[i + 1].x - point.x
                dy = line_points[i + 1].y - point.y
            elif i == len(line_points) - 1:
                # Use direction from previous point
                dx = point.x - line_points[i - 1].x
                dy = point.y - line_points[i - 1].y
            else:
                # Use average direction
                dx1 = point.x - line_points[i - 1].x
                dy1 = point.y - line_points[i - 1].y
                dx2 = line_points[i + 1].x - point.x
                dy2 = line_points[i + 1].y - point.y
                dx = (dx1 + dx2) / 2
                dy = (dy1 + dy2) / 2
            
            # Normalize and create perpendicular
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                perp_x = -dy / length * buffer_px
                perp_y = dx / length * buffer_px
                
                # Add both sides of the buffer
                buffer_polygon.append(Point(x=point.x + perp_x, y=point.y + perp_y))
        
        # Add reverse direction for other side
        for i in range(len(line_points) - 1, -1, -1):
            point = line_points[i]
            if i == 0:
                dx = line_points[i + 1].x - point.x
                dy = line_points[i + 1].y - point.y
            elif i == len(line_points) - 1:
                dx = point.x - line_points[i - 1].x
                dy = point.y - line_points[i - 1].y
            else:
                dx1 = point.x - line_points[i - 1].x
                dy1 = point.y - line_points[i - 1].y
                dx2 = line_points[i + 1].x - point.x
                dy2 = line_points[i + 1].y - point.y
                dx = (dx1 + dx2) / 2
                dy = (dy1 + dy2) / 2
            
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                perp_x = dy / length * buffer_px
                perp_y = -dx / length * buffer_px
                
                buffer_polygon.append(Point(x=point.x + perp_x, y=point.y + perp_y))
        
        return buffer_polygon
    
    def _create_circle_polygon(self, center: Point, radius: float, num_points: int = 16) -> List[Point]:
        """Create polygon approximation of circle."""
        circle_points = []
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            circle_points.append(Point(x=x, y=y))
        
        return circle_points
    
    def _create_ellipse_polygon(self, center: Point, width: float, height: float, num_points: int = 16) -> List[Point]:
        """Create polygon approximation of ellipse."""
        ellipse_points = []
        
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = center.x + (width / 2) * math.cos(angle)
            y = center.y + (height / 2) * math.sin(angle)
            ellipse_points.append(Point(x=x, y=y))
        
        return ellipse_points
    
    def _expand_polygon(self, polygon: List[Point], buffer_px: float) -> List[Point]:
        """Expand polygon outward by buffer distance."""
        if len(polygon) < 3:
            return polygon
        
        # Calculate centroid
        centroid_x = sum(p.x for p in polygon) / len(polygon)
        centroid_y = sum(p.y for p in polygon) / len(polygon)
        
        # Expand each point away from centroid
        expanded_points = []
        for point in polygon:
            dx = point.x - centroid_x
            dy = point.y - centroid_y
            length = math.sqrt(dx * dx + dy * dy)
            
            if length > 0:
                # Normalize and extend
                norm_dx = dx / length
                norm_dy = dy / length
                
                new_x = point.x + norm_dx * buffer_px
                new_y = point.y + norm_dy * buffer_px
                
                expanded_points.append(Point(x=new_x, y=new_y))
            else:
                expanded_points.append(point)
        
        return expanded_points