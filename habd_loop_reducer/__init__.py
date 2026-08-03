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
        description="Desired number of segments for the loop reduction",
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
        name="Segments to Remove",
        description="Difference between the current and target segment counts",
        default=0,
    )
    selection_compatible: BoolProperty(
        name="Compatible",
        description="Whether the selected chains are compatible with reduction",
        default=False,
    )
    selection_status: StringProperty(
        name="Status",
        description="Result of the most recent segment detection",
        default="No analysis performed",
    )
    geometry_mode: EnumProperty(
        name="Geometry Mode",
        description="Choose straight reduction or non-destructive curved analysis",
        items=(
            ("STRAIGHT", "Straight", "Use the stable straight-cylinder workflow"),
            ("CURVED", "Curved", "Analyze a curved tubular surface"),
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
