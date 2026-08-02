"""Registration entry point for HABD Loop Reducer."""

import bpy
from bpy.props import BoolProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .operators import classes as operator_classes
from .panel import classes as panel_classes


bl_info = {
    "name": "HABD Loop Reducer",
    "author": "Habdorn",
    "version": (0, 1, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > HABD",
    "description": "Reducción controlada de loops y segmentos en mallas",
    "support": "COMMUNITY",
    "category": "Mesh",
}


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
