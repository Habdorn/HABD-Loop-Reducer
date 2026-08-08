"""Registration entry point for HABD Loop Reducer."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from .operators import classes as operator_classes
from .panel import classes as panel_classes


class HABD_LR_Properties(PropertyGroup):
    """Scene-level options used by HABD Loop Reducer."""

    target_segments: IntProperty(
        name="Target Segments",
        description="Final number of radial segments or profile samples",
        default=18,
        min=3,
        max=10_000,
    )
    current_segments: IntProperty(
        name="Current Segments",
        description="Number of valid longitudinal chains found in the selection",
        default=0,
    )
    segments_to_remove: IntProperty(
        name="Segment Difference",
        description="Legacy current-minus-target segment difference",
        default=0,
    )
    selection_compatible: BoolProperty(
        name="Compatible",
        description="Whether the selected chains are compatible with resampling",
        default=False,
    )
    selection_status: StringProperty(
        name="Status",
        description="Result of the most recent segment detection",
        default="No analysis performed",
    )
    geometry_mode: EnumProperty(
        name="Geometry Mode",
        description="Choose straight or curved tube resampling",
        items=(
            ("STRAIGHT", "Straight", "Resample a straight circular tube"),
            ("CURVED", "Curved", "Analyze and resample a curved circular tube"),
            (
                "PROFILE",
                "Profile",
                "Resample an open or closed profile by cumulative length",
            ),
        ),
        default="STRAIGHT",
    )
    curve_analysis_valid: BoolProperty(
        name="Valid",
        description="Whether the most recent curved analysis is compatible",
        default=False,
    )
    curve_level_count: IntProperty(
        name="Levels",
        description="Number of transverse levels found in the curved selection",
        default=0,
        min=0,
    )
    curve_path_length: FloatProperty(
        name="Path Length",
        description="Length of the analyzed centerline in local mesh units",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        precision=4,
    )
    curve_min_radius: FloatProperty(
        name="Minimum Radius",
        description="Smallest radial distance found across all levels",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        precision=4,
    )
    curve_max_radius: FloatProperty(
        name="Maximum Radius",
        description="Largest radial distance found across all levels",
        default=0.0,
        min=0.0,
        unit="LENGTH",
        precision=4,
    )
    curve_max_turn_angle: FloatProperty(
        name="Maximum Turn Angle",
        description="Largest angle between consecutive local tangents",
        default=0.0,
        min=0.0,
        max=3.141592653589793,
        subtype="ANGLE",
        unit="ROTATION",
        precision=2,
    )
    curve_frame_continuity: BoolProperty(
        name="Frame Continuity",
        description="Whether transported local frames avoid orientation flips",
        default=False,
    )
    curve_status: StringProperty(
        name="Status",
        description="Result of the most recent curved tube analysis",
        default="No curved analysis performed",
    )
    profile_analysis_valid: BoolProperty(
        name="Valid Profile",
        description="Whether the most recent PROFILE analysis is compatible",
        default=False,
    )
    profile_type: StringProperty(
        name="Profile Type",
        description="Automatically detected open or closed profile topology",
        default="UNKNOWN",
    )
    profile_level_count: IntProperty(
        name="Profile Levels",
        description="Number of corresponding transverse profile levels",
        default=0,
        min=0,
    )
    profile_region_count: IntProperty(
        name="Profile Regions",
        description="Number of automatically detected bevel regions",
        default=0,
        min=0,
    )
    profile_sample_summary: StringProperty(
        name="Current Profile Samples",
        description="Current sample count for each detected profile region",
        default="0",
    )
    profile_status: StringProperty(
        name="Profile Status",
        description="Result of the most recent PROFILE analysis",
        default="No profile analysis performed",
    )


classes = (
    HABD_LR_Properties,
    *operator_classes,
    *panel_classes,
)


def register() -> None:
    """Register addon classes and scene properties."""
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.habd_loop_reducer = PointerProperty(type=HABD_LR_Properties)


def unregister() -> None:
    """Remove scene properties and unregister addon classes."""
    del bpy.types.Scene.habd_loop_reducer

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
