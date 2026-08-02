"""Operators provided by HABD Loop Reducer."""

import math

import bpy
import bmesh

from .utils import (
    analyze_curved_tube,
    analyze_selected_chains,
    build_reduction_plan,
    is_valid_edit_mesh_context,
    redistribute_surviving_chains,
)


def _store_curved_analysis(settings, analysis) -> None:
    """Copy simple analysis values into RNA properties for display."""
    settings.curve_analysis_valid = analysis.valid
    settings.curve_level_count = len(analysis.levels)
    settings.curve_path_length = analysis.path_length
    settings.curve_min_radius = analysis.min_radius
    settings.curve_max_radius = analysis.max_radius
    settings.curve_max_turn_angle = analysis.max_turn_angle
    settings.curve_frame_continuity = analysis.frame_continuity
    settings.curve_status = analysis.status


class HABD_OT_detect_segments(bpy.types.Operator):
    """Analyze selected edges as longitudinal mesh chains."""

    bl_idname = "mesh.habd_detect_segments"
    bl_label = "Detect Segments"
    bl_description = "Analyze selected longitudinal edge chains without changing geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.habd_loop_reducer
        edit_mesh = bmesh.from_edit_mesh(context.active_object.data)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_selected_chains(
            selected_edges,
            settings.target_segments,
        )

        settings.current_segments = analysis.current_segments
        settings.segments_to_remove = analysis.segments_to_remove
        settings.selection_compatible = analysis.compatible
        settings.selection_status = analysis.status

        compatible_text = "Yes" if analysis.compatible else "No"
        summary = (
            f"Current: {analysis.current_segments} | "
            f"Target: {settings.target_segments} | "
            f"Remove: {analysis.segments_to_remove} | "
            f"Compatible: {compatible_text}"
        )
        has_warning = analysis.status != "Selection is compatible"
        report_level = {"WARNING"} if has_warning else {"INFO"}
        self.report(report_level, summary)
        print(summary)

        return {"FINISHED"}


class HABD_OT_analyze_curved_tube(bpy.types.Operator):
    """Analyze selected longitudinal chains without modifying the mesh."""

    bl_idname = "mesh.habd_analyze_curved_tube"
    bl_label = "Analyze Curved Tube"
    bl_description = "Analyze a curved tubular selection without changing geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not is_valid_edit_mesh_context(context):
            self.report({"ERROR"}, "An active mesh must be in Edit Mode")
            return {"CANCELLED"}

        settings = context.scene.habd_loop_reducer
        mesh = context.active_object.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_curved_tube(selected_edges)
        _store_curved_analysis(settings, analysis)

        if not selected_edges:
            self.report({"WARNING"}, analysis.status)
            return {"CANCELLED"}

        if analysis.valid:
            summary = (
                f"Curved tube valid | Levels: {len(analysis.levels)} | "
                f"Path: {analysis.path_length:.2f} | "
                f"Max turn: {math.degrees(analysis.max_turn_angle):.1f}°"
            )
            self.report({"INFO"}, summary)
            print(summary)
        else:
            self.report({"WARNING"}, analysis.status)
            print(analysis.status)
        return {"FINISHED"}


class HABD_OT_reduce_loops(bpy.types.Operator):
    """Reduce selected longitudinal chains and redistribute the survivors."""

    bl_idname = "mesh.habd_reduce_loops"
    bl_label = "Reduce Loops"
    bl_description = "Reduce and evenly redistribute segments around the selected mesh surface"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.habd_loop_reducer
        if not is_valid_edit_mesh_context(context):
            self.report({"ERROR"}, "An active mesh must be in Edit Mode")
            return {"CANCELLED"}
        if settings.geometry_mode != "STRAIGHT":
            self.report({"ERROR"}, "Curved reduction is not implemented yet")
            return {"CANCELLED"}

        active_object = context.active_object
        if active_object.data.shape_keys is not None:
            self.report({"ERROR"}, "Reduction is disabled for meshes with shape keys")
            return {"CANCELLED"}

        mesh = active_object.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        target_segments = settings.target_segments
        analysis = analyze_selected_chains(selected_edges, target_segments)
        settings.current_segments = analysis.current_segments
        settings.segments_to_remove = analysis.segments_to_remove
        settings.selection_compatible = analysis.compatible
        settings.selection_status = analysis.status
        if not analysis.compatible:
            self.report({"ERROR"}, analysis.status)
            return {"CANCELLED"}

        try:
            plan = build_reduction_plan(selected_edges, target_segments)
        except ValueError as error:
            settings.selection_compatible = False
            settings.selection_status = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        current_segments = len(plan.ordered_chains)
        bmesh.ops.dissolve_edges(
            edit_mesh,
            edges=plan.edges_to_dissolve,
            use_verts=True,
            use_face_split=False,
        )
        edit_mesh.verts.ensure_lookup_table()
        edit_mesh.edges.ensure_lookup_table()
        edit_mesh.faces.ensure_lookup_table()
        redistribute_surviving_chains(plan)

        for vertex in edit_mesh.verts:
            vertex.select = False
        for edge in edit_mesh.edges:
            edge.select = False
        for face in edit_mesh.faces:
            face.select = False
        for chain in plan.survivor_chains:
            for vertex in chain:
                if vertex.is_valid:
                    vertex.select = True
            for first, second in zip(chain, chain[1:]):
                for edge in first.link_edges:
                    if edge.is_valid and edge.other_vert(first) is second:
                        edge.select = True
                        break

        edit_mesh.normal_update()
        bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)

        settings.current_segments = target_segments
        settings.segments_to_remove = 0
        settings.selection_compatible = False
        settings.selection_status = "Reduction completed; run detection again"
        message = f"Reduced segments: {current_segments} → {target_segments}"

        self.report({"INFO"}, message)
        print(message)

        return {"FINISHED"}


classes = (
    HABD_OT_detect_segments,
    HABD_OT_analyze_curved_tube,
    HABD_OT_reduce_loops,
)
