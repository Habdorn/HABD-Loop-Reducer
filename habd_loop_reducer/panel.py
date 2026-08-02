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
        layout.prop(settings, "geometry_mode", text="Geometry Mode")

        if settings.geometry_mode == "CURVED":
            analyze_row = layout.row()
            analyze_row.enabled = is_valid_edit_mesh_context(context)
            analyze_row.operator(
                "mesh.habd_analyze_curved_tube",
                text="Analyze Curved Tube",
            )

            analysis_box = layout.box()
            analysis_box.label(text="Curved Analysis")
            analysis_box.label(text=f"Status: {settings.curve_status}")
            analysis_box.label(text=f"Levels: {settings.curve_level_count}")
            analysis_box.label(text=f"Current Segments: {settings.current_segments}")
            analysis_box.prop(settings, "target_segments", text="Target Segments")
            analysis_box.prop(settings, "curve_path_length", text="Path Length")
            analysis_box.prop(settings, "curve_min_radius", text="Minimum Radius")
            analysis_box.prop(settings, "curve_max_radius", text="Maximum Radius")
            analysis_box.prop(
                settings,
                "curve_max_turn_angle",
                text="Maximum Turn Angle",
            )
            continuity = "Yes" if settings.curve_frame_continuity else "No"
            analysis_box.label(text=f"Frame Continuity: {continuity}")

            reduction_ready = (
                settings.curve_analysis_valid
                and settings.target_segments < settings.current_segments
            )
            guidance = layout.column()
            guidance.alert = not reduction_ready
            if reduction_ready:
                guidance.label(text="Curved reduction ready")
            elif settings.curve_analysis_valid:
                guidance.label(text="Target must be lower than current segments")
            else:
                guidance.label(text="Analyze the curved tube before reducing")
            operator_row = layout.row()
            operator_row.enabled = (
                is_valid_edit_mesh_context(context) and reduction_ready
            )
            operator_row.operator("mesh.habd_reduce_loops", text="Reduce Loops")
        else:
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
