"""3D Viewport interface for HABD Loop Reducer."""

import bpy

from .utils import is_valid_edit_mesh_context


class HABD_PT_loop_reducer(bpy.types.Panel):
    """Display the initial HABD Loop Reducer controls."""

    bl_idname = "HABD_PT_loop_reducer"
    bl_label = "Loop Reducer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "HABD"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        settings = context.scene.habd_loop_reducer

        layout.label(text="HABD Loop Reducer")

        detect_row = layout.row()
        detect_row.enabled = is_valid_edit_mesh_context(context)
        detect_row.operator("mesh.habd_detect_segments", text="Detect Segments")

        results = layout.column(align=True)
        results.label(text=f"Current Segments: {settings.current_segments}")
        results.prop(settings, "target_segments", text="Target Segments")
        results.label(text=f"Segments to Remove: {settings.segments_to_remove}")
        compatible_text = "Yes" if settings.selection_compatible else "No"
        results.label(text=f"Compatible: {compatible_text}")
        results.label(text=f"Status: {settings.selection_status}")

        operator_row = layout.row()
        operator_row.enabled = (
            is_valid_edit_mesh_context(context)
            and settings.selection_compatible
        )
        operator_row.operator("mesh.habd_reduce_loops", text="Reduce Loops")


classes = (HABD_PT_loop_reducer,)
