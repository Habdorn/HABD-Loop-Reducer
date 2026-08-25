"""Operators provided by HABD Loop Reducer."""

import math

import bpy
import bmesh

from .utils import (
    analyze_curved_tube,
    analyze_longitudinal_bend,
    analyze_profile,
    build_longitudinal_resample_plan,
    analyze_selected_chains,
    build_profile_regions_plan,
    build_profile_resample_plan,
    build_reduction_plan,
    build_straight_increase_plan,
    collect_curved_increase_data,
    collect_curved_reduction_data,
    increase_tube_segments,
    is_valid_edit_mesh_context,
    reduce_curved_tube,
    resample_profile,
    resample_profile_regions,
    redistribute_surviving_chains,
    resample_longitudinal_bend,
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


def _store_profile_analysis(settings, analysis) -> None:
    """Copy PROFILE analysis values into RNA properties for display."""
    settings.profile_analysis_valid = analysis.valid
    settings.profile_type = (
        "BEVEL REGIONS"
        if analysis.regions
        else (
            analysis.profile_type.value
            if analysis.profile_type is not None
            else "UNKNOWN"
        )
    )
    settings.profile_level_count = len(analysis.levels)
    settings.profile_region_count = len(analysis.regions)
    region_counts = tuple(
        region.current_segments for region in analysis.regions
    )
    settings.profile_sample_summary = (
        ", ".join(str(count) for count in region_counts)
        if region_counts
        else str(len(analysis.ordered_chains))
    )
    settings.profile_status = analysis.status


def _store_longitudinal_analysis(settings, analysis) -> None:
    """Copy longitudinal analysis values into dedicated RNA properties."""
    settings.longitudinal_analysis_valid = analysis.valid
    settings.longitudinal_section_type = (
        analysis.section_type.value
        if analysis.section_type is not None
        else "UNKNOWN"
    )
    settings.longitudinal_selection_kind = (
        analysis.selection_kind.value.replace("_", " ")
        if analysis.selection_kind is not None
        else "UNKNOWN"
    )
    settings.longitudinal_current_cuts = analysis.current_cuts
    settings.longitudinal_level_count = len(analysis.levels)
    settings.longitudinal_path_length = analysis.path_length
    settings.longitudinal_status = analysis.status


def _profile_current_segments(analysis) -> int:
    """Return one current count when all detected regions agree."""
    if not analysis.regions:
        return len(analysis.ordered_chains)
    counts = {region.current_segments for region in analysis.regions}
    return counts.pop() if len(counts) == 1 else 0


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
            f"Change: {-analysis.segments_to_remove:+d} | "
            f"Compatible: {compatible_text}"
        )
        has_warning = not analysis.compatible
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
        settings.current_segments = len(analysis.ordered_chains)
        settings.segments_to_remove = (
            settings.current_segments - settings.target_segments
        )
        settings.selection_compatible = analysis.valid

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


class HABD_OT_analyze_profile(bpy.types.Operator):
    """Analyze selected longitudinal chains as a PROFILE band."""

    bl_idname = "mesh.habd_analyze_profile"
    bl_label = "Analyze Profile"
    bl_description = "Detect an open or closed profile band without changing geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.habd_loop_reducer
        edit_mesh = bmesh.from_edit_mesh(context.active_object.data)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_profile(selected_edges)
        _store_profile_analysis(settings, analysis)
        settings.current_segments = _profile_current_segments(analysis)
        settings.segments_to_remove = (
            settings.current_segments - settings.target_segments
        )
        settings.selection_compatible = analysis.valid
        settings.selection_status = analysis.status
        if not analysis.valid:
            self.report({"WARNING"}, analysis.status)
            return {"CANCELLED"}
        summary = (
            f"{settings.profile_type.title()} | "
            f"Regions: {len(analysis.regions)} | "
            f"Samples: {settings.profile_sample_summary} | "
            f"Levels: {len(analysis.levels)}"
        )
        self.report({"INFO"}, summary)
        print(summary)
        return {"FINISHED"}


class HABD_OT_analyze_longitudinal(bpy.types.Operator):
    """Analyze selected rails as a bend between two preserved bases."""

    bl_idname = "mesh.habd_analyze_longitudinal"
    bl_label = "Analyze Bend"
    bl_description = "Detect bases and interior cuts without changing geometry"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.habd_loop_reducer
        edit_mesh = bmesh.from_edit_mesh(context.active_object.data)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_longitudinal_bend(selected_edges)
        _store_longitudinal_analysis(settings, analysis)
        if not analysis.valid:
            self.report({"WARNING"}, analysis.status)
            return {"CANCELLED"}
        summary = (
            f"Input: {settings.longitudinal_selection_kind.title()} | "
            f"Bases detected | Cuts: {analysis.current_cuts} | "
            f"Section: {analysis.section_type.value} | "
            f"Path: {analysis.path_length:.4f}"
        )
        self.report({"INFO"}, summary)
        print(summary)
        return {"FINISHED"}


class HABD_OT_reduce_loops(bpy.types.Operator):
    """Resample selected longitudinal chains to the requested radial count."""

    bl_idname = "mesh.habd_reduce_loops"
    bl_label = "Apply Segments"
    bl_description = "Resample the selected mesh surface to the requested final count"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return is_valid_edit_mesh_context(context)

    def execute(self, context: bpy.types.Context) -> set[str]:
        settings = context.scene.habd_loop_reducer
        if not is_valid_edit_mesh_context(context):
            self.report({"ERROR"}, "An active mesh must be in Edit Mode")
            return {"CANCELLED"}
        if settings.resample_direction == "LONGITUDINAL":
            return self._execute_longitudinal(context, settings)
        if settings.geometry_mode == "PROFILE":
            return self._execute_profile(context, settings)
        if settings.geometry_mode == "CURVED":
            return self._execute_curved(context, settings)

        active_object = context.active_object
        if active_object.data.shape_keys is not None:
            self.report({"ERROR"}, "Segment resampling is disabled for meshes with shape keys")
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

        current_segments = analysis.current_segments
        if target_segments == current_segments:
            settings.selection_status = "Target matches current segments; no changes made"
            self.report({"INFO"}, settings.selection_status)
            return {"FINISHED"}

        if target_segments > current_segments:
            try:
                plan = build_straight_increase_plan(
                    selected_edges, target_segments
                )
                result = increase_tube_segments(
                    edit_mesh, plan, curved=False
                )
            except (ValueError, RuntimeError) as error:
                settings.selection_compatible = False
                settings.selection_status = str(error)
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
            bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)
            settings.current_segments = target_segments
            settings.segments_to_remove = 0
            settings.selection_compatible = True
            settings.selection_status = (
                "Increase completed; target matches current segments"
            )
            self.report({"INFO"}, result.message)
            print(result.message)
            return {"FINISHED"}

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

    def _execute_longitudinal(self, context, settings) -> set[str]:
        """Reanalyze, plan, and replace only one bend interior."""
        active_object = context.active_object
        if active_object.data.shape_keys is not None:
            self.report(
                {"ERROR"},
                "Longitudinal resampling is disabled for meshes with shape keys",
            )
            return {"CANCELLED"}

        mesh = active_object.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_longitudinal_bend(selected_edges)
        _store_longitudinal_analysis(settings, analysis)
        if not analysis.valid:
            self.report({"ERROR"}, analysis.status)
            return {"CANCELLED"}

        target_cuts = settings.longitudinal_target_cuts
        if target_cuts < 1:
            self.report({"ERROR"}, "Target Cuts must be at least 1")
            return {"CANCELLED"}
        if target_cuts == analysis.current_cuts:
            settings.longitudinal_status = (
                "Target Cuts matches Current Cuts; no changes made"
            )
            self.report({"INFO"}, settings.longitudinal_status)
            return {"FINISHED"}

        try:
            plan = build_longitudinal_resample_plan(
                analysis,
                target_cuts,
                settings.longitudinal_path_shape,
            )
            result = resample_longitudinal_bend(edit_mesh, plan)
        except (ValueError, RuntimeError) as error:
            settings.longitudinal_analysis_valid = False
            settings.longitudinal_status = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)
        _store_longitudinal_analysis(settings, result.analysis)
        settings.longitudinal_status = result.message
        self.report({"INFO"}, result.message)
        print(result.message)
        return {"FINISHED"}

    def _execute_profile(self, context, settings) -> set[str]:
        """Reanalyze and resample one compatible PROFILE band."""
        active_object = context.active_object
        if active_object.data.shape_keys is not None:
            self.report(
                {"ERROR"},
                "Profile resampling is disabled for meshes with shape keys",
            )
            return {"CANCELLED"}

        mesh = active_object.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_profile(selected_edges)
        _store_profile_analysis(settings, analysis)
        settings.current_segments = _profile_current_segments(analysis)
        settings.segments_to_remove = (
            settings.current_segments - settings.target_segments
        )
        settings.selection_compatible = analysis.valid
        settings.selection_status = analysis.status
        if not analysis.valid:
            self.report({"ERROR"}, analysis.status)
            return {"CANCELLED"}

        target_segments = settings.target_segments
        if target_segments < 3:
            self.report({"ERROR"}, "Target must be at least 3 profile samples")
            return {"CANCELLED"}
        current_counts = (
            tuple(region.current_segments for region in analysis.regions)
            if analysis.regions
            else (len(analysis.ordered_chains),)
        )
        if all(count == target_segments for count in current_counts):
            settings.profile_status = "Target matches current profile samples; no changes made"
            settings.selection_status = settings.profile_status
            self.report({"INFO"}, settings.profile_status)
            return {"FINISHED"}

        try:
            if analysis.regions:
                plan = build_profile_regions_plan(analysis, target_segments)
                result = resample_profile_regions(edit_mesh, plan)
            else:
                plan = build_profile_resample_plan(analysis, target_segments)
                result = resample_profile(edit_mesh, plan)
        except (ValueError, RuntimeError) as error:
            settings.profile_analysis_valid = False
            settings.selection_compatible = False
            settings.profile_status = str(error)
            settings.selection_status = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)
        settings.current_segments = target_segments
        settings.segments_to_remove = 0
        settings.selection_compatible = False
        settings.profile_analysis_valid = False
        settings.profile_status = "Profile resampling completed; analyze again"
        settings.selection_status = settings.profile_status
        self.report({"INFO"}, result.message)
        print(result.message)
        return {"FINISHED"}

    def _execute_curved(self, context, settings) -> set[str]:
        """Reanalyze and resample one compatible curved tubular selection."""
        active_object = context.active_object
        if active_object.data.shape_keys is not None:
            self.report({"ERROR"}, "Segment resampling is disabled for meshes with shape keys")
            return {"CANCELLED"}

        mesh = active_object.data
        edit_mesh = bmesh.from_edit_mesh(mesh)
        selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
        analysis = analyze_curved_tube(selected_edges)
        _store_curved_analysis(settings, analysis)
        settings.current_segments = len(analysis.ordered_chains)
        settings.segments_to_remove = (
            settings.current_segments - settings.target_segments
        )
        settings.selection_compatible = analysis.valid
        if not analysis.valid:
            self.report({"ERROR"}, analysis.status)
            return {"CANCELLED"}

        current_segments = len(analysis.ordered_chains)
        target_segments = settings.target_segments
        if target_segments < 3:
            self.report({"ERROR"}, "Target must be at least 3")
            return {"CANCELLED"}
        if target_segments == current_segments:
            settings.curve_status = "Target matches current segments; no changes made"
            self.report({"INFO"}, settings.curve_status)
            return {"FINISHED"}
        if target_segments > current_segments:
            try:
                plan = collect_curved_increase_data(analysis, target_segments)
                result = increase_tube_segments(edit_mesh, plan, curved=True)
            except (ValueError, RuntimeError) as error:
                settings.curve_analysis_valid = False
                settings.selection_compatible = False
                settings.curve_status = str(error)
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
            bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)
            settings.current_segments = target_segments
            settings.segments_to_remove = 0
            settings.selection_compatible = False
            settings.curve_analysis_valid = False
            settings.curve_status = "Curved increase completed; analyze again"
            self.report({"INFO"}, result.message)
            print(result.message)
            return {"FINISHED"}

        edit_mesh.normal_update()
        try:
            plan = collect_curved_reduction_data(
                analysis,
                settings.target_segments,
            )
        except ValueError as error:
            settings.curve_analysis_valid = False
            settings.selection_compatible = False
            settings.curve_status = str(error)
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        result = reduce_curved_tube(edit_mesh, plan)
        bmesh.update_edit_mesh(mesh, loop_triangles=True, destructive=True)

        settings.current_segments = settings.target_segments
        settings.segments_to_remove = 0
        settings.selection_compatible = False
        settings.curve_analysis_valid = False
        settings.curve_status = "Curved reduction completed; analyze again"
        self.report({"INFO"}, result.message)
        print(result.message)
        return {"FINISHED"}


classes = (
    HABD_OT_detect_segments,
    HABD_OT_analyze_curved_tube,
    HABD_OT_analyze_profile,
    HABD_OT_analyze_longitudinal,
    HABD_OT_reduce_loops,
)
