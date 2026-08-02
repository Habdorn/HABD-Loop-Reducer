"""Small shared helpers for HABD Loop Reducer."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

import bmesh
from mathutils import Quaternion, Vector


_GEOMETRY_EPSILON = 1.0e-8
_CURVE_CIRCULARITY_TOLERANCE = 0.05
_FRAME_FLIP_DOT_THRESHOLD = -0.95
_CURVE_PLANARITY_TOLERANCE = 0.05
_CURVE_MEAN_PLANARITY_TOLERANCE = 0.025
_CURVE_RESULT_TOLERANCE_RATIO = 1.0e-5


@dataclass(frozen=True)
class EdgeComponentInfo:
    """Topological classification of one connected edge component."""

    edge_count: int
    vertex_count: int
    is_open_chain: bool
    is_closed: bool
    is_branched: bool


@dataclass(frozen=True)
class SelectionAnalysis:
    """Result of analyzing selected edges as longitudinal chains."""

    current_segments: int
    segments_to_remove: int
    compatible: bool
    status: str


@dataclass(frozen=True)
class CurvedLevelInfo:
    """Geometric measurements and transported frame for one tube level."""

    center: Vector
    path_tangent: Vector
    tangent: Vector
    normal: Vector
    binormal: Vector
    average_radius: float
    min_radius: float
    max_radius: float
    max_abs_axial_offset: float
    mean_abs_axial_offset: float
    planarity_ratio: float


class TubeEndType(str, Enum):
    """Supported longitudinal endpoint configurations."""

    OPEN = "OPEN"
    NGON_CAP = "NGON_CAP"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class TubeEndInfo:
    """Classification and preserved data for one longitudinal endpoint."""

    end_type: TubeEndType
    cap_face: Any | None
    status: str


@dataclass(frozen=True)
class CurvedTubeAnalysis:
    """Non-destructive analysis result for a selected tubular surface."""

    valid: bool
    status: str
    ordered_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    level_info: tuple[CurvedLevelInfo, ...]
    path_length: float
    min_radius: float
    max_radius: float
    max_turn_angle: float
    frame_continuity: bool


@dataclass(frozen=True)
class CurvedReductionPlan:
    """Validated geometry and live survivors needed for curved reduction."""

    current_segments: int
    target_segments: int
    remove_indices: tuple[int, ...]
    survivor_indices: tuple[int, ...]
    ordered_chains: tuple[tuple[Any, ...], ...]
    survivor_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    centers: tuple[Vector, ...]
    tangents: tuple[Vector, ...]
    normals: tuple[Vector, ...]
    binormals: tuple[Vector, ...]
    radii: tuple[float, ...]
    reference_angles: tuple[float, ...]
    axial_offsets: tuple[tuple[float, ...], ...]
    edges_to_dissolve: tuple[Any, ...]
    end_types: tuple[TubeEndType, TubeEndType]
    cap_normals: tuple[Vector | None, Vector | None]
    cap_material_indices: tuple[int | None, int | None]
    lateral_winding_sign: int


@dataclass(frozen=True)
class CurvedReductionResult:
    """Topology counts reported after a successful curved reduction."""

    success: bool
    message: str
    vertex_count_before: int
    vertex_count_after: int
    edge_count_before: int
    edge_count_after: int
    face_count_before: int
    face_count_after: int


@dataclass(frozen=True)
class ReductionPlan:
    """Geometry and live survivor references needed for one reduction."""

    ordered_chains: tuple[tuple[Any, ...], ...]
    survivor_chains: tuple[tuple[Any, ...], ...]
    edges_to_dissolve: tuple[Any, ...]
    centers: tuple[Vector, ...]
    radii: tuple[float, ...]
    axial_offsets: tuple[tuple[float, ...], ...]
    basis_u: Vector
    basis_v: Vector
    axis: Vector
    start_angle: float
    target_segments: int


def is_valid_edit_mesh_context(context: Any) -> bool:
    """Return whether the context is editing an active mesh object."""
    active_object = getattr(context, "active_object", None)
    return (
        active_object is not None
        and active_object.type == "MESH"
        and context.mode == "EDIT_MESH"
    )


def separate_connected_edge_components(
    selected_edges: Iterable[Any],
) -> tuple[tuple[Any, ...], ...]:
    """Separate selected edges into vertex-connected components."""
    remaining_edges = set(selected_edges)
    components: list[tuple[Any, ...]] = []

    while remaining_edges:
        first_edge = remaining_edges.pop()
        component = [first_edge]
        pending_edges = [first_edge]

        while pending_edges:
            edge = pending_edges.pop()
            for vertex in edge.verts:
                for linked_edge in vertex.link_edges:
                    if linked_edge in remaining_edges:
                        remaining_edges.remove(linked_edge)
                        component.append(linked_edge)
                        pending_edges.append(linked_edge)

        components.append(tuple(component))

    return tuple(components)


def classify_edge_component(component: Sequence[Any]) -> EdgeComponentInfo:
    """Classify a connected edge component by its internal vertex degrees."""
    vertices = {vertex for edge in component for vertex in edge.verts}
    component_edges = set(component)
    degrees = {
        vertex: sum(1 for edge in vertex.link_edges if edge in component_edges)
        for vertex in vertices
    }

    degree_one_count = sum(degree == 1 for degree in degrees.values())
    is_branched = any(degree > 2 for degree in degrees.values())
    is_closed = bool(degrees) and all(degree == 2 for degree in degrees.values())
    is_open_chain = (
        degree_one_count == 2
        and not is_branched
        and all(degree in {1, 2} for degree in degrees.values())
    )

    return EdgeComponentInfo(
        edge_count=len(component),
        vertex_count=len(vertices),
        is_open_chain=is_open_chain,
        is_closed=is_closed,
        is_branched=is_branched,
    )


def analyze_selected_chains(
    selected_edges: Iterable[Any],
    target_segments: int,
) -> SelectionAnalysis:
    """Analyze whether selected components are equivalent open chains."""
    components = separate_connected_edge_components(selected_edges)
    component_info = tuple(classify_edge_component(item) for item in components)
    valid_chains = tuple(item for item in component_info if item.is_open_chain)
    current_segments = len(valid_chains)
    segments_to_remove = current_segments - target_segments

    def result(compatible: bool, status: str) -> SelectionAnalysis:
        return SelectionAnalysis(
            current_segments=current_segments,
            segments_to_remove=segments_to_remove,
            compatible=compatible,
            status=status,
        )

    if not component_info:
        return result(False, "No edges selected")
    if any(item.is_branched for item in component_info):
        return result(False, "Selection contains branched components")
    if any(item.is_closed for item in component_info):
        return result(False, "Selection contains closed components")
    if any(not item.is_open_chain for item in component_info):
        return result(False, "Selection contains invalid components")
    if current_segments < 3:
        return result(False, "Select at least 3 open chains")

    edge_counts = {item.edge_count for item in valid_chains}
    vertex_counts = {item.vertex_count for item in valid_chains}
    if len(edge_counts) != 1 or len(vertex_counts) != 1:
        return result(False, "Selected chains do not have matching topology")
    if target_segments < 3:
        return result(False, "Target must be at least 3")
    if target_segments >= current_segments:
        return result(False, "Target must be lower than current segment count")
    if segments_to_remove < 1:
        return result(False, "At least one segment must be removed")
    if current_segments % segments_to_remove != 0:
        return result(True, "Compatible; removal spacing will be uneven")

    return result(True, "Selection is compatible")


def _ordered_component_vertices(component: Sequence[Any]) -> tuple[Any, ...]:
    """Walk an already validated open edge chain from one end to the other."""
    component_edges = set(component)
    vertices = {vertex for edge in component for vertex in edge.verts}
    adjacency = {
        vertex: tuple(
            edge.other_vert(vertex)
            for edge in vertex.link_edges
            if edge in component_edges
        )
        for vertex in vertices
    }
    endpoints = [vertex for vertex, neighbors in adjacency.items() if len(neighbors) == 1]
    if len(endpoints) != 2:
        raise ValueError("Each selected component must be an open chain")

    # Coordinate ordering makes the walk deterministic before the common axis is known.
    current = min(endpoints, key=lambda vertex: tuple(vertex.co))
    previous = None
    ordered = []
    while current is not None:
        ordered.append(current)
        next_vertices = [item for item in adjacency[current] if item is not previous]
        if len(next_vertices) > 1:
            raise ValueError("Selection contains branched components")
        previous, current = current, next_vertices[0] if next_vertices else None

    if len(ordered) != len(vertices):
        raise ValueError("A selected chain could not be traversed completely")
    return tuple(ordered)


def _mean_position(vertices: Sequence[Any]) -> Vector:
    """Return the arithmetic mean of mesh vertex coordinates."""
    total = Vector((0.0, 0.0, 0.0))
    for vertex in vertices:
        total += vertex.co
    return total / len(vertices)


def _calculate_axis(chains: Sequence[tuple[Any, ...]]) -> Vector:
    """Orient chain endpoints consistently and calculate the longitudinal axis."""
    reference_chain = max(
        chains,
        key=lambda chain: (chain[-1].co - chain[0].co).length_squared,
    )
    reference_direction = reference_chain[-1].co - reference_chain[0].co
    if reference_direction.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not determine a stable longitudinal axis")
    reference_direction.normalize()

    start_points = []
    end_points = []
    for chain in chains:
        direction = chain[-1].co - chain[0].co
        if direction.length <= _GEOMETRY_EPSILON:
            raise ValueError("A selected chain has coincident endpoints")
        if abs(direction.normalized().dot(reference_direction)) <= 1.0e-4:
            raise ValueError("Selected chains do not share a stable direction")
        if direction.dot(reference_direction) < 0.0:
            chain = tuple(reversed(chain))
        start_points.append(chain[0])
        end_points.append(chain[-1])

    start_center = _mean_position(start_points)
    end_center = _mean_position(end_points)
    axis = end_center - start_center
    if axis.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not determine a stable longitudinal axis")
    axis.normalize()
    return axis


def _orient_chains_to_axis(
    chains: Sequence[tuple[Any, ...]],
    axis: Vector,
) -> tuple[tuple[Any, ...], ...]:
    """Return all chains ordered in the positive longitudinal direction."""
    return tuple(
        chain
        if (chain[-1].co - chain[0].co).dot(axis) >= 0.0
        else tuple(reversed(chain))
        for chain in chains
    )


def _perpendicular_basis(axis: Vector) -> tuple[Vector, Vector]:
    """Build a stable right-handed basis for the plane normal to axis."""
    coordinate_axes = (
        Vector((1.0, 0.0, 0.0)),
        Vector((0.0, 1.0, 0.0)),
        Vector((0.0, 0.0, 1.0)),
    )
    auxiliary = min(coordinate_axes, key=lambda item: abs(axis.dot(item)))
    basis_u = axis.cross(auxiliary)
    if basis_u.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not construct a plane perpendicular to the axis")
    basis_u.normalize()
    basis_v = axis.cross(basis_u).normalized()
    return basis_u, basis_v


def _find_connecting_edge(first: Any, second: Any) -> Any | None:
    """Find a direct mesh edge between two vertices."""
    for edge in first.link_edges:
        if edge.other_vert(first) is second:
            return edge
    return None


def _walk_open_chain(
    component: Sequence[Any],
    start_vertex: Any,
) -> tuple[Any, ...]:
    """Walk an open component from a supplied endpoint without spatial sorting."""
    component_edges = set(component)
    vertices = {vertex for edge in component for vertex in edge.verts}
    adjacency = {
        vertex: tuple(
            edge.other_vert(vertex)
            for edge in vertex.link_edges
            if edge in component_edges
        )
        for vertex in vertices
    }
    if len(adjacency.get(start_vertex, ())) != 1:
        raise ValueError("Each selected component must be an open chain")

    ordered = []
    previous = None
    current = start_vertex
    while current is not None:
        ordered.append(current)
        next_vertices = [item for item in adjacency[current] if item is not previous]
        if len(next_vertices) > 1:
            raise ValueError("Selection contains branched components")
        previous, current = current, next_vertices[0] if next_vertices else None

    if len(ordered) != len(vertices):
        raise ValueError("A selected chain could not be traversed completely")
    return tuple(ordered)


def _orient_and_order_curved_chains(
    components: Sequence[Sequence[Any]],
) -> tuple[tuple[Any, ...], ...]:
    """Align and circularly order chains using only transverse connectivity."""
    raw_chains = []
    for component in components:
        component_edges = set(component)
        vertices = {vertex for edge in component for vertex in edge.verts}
        endpoints = [
            vertex
            for vertex in vertices
            if sum(1 for edge in vertex.link_edges if edge in component_edges) == 1
        ]
        if len(endpoints) != 2:
            raise ValueError("Each selected component must be an open chain")
        raw_chains.append(_walk_open_chain(component, endpoints[0]))

    level_count = len(raw_chains[0])
    adjacency: list[list[tuple[int, bool]]] = [
        [] for _ in range(len(raw_chains))
    ]
    for first_index, first_chain in enumerate(raw_chains):
        for second_index in range(first_index + 1, len(raw_chains)):
            second_chain = raw_chains[second_index]
            same_count = sum(
                _find_connecting_edge(first_chain[level], second_chain[level])
                is not None
                for level in range(level_count)
            )
            reversed_count = sum(
                _find_connecting_edge(
                    first_chain[level],
                    second_chain[level_count - 1 - level],
                )
                is not None
                for level in range(level_count)
            )
            if same_count == level_count and reversed_count < level_count:
                is_reversed = False
            elif reversed_count == level_count and same_count < level_count:
                is_reversed = True
            elif same_count == 0 and reversed_count == 0:
                continue
            else:
                raise ValueError("Chain correspondence is inconsistent between levels")
            adjacency[first_index].append((second_index, is_reversed))
            adjacency[second_index].append((first_index, is_reversed))

    if any(len(neighbors) != 2 for neighbors in adjacency):
        raise ValueError("Selection is not one complete tubular surface")

    orientation = {0: False}
    pending = [0]
    while pending:
        current = pending.pop()
        for neighbor, reverses_orientation in adjacency[current]:
            expected = orientation[current] ^ reverses_orientation
            if neighbor in orientation:
                if orientation[neighbor] != expected:
                    raise ValueError("Chain orientation is inconsistent")
                continue
            orientation[neighbor] = expected
            pending.append(neighbor)
    if len(orientation) != len(raw_chains):
        raise ValueError("Selection contains more than one tubular surface")

    chain_order = [0]
    previous = None
    current = 0
    while True:
        candidates = [
            neighbor for neighbor, _ in adjacency[current] if neighbor != previous
        ]
        next_index = candidates[0]
        if next_index == chain_order[0]:
            break
        if next_index in chain_order:
            raise ValueError("Transverse chain order is not a single cycle")
        chain_order.append(next_index)
        previous, current = current, next_index
    if len(chain_order) != len(raw_chains):
        raise ValueError("Transverse chain order is incomplete")

    return tuple(
        tuple(reversed(raw_chains[index]))
        if orientation[index]
        else tuple(raw_chains[index])
        for index in chain_order
    )


def build_longitudinal_levels(
    ordered_chains: Sequence[Sequence[Any]],
) -> tuple[tuple[Any, ...], ...]:
    """Transpose equally sized longitudinal chains into transverse levels."""
    if not ordered_chains:
        raise ValueError("No selected longitudinal chains")
    level_counts = {len(chain) for chain in ordered_chains}
    if len(level_counts) != 1:
        raise ValueError("Selected chains have different topology")
    level_count = level_counts.pop()
    if level_count < 2:
        raise ValueError("At least two transverse levels are required")
    levels = tuple(
        tuple(chain[level_index] for chain in ordered_chains)
        for level_index in range(level_count)
    )
    if any(len(level) != len(ordered_chains) for level in levels):
        raise ValueError("A transverse level has an invalid vertex count")
    return levels


def calculate_level_centers(
    levels: Sequence[Sequence[Any]],
) -> tuple[Vector, ...]:
    """Calculate transverse centers in local mesh coordinates."""
    return tuple(_mean_position(level).copy() for level in levels)


def calculate_local_tangents(centers: Sequence[Vector]) -> tuple[Vector, ...]:
    """Calculate endpoint and centered local tangents along a centerline."""
    if len(centers) < 2:
        raise ValueError("At least two centerline points are required")
    tangents = []
    for index in range(len(centers)):
        if index == 0:
            tangent = centers[1] - centers[0]
        elif index == len(centers) - 1:
            tangent = centers[-1] - centers[-2]
        else:
            tangent = centers[index + 1] - centers[index - 1]
        if tangent.length <= _GEOMETRY_EPSILON:
            raise ValueError("Invalid local tangent")
        tangents.append(tangent.normalized())
    return tuple(tangents)


def calculate_ring_normals(
    levels: Sequence[Sequence[Any]],
    path_tangents: Sequence[Vector],
) -> tuple[Vector, ...]:
    """Calculate consistently oriented geometric ring normals using Newell."""
    if len(levels) != len(path_tangents):
        raise ValueError("Ring levels and centerline tangents do not match")
    ring_normals = []
    previous_normal = None
    for level_index, (level, path_tangent) in enumerate(
        zip(levels, path_tangents)
    ):
        ring_normal = Vector((0.0, 0.0, 0.0))
        for current, following in zip(level, level[1:] + level[:1]):
            ring_normal.x += (
                (current.co.y - following.co.y)
                * (current.co.z + following.co.z)
            )
            ring_normal.y += (
                (current.co.z - following.co.z)
                * (current.co.x + following.co.x)
            )
            ring_normal.z += (
                (current.co.x - following.co.x)
                * (current.co.y + following.co.y)
            )
        if ring_normal.length <= _GEOMETRY_EPSILON:
            raise ValueError(
                f"Level {level_index + 1} has a degenerate ring normal"
            )
        ring_normal.normalize()
        alignment = ring_normal.dot(path_tangent)
        if abs(alignment) <= 1.0e-4:
            raise ValueError(
                f"Level {level_index + 1} ring normal is incompatible "
                "with the centerline"
            )
        if alignment < 0.0:
            ring_normal.negate()
        if previous_normal is not None and ring_normal.dot(previous_normal) < 0.0:
            ring_normal.negate()
        ring_normals.append(ring_normal)
        previous_normal = ring_normal
    return tuple(ring_normals)


def build_initial_frame(
    level: Sequence[Any],
    center: Vector,
    tangent: Vector,
) -> tuple[Vector, Vector, Vector]:
    """Build a geometry-anchored orthonormal frame for the first level."""
    reference = level[0].co - center
    normal = reference - tangent * reference.dot(tangent)
    if normal.length <= _GEOMETRY_EPSILON:
        coordinate_axes = (
            Vector((1.0, 0.0, 0.0)),
            Vector((0.0, 1.0, 0.0)),
            Vector((0.0, 0.0, 1.0)),
        )
        helper = min(coordinate_axes, key=lambda axis: abs(tangent.dot(axis)))
        normal = tangent.cross(helper)
    if normal.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not build the initial local frame")
    normal.normalize()
    binormal = tangent.cross(normal)
    if binormal.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not build the initial local frame")
    binormal.normalize()
    normal = binormal.cross(tangent).normalized()
    return tangent.copy(), normal, binormal


def parallel_transport_frame(
    previous_frame: tuple[Vector, Vector, Vector],
    current_tangent: Vector,
) -> tuple[Vector, Vector, Vector]:
    """Approximately parallel-transport one orthonormal frame."""
    previous_tangent, previous_normal, previous_binormal = previous_frame
    rotation_axis = previous_tangent.cross(current_tangent)
    dot_value = max(-1.0, min(1.0, previous_tangent.dot(current_tangent)))
    if rotation_axis.length > _GEOMETRY_EPSILON:
        angle = math.atan2(rotation_axis.length, dot_value)
        rotation_axis.normalize()
        rotation = Quaternion(rotation_axis, angle)
        normal = rotation @ previous_normal
        binormal = rotation @ previous_binormal
    else:
        normal = previous_normal.copy()
        binormal = previous_binormal.copy()

    normal -= current_tangent * normal.dot(current_tangent)
    if normal.length <= _GEOMETRY_EPSILON:
        normal = binormal.cross(current_tangent)
    if normal.length <= _GEOMETRY_EPSILON:
        raise ValueError("Invalid transported local frame")
    normal.normalize()
    binormal = current_tangent.cross(normal)
    if binormal.length <= _GEOMETRY_EPSILON:
        raise ValueError("Invalid transported local frame")
    binormal.normalize()
    normal = binormal.cross(current_tangent).normalized()
    return current_tangent.copy(), normal, binormal


def reproject_frame_to_ring_plane(
    previous_frame: tuple[Vector, Vector, Vector],
    ring_normal: Vector,
) -> tuple[Vector, Vector, Vector]:
    """Keep the previous radial reference projected into a real ring plane."""
    _, previous_normal, _ = previous_frame
    projected = previous_normal - ring_normal * previous_normal.dot(ring_normal)
    if projected.length <= _GEOMETRY_EPSILON:
        return parallel_transport_frame(previous_frame, ring_normal)
    normal = projected.normalized()
    binormal = ring_normal.cross(normal)
    if binormal.length <= _GEOMETRY_EPSILON:
        return parallel_transport_frame(previous_frame, ring_normal)
    binormal.normalize()
    normal = binormal.cross(ring_normal).normalized()
    return ring_normal.copy(), normal, binormal


def calculate_level_radius_data(
    level: Sequence[Any],
    center: Vector,
    tangent: Vector,
) -> tuple[float, float, float, tuple[float, ...]]:
    """Measure radial distances after removing each axial component."""
    radii = []
    for vertex in level:
        relative = vertex.co - center
        axial = tangent * relative.dot(tangent)
        radii.append((relative - axial).length)
    average_radius = sum(radii) / len(radii)
    return average_radius, min(radii), max(radii), tuple(radii)


def validate_level_circularity(
    radii: Sequence[float],
    average_radius: float,
    tolerance: float = _CURVE_CIRCULARITY_TOLERANCE,
) -> bool:
    """Accept levels whose maximum radial deviation is at most five percent."""
    if average_radius <= _GEOMETRY_EPSILON:
        return False
    maximum_deviation = max(abs(radius - average_radius) for radius in radii)
    return maximum_deviation / average_radius <= tolerance


def analyze_curved_tube(selected_edges: Iterable[Any]) -> CurvedTubeAnalysis:
    """Analyze a selected tube without changing BMesh geometry or selection."""
    selected_edges = tuple(selected_edges)

    def result(
        valid: bool,
        status: str,
        *,
        ordered_chains: tuple[tuple[Any, ...], ...] = (),
        levels: tuple[tuple[Any, ...], ...] = (),
        level_info: tuple[CurvedLevelInfo, ...] = (),
        path_length: float = 0.0,
        min_radius: float = 0.0,
        max_radius: float = 0.0,
        max_turn_angle: float = 0.0,
        frame_continuity: bool = False,
    ) -> CurvedTubeAnalysis:
        return CurvedTubeAnalysis(
            valid=valid,
            status=status,
            ordered_chains=ordered_chains,
            levels=levels,
            level_info=level_info,
            path_length=path_length,
            min_radius=min_radius,
            max_radius=max_radius,
            max_turn_angle=max_turn_angle,
            frame_continuity=frame_continuity,
        )

    if not selected_edges:
        return result(False, "No selected longitudinal chains")
    components = separate_connected_edge_components(selected_edges)
    component_info = tuple(classify_edge_component(item) for item in components)
    if any(item.is_branched for item in component_info):
        return result(False, "Selection contains branched components")
    if any(item.is_closed for item in component_info):
        return result(False, "Selection contains closed components")
    if any(not item.is_open_chain for item in component_info):
        return result(False, "Selection contains invalid longitudinal chains")
    if len(components) < 3:
        return result(False, "Select at least 3 complete longitudinal chains")
    edge_counts = {item.edge_count for item in component_info}
    vertex_counts = {item.vertex_count for item in component_info}
    if len(edge_counts) != 1 or len(vertex_counts) != 1:
        return result(False, "Selected chains have different topology")

    try:
        ordered_chains = _orient_and_order_curved_chains(components)
        _validate_circular_structure(ordered_chains)
        levels = build_longitudinal_levels(ordered_chains)
        centers = calculate_level_centers(levels)
        segment_lengths = tuple(
            (second - first).length
            for first, second in zip(centers, centers[1:])
        )
        if any(length <= _GEOMETRY_EPSILON for length in segment_lengths):
            return result(
                False,
                "Degenerate centerline segment",
                ordered_chains=ordered_chains,
                levels=levels,
            )
        path_length = sum(segment_lengths)
        path_tangents = calculate_local_tangents(centers)
        ring_normals = calculate_ring_normals(levels, path_tangents)
        frame = build_initial_frame(levels[0], centers[0], ring_normals[0])
        frames = [frame]
        frame_continuity = True
        max_turn_angle = 0.0
        for index in range(1, len(ring_normals)):
            turn_angle = math.acos(
                max(
                    -1.0,
                    min(1.0, ring_normals[index - 1].dot(ring_normals[index])),
                )
            )
            max_turn_angle = max(max_turn_angle, turn_angle)
            current_frame = reproject_frame_to_ring_plane(
                frames[-1], ring_normals[index]
            )
            if (
                frames[-1][1].dot(current_frame[1])
                <= _FRAME_FLIP_DOT_THRESHOLD
                or frames[-1][2].dot(current_frame[2])
                <= _FRAME_FLIP_DOT_THRESHOLD
            ):
                frame_continuity = False
            frames.append(current_frame)

        level_info_items = []
        global_min_radius = math.inf
        global_max_radius = 0.0
        circularity_failure = None
        planarity_failure = None
        for level_index, (level, center, path_tangent, frame) in enumerate(
            zip(levels, centers, path_tangents, frames)
        ):
            tangent, normal, binormal = frame
            average, minimum, maximum, radii = calculate_level_radius_data(
                level, center, tangent
            )
            if minimum <= _GEOMETRY_EPSILON:
                return result(
                    False,
                    "A transverse level has a degenerate radius",
                    ordered_chains=ordered_chains,
                    levels=levels,
                    path_length=path_length,
                    max_turn_angle=max_turn_angle,
                    frame_continuity=frame_continuity,
                )
            if (
                circularity_failure is None
                and not validate_level_circularity(radii, average)
            ):
                circularity_failure = level_index + 1
            axial_offsets = tuple(
                abs((vertex.co - center).dot(tangent)) for vertex in level
            )
            max_abs_offset = max(axial_offsets)
            mean_abs_offset = sum(axial_offsets) / len(axial_offsets)
            planarity_ratio = max_abs_offset / average
            mean_planarity_ratio = mean_abs_offset / average
            if (
                planarity_failure is None
                and (
                    planarity_ratio > _CURVE_PLANARITY_TOLERANCE
                    or mean_planarity_ratio > _CURVE_MEAN_PLANARITY_TOLERANCE
                )
            ):
                planarity_failure = level_index + 1
            global_min_radius = min(global_min_radius, minimum)
            global_max_radius = max(global_max_radius, maximum)
            level_info_items.append(
                CurvedLevelInfo(
                    center=center.copy(),
                    path_tangent=path_tangent.copy(),
                    tangent=tangent.copy(),
                    normal=normal.copy(),
                    binormal=binormal.copy(),
                    average_radius=average,
                    min_radius=minimum,
                    max_radius=maximum,
                    max_abs_axial_offset=max_abs_offset,
                    mean_abs_axial_offset=mean_abs_offset,
                    planarity_ratio=planarity_ratio,
                )
            )
        level_info = tuple(level_info_items)
        common_values = {
            "ordered_chains": ordered_chains,
            "levels": levels,
            "level_info": level_info,
            "path_length": path_length,
            "min_radius": global_min_radius,
            "max_radius": global_max_radius,
            "max_turn_angle": max_turn_angle,
            "frame_continuity": frame_continuity,
        }
        if circularity_failure is not None:
            return result(
                False,
                f"Level {circularity_failure} is not circular enough",
                **common_values,
            )
        if planarity_failure is not None:
            return result(
                False,
                f"Level {planarity_failure} is not planar enough",
                **common_values,
            )
        if not frame_continuity:
            return result(False, "Frame continuity failed", **common_values)
        return result(True, "Curved tube analysis is compatible", **common_values)
    except ValueError as error:
        return result(False, str(error))


def _validate_circular_structure(chains: Sequence[tuple[Any, ...]]) -> None:
    """Require a closed strip of matching lateral faces between every chain pair."""
    chain_count = len(chains)
    level_count = len(chains[0])
    for chain_index, chain in enumerate(chains):
        next_chain = chains[(chain_index + 1) % chain_count]
        for level in range(level_count):
            if _find_connecting_edge(chain[level], next_chain[level]) is None:
                raise ValueError(
                    "Selection is not one complete cylindrical surface"
                )

        for level in range(level_count - 1):
            face_vertices = {
                chain[level],
                chain[level + 1],
                next_chain[level],
                next_chain[level + 1],
            }
            common_faces = set(chain[level].link_faces)
            common_faces.intersection_update(chain[level + 1].link_faces)
            if not any(face_vertices.issubset(set(face.verts)) for face in common_faces):
                raise ValueError(
                    "Selected chains do not have compatible lateral faces"
                )


def _find_lateral_face(
    first_start: Any,
    first_end: Any,
    second_start: Any,
    second_end: Any,
) -> Any | None:
    """Find a face spanning two adjacent chains and two adjacent levels."""
    required_vertices = {first_start, first_end, second_start, second_end}
    common_faces = set(first_start.link_faces)
    common_faces.intersection_update(first_end.link_faces)
    for face in common_faces:
        if required_vertices.issubset(set(face.verts)):
            return face
    return None


def _validate_orthonormal_frame(
    tangent: Vector,
    normal: Vector,
    binormal: Vector,
) -> None:
    """Reject non-unit, non-perpendicular, or left-handed local frames."""
    tolerance = 1.0e-5
    if any(
        abs(vector.length - 1.0) > tolerance
        for vector in (tangent, normal, binormal)
    ):
        raise ValueError("Curved analysis contains a non-unit local frame")
    if any(
        abs(value) > tolerance
        for value in (
            tangent.dot(normal),
            tangent.dot(binormal),
            normal.dot(binormal),
        )
    ):
        raise ValueError("Curved analysis contains a non-orthogonal local frame")
    if tangent.cross(normal).dot(binormal) < 1.0 - tolerance:
        raise ValueError("Curved analysis contains an inverted local frame")


def order_curved_chains_circularly(
    analysis: CurvedTubeAnalysis,
) -> tuple[tuple[Any, ...], ...]:
    """Order all chains once using the first transported local frame."""
    if not analysis.valid or not analysis.level_info:
        raise ValueError("A valid curved analysis is required")
    first_level = analysis.level_info[0]
    _validate_orthonormal_frame(
        first_level.tangent,
        first_level.normal,
        first_level.binormal,
    )

    def chain_angle(chain: Sequence[Any]) -> float:
        relative = chain[0].co - first_level.center
        radial = relative - first_level.tangent * relative.dot(first_level.tangent)
        if radial.length <= _GEOMETRY_EPSILON:
            raise ValueError("A chain has a degenerate angular reference")
        return math.atan2(
            radial.dot(first_level.binormal),
            radial.dot(first_level.normal),
        )

    ordered_chains = tuple(sorted(analysis.ordered_chains, key=chain_angle))
    _validate_circular_structure(ordered_chains)
    return ordered_chains


def unwrap_angle_sequence(angles: Sequence[float]) -> tuple[float, ...]:
    """Choose the nearest equivalent angle at every consecutive level."""
    if not angles:
        return ()
    unwrapped = [angles[0]]
    for angle in angles[1:]:
        previous = unwrapped[-1]
        while angle - previous > math.pi:
            angle -= math.tau
        while angle - previous < -math.pi:
            angle += math.tau
        if abs(angle - previous) >= math.pi * 0.95:
            raise ValueError("Angular reference flips between consecutive levels")
        unwrapped.append(angle)
    return tuple(unwrapped)


def calculate_reference_angles_per_level(
    reference_chain: Sequence[Any],
    level_info: Sequence[CurvedLevelInfo],
) -> tuple[float, ...]:
    """Project one survivor through all transported local frames."""
    angles = []
    for vertex, info in zip(reference_chain, level_info):
        relative = vertex.co - info.center
        radial = relative - info.tangent * relative.dot(info.tangent)
        if radial.length <= _GEOMETRY_EPSILON:
            raise ValueError("A level has a degenerate angular reference")
        angles.append(math.atan2(radial.dot(info.binormal), radial.dot(info.normal)))
    return unwrap_angle_sequence(angles)


def classify_tube_end(
    level: Sequence[Any],
    adjacent_level: Sequence[Any],
    label: str,
) -> TubeEndInfo:
    """Classify one endpoint as open, one compatible ngon, or unsupported."""
    adjacent_vertices = set(adjacent_level)
    endpoint_faces = set()
    perimeter_edges = []
    for index, vertex in enumerate(level):
        next_vertex = level[(index + 1) % len(level)]
        edge = _find_connecting_edge(vertex, next_vertex)
        if edge is None:
            return TubeEndInfo(
                TubeEndType.UNSUPPORTED,
                None,
                f"End {label} uses unsupported cap topology",
            )
        perimeter_edges.append(edge)
        lateral_faces = tuple(
            face for face in edge.link_faces if adjacent_vertices.intersection(face.verts)
        )
        if len(lateral_faces) != 1:
            return TubeEndInfo(
                TubeEndType.UNSUPPORTED,
                None,
                f"End {label} uses unsupported cap topology",
            )
        endpoint_faces.update(
            face
            for face in edge.link_faces
            if not adjacent_vertices.intersection(face.verts)
        )

    if not endpoint_faces:
        if all(len(edge.link_faces) == 1 for edge in perimeter_edges):
            return TubeEndInfo(TubeEndType.OPEN, None, f"End {label} is open")
        return TubeEndInfo(
            TubeEndType.UNSUPPORTED,
            None,
            f"End {label} uses unsupported cap topology",
        )
    if len(endpoint_faces) != 1:
        return TubeEndInfo(
            TubeEndType.UNSUPPORTED,
            None,
            f"End {label} uses unsupported cap topology",
        )

    cap = next(iter(endpoint_faces))
    if (
        set(cap.verts) != set(level)
        or len(cap.verts) != len(level)
        or any(len(edge.link_faces) != 2 or cap not in edge.link_faces for edge in perimeter_edges)
    ):
        return TubeEndInfo(
            TubeEndType.UNSUPPORTED,
            None,
            f"End {label} uses unsupported cap topology",
        )
    return TubeEndInfo(
        TubeEndType.NGON_CAP,
        cap,
        f"End {label} has a compatible ngon cap",
    )


def classify_tube_ends(
    levels: Sequence[Sequence[Any]],
) -> tuple[TubeEndInfo, TubeEndInfo]:
    """Classify both longitudinal endpoints independently."""
    return (
        classify_tube_end(levels[0], levels[1], "A"),
        classify_tube_end(levels[-1], levels[-2], "B"),
    )


def _calculate_lateral_winding_sign(
    chains: Sequence[Sequence[Any]],
    centers: Sequence[Vector],
) -> int:
    """Require one consistent inward or outward winding on all lateral faces."""
    winding_sign = 0
    for chain_index, chain in enumerate(chains):
        next_chain = chains[(chain_index + 1) % len(chains)]
        for level_index in range(len(chain) - 1):
            face = _find_lateral_face(
                chain[level_index],
                chain[level_index + 1],
                next_chain[level_index],
                next_chain[level_index + 1],
            )
            if face is None:
                raise ValueError("A lateral face band is incomplete")
            centerline_point = (
                centers[level_index] + centers[level_index + 1]
            ) * 0.5
            outward = face.calc_center_median() - centerline_point
            orientation = face.normal.dot(outward)
            if abs(orientation) <= _GEOMETRY_EPSILON:
                raise ValueError("A lateral face has an ambiguous orientation")
            current_sign = 1 if orientation > 0.0 else -1
            if winding_sign and current_sign != winding_sign:
                raise ValueError("Lateral faces have inconsistent winding")
            winding_sign = current_sign
    return winding_sign


def collect_curved_reduction_data(
    analysis: CurvedTubeAnalysis,
    target_segments: int,
) -> CurvedReductionPlan:
    """Validate and collect every value needed before destructive editing."""
    if not analysis.valid:
        raise ValueError(analysis.status)
    current_segments = len(analysis.ordered_chains)
    if target_segments < 3:
        raise ValueError("Target must be at least 3")
    if target_segments >= current_segments:
        raise ValueError("Target must be lower than current segment count")
    remove_count = current_segments - target_segments
    if remove_count < 1:
        raise ValueError("At least one segment must be removed")
    if len(analysis.levels) < 2:
        raise ValueError("At least two transverse levels are required")
    if not analysis.frame_continuity:
        raise ValueError("Frame continuity failed")

    ordered_chains = order_curved_chains_circularly(analysis)
    levels = build_longitudinal_levels(ordered_chains)
    if len(levels) != len(analysis.level_info):
        raise ValueError("Curved level data is incomplete")
    for info in analysis.level_info:
        _validate_orthonormal_frame(info.tangent, info.normal, info.binormal)

    remove_indices = _uniform_removal_indices(current_segments, remove_count)
    removal_set = set(remove_indices)
    natural_survivors = tuple(
        index for index in range(current_segments) if index not in removal_set
    )
    first_removed = remove_indices[0]
    anchor_index = next(
        index
        for offset in range(1, current_segments + 1)
        for index in ((first_removed + offset) % current_segments,)
        if index not in removal_set
    )
    anchor_position = natural_survivors.index(anchor_index)
    survivor_indices = (
        natural_survivors[anchor_position:] + natural_survivors[:anchor_position]
    )
    if len(survivor_indices) != target_segments:
        raise ValueError("The requested number of surviving chains was not produced")
    survivor_chains = tuple(ordered_chains[index] for index in survivor_indices)

    centers = tuple(info.center.copy() for info in analysis.level_info)
    tangents = tuple(info.tangent.copy() for info in analysis.level_info)
    normals = tuple(info.normal.copy() for info in analysis.level_info)
    binormals = tuple(info.binormal.copy() for info in analysis.level_info)
    radii = tuple(info.average_radius for info in analysis.level_info)
    if any(radius <= _GEOMETRY_EPSILON for radius in radii):
        raise ValueError("A transverse level has a degenerate radius")
    reference_angles = calculate_reference_angles_per_level(
        survivor_chains[0], analysis.level_info
    )

    axial_offsets = []
    for level_index, info in enumerate(analysis.level_info):
        raw_offsets = tuple(
            (chain[level_index].co - info.center).dot(info.tangent)
            for chain in survivor_chains
        )
        average_offset = sum(raw_offsets) / len(raw_offsets)
        centered_offsets = tuple(value - average_offset for value in raw_offsets)
        max_abs_offset = max(abs(value) for value in centered_offsets)
        mean_abs_offset = sum(abs(value) for value in centered_offsets) / len(
            centered_offsets
        )
        maximum_limit = max(
            _GEOMETRY_EPSILON * 10.0,
            info.average_radius * _CURVE_PLANARITY_TOLERANCE,
        )
        mean_limit = max(
            _GEOMETRY_EPSILON * 10.0,
            info.average_radius * _CURVE_MEAN_PLANARITY_TOLERANCE,
        )
        if max_abs_offset > maximum_limit or mean_abs_offset > mean_limit:
            raise ValueError(f"Level {level_index + 1} is not planar enough")
        axial_offsets.append(centered_offsets)

    edges_to_dissolve = tuple(
        edge
        for index in remove_indices
        for first, second in zip(ordered_chains[index], ordered_chains[index][1:])
        for edge in (_find_connecting_edge(first, second),)
        if edge is not None
    )
    expected_edge_count = remove_count * (len(levels) - 1)
    if (
        len(edges_to_dissolve) != expected_edge_count
        or len(set(edges_to_dissolve)) != expected_edge_count
    ):
        raise ValueError("Could not resolve every curved chain marked for removal")

    end_infos = classify_tube_ends(levels)
    for end_info in end_infos:
        if end_info.end_type is TubeEndType.UNSUPPORTED:
            raise ValueError(end_info.status)
    lateral_winding_sign = _calculate_lateral_winding_sign(
        ordered_chains, centers
    )
    return CurvedReductionPlan(
        current_segments=current_segments,
        target_segments=target_segments,
        remove_indices=remove_indices,
        survivor_indices=survivor_indices,
        ordered_chains=ordered_chains,
        survivor_chains=survivor_chains,
        levels=levels,
        centers=centers,
        tangents=tangents,
        normals=normals,
        binormals=binormals,
        radii=radii,
        reference_angles=reference_angles,
        axial_offsets=tuple(axial_offsets),
        edges_to_dissolve=edges_to_dissolve,
        end_types=tuple(end_info.end_type for end_info in end_infos),
        cap_normals=tuple(
            end_info.cap_face.normal.copy()
            if end_info.cap_face is not None
            else None
            for end_info in end_infos
        ),
        cap_material_indices=tuple(
            end_info.cap_face.material_index
            if end_info.cap_face is not None
            else None
            for end_info in end_infos
        ),
        lateral_winding_sign=lateral_winding_sign,
    )


def redistribute_curved_survivors(plan: CurvedReductionPlan) -> None:
    """Redistribute survivors in each transported local frame."""
    angle_step = math.tau / plan.target_segments
    for level_index in range(len(plan.centers)):
        center = plan.centers[level_index]
        tangent = plan.tangents[level_index]
        normal = plan.normals[level_index]
        binormal = plan.binormals[level_index]
        radius = plan.radii[level_index]
        start_angle = plan.reference_angles[level_index]
        for chain_index, chain in enumerate(plan.survivor_chains):
            vertex = chain[level_index]
            if not vertex.is_valid:
                raise RuntimeError("A curved survivor vertex was removed unexpectedly")
            angle = start_angle + chain_index * angle_step
            radial_direction = (
                math.cos(angle) * normal + math.sin(angle) * binormal
            )
            vertex.co = (
                center
                + plan.axial_offsets[level_index][chain_index] * tangent
                + radius * radial_direction
            )


def select_curved_survivors(
    edit_mesh: Any,
    survivor_chains: Sequence[Sequence[Any]],
) -> None:
    """Leave only valid longitudinal survivor chains selected."""
    for vertex in edit_mesh.verts:
        vertex.select = False
    for edge in edit_mesh.edges:
        edge.select = False
    for face in edit_mesh.faces:
        face.select = False
    for chain in survivor_chains:
        for vertex in chain:
            if not vertex.is_valid:
                raise RuntimeError("A curved survivor vertex became invalid")
            vertex.select = True
        for first, second in zip(chain, chain[1:]):
            edge = _find_connecting_edge(first, second)
            if edge is None or not edge.is_valid:
                raise RuntimeError("A curved survivor edge is missing")
            edge.select = True


def validate_curved_result(
    edit_mesh: Any,
    plan: CurvedReductionPlan,
) -> None:
    """Validate geometry, winding, caps, centers, radii, and selection."""
    survivor_levels = build_longitudinal_levels(plan.survivor_chains)
    if any(not vertex.is_valid for level in survivor_levels for vertex in level):
        raise RuntimeError("Curved reduction left invalid survivor references")
    if len(plan.survivor_chains) != plan.target_segments:
        raise RuntimeError("Curved reduction produced the wrong chain count")
    _validate_circular_structure(plan.survivor_chains)

    geometry_scale = max(
        max(plan.radii),
        max(
            (second - first).length
            for first, second in zip(plan.centers, plan.centers[1:])
        ),
    )
    tolerance = max(
        _GEOMETRY_EPSILON * 100.0,
        geometry_scale * _CURVE_RESULT_TOLERANCE_RATIO,
    )
    calculated_centers = calculate_level_centers(survivor_levels)
    for expected, calculated in zip(plan.centers, calculated_centers):
        if (expected - calculated).length > tolerance:
            raise RuntimeError("Curved reduction changed the centerline")
    for level_index, level in enumerate(survivor_levels):
        _, minimum, maximum, radii = calculate_level_radius_data(
            level,
            plan.centers[level_index],
            plan.tangents[level_index],
        )
        expected_radius = plan.radii[level_index]
        if any(abs(radius - expected_radius) > tolerance for radius in radii):
            raise RuntimeError("Curved reduction did not preserve a level radius")
        if maximum - minimum > tolerance:
            raise RuntimeError("Curved reduction produced a non-circular level")

    if any(not vertex.link_edges for vertex in edit_mesh.verts):
        raise RuntimeError("Curved reduction produced loose vertices")
    if any(not edge.link_faces for edge in edit_mesh.edges):
        raise RuntimeError("Curved reduction produced loose edges")
    if any(face.calc_area() <= _GEOMETRY_EPSILON for face in edit_mesh.faces):
        raise RuntimeError("Curved reduction produced a degenerate face")
    if _calculate_lateral_winding_sign(
        plan.survivor_chains, plan.centers
    ) != plan.lateral_winding_sign:
        raise RuntimeError("Curved reduction inverted lateral face winding")

    end_infos = classify_tube_ends(survivor_levels)
    for index, end_info in enumerate(end_infos):
        if end_info.end_type is TubeEndType.UNSUPPORTED:
            raise RuntimeError(end_info.status)
        if end_info.end_type is not plan.end_types[index]:
            raise RuntimeError("Curved reduction changed endpoint closure")
        endpoint_level = survivor_levels[0 if index == 0 else -1]
        perimeter_edges = tuple(
            _find_connecting_edge(
                endpoint_level[vertex_index],
                endpoint_level[(vertex_index + 1) % plan.target_segments],
            )
            for vertex_index in range(plan.target_segments)
        )
        if any(edge is None for edge in perimeter_edges):
            raise RuntimeError("Curved reduction produced an invalid endpoint")
        if end_info.end_type is TubeEndType.OPEN:
            if (
                sum(len(edge.link_faces) == 1 for edge in perimeter_edges)
                != plan.target_segments
            ):
                raise RuntimeError("Curved reduction changed an open endpoint")
            continue
        cap = end_info.cap_face
        if cap is None:
            raise RuntimeError("Curved reduction lost an end cap")
        if len(cap.verts) != plan.target_segments:
            raise RuntimeError("Curved reduction produced an invalid end cap")
        if any(len(edge.link_faces) != 2 for edge in perimeter_edges):
            raise RuntimeError("Curved reduction opened a capped endpoint")
        if cap.normal.dot(plan.cap_normals[index]) <= 0.0:
            raise RuntimeError("Curved reduction inverted an end cap")
        if cap.material_index != plan.cap_material_indices[index]:
            raise RuntimeError("Curved reduction changed an end-cap material")

    expected_selected_vertices = plan.target_segments * len(plan.centers)
    expected_selected_edges = plan.target_segments * (len(plan.centers) - 1)
    if sum(vertex.select for vertex in edit_mesh.verts) != expected_selected_vertices:
        raise RuntimeError("Curved reduction left an invalid vertex selection")
    if sum(edge.select for edge in edit_mesh.edges) != expected_selected_edges:
        raise RuntimeError("Curved reduction left an invalid edge selection")
    if any(face.select for face in edit_mesh.faces):
        raise RuntimeError("Curved reduction selected faces unexpectedly")


def reduce_curved_tube(
    edit_mesh: Any,
    plan: CurvedReductionPlan,
) -> CurvedReductionResult:
    """Dissolve, redistribute, select, and validate one curved reduction."""
    before = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    bmesh.ops.dissolve_edges(
        edit_mesh,
        edges=plan.edges_to_dissolve,
        use_verts=True,
        use_face_split=False,
    )
    edit_mesh.verts.ensure_lookup_table()
    edit_mesh.edges.ensure_lookup_table()
    edit_mesh.faces.ensure_lookup_table()
    redistribute_curved_survivors(plan)
    select_curved_survivors(edit_mesh, plan.survivor_chains)
    edit_mesh.normal_update()
    validate_curved_result(edit_mesh, plan)
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    return CurvedReductionResult(
        success=True,
        message=(
            f"Reduced curved tube: {plan.current_segments} → "
            f"{plan.target_segments} | Levels: {len(plan.centers)}"
        ),
        vertex_count_before=before[0],
        vertex_count_after=after[0],
        edge_count_before=before[1],
        edge_count_after=after[1],
        face_count_before=before[2],
        face_count_after=after[2],
    )


def _uniform_removal_indices(current: int, remove_count: int) -> tuple[int, ...]:
    """Sample exactly remove_count deterministic indices around a circular range."""
    indices = tuple((index * current) // remove_count for index in range(remove_count))
    if len(set(indices)) != remove_count:
        raise ValueError("Could not distribute the requested removals")
    return indices


def build_reduction_plan(
    selected_edges: Iterable[Any],
    target_segments: int,
) -> ReductionPlan:
    """Revalidate selection and prepare all geometry before destructive editing."""
    selected_edges = tuple(selected_edges)
    analysis = analyze_selected_chains(selected_edges, target_segments)
    if not analysis.compatible:
        raise ValueError(analysis.status)

    components = separate_connected_edge_components(selected_edges)
    chains = tuple(_ordered_component_vertices(component) for component in components)
    axis = _calculate_axis(chains)
    chains = _orient_chains_to_axis(chains, axis)
    basis_u, basis_v = _perpendicular_basis(axis)

    representatives = tuple(_mean_position(chain) for chain in chains)
    representative_center = sum(
        representatives,
        Vector((0.0, 0.0, 0.0)),
    ) / len(representatives)

    def circular_angle(position: Vector) -> float:
        relative = position - representative_center
        radial = relative - axis * relative.dot(axis)
        if radial.length <= _GEOMETRY_EPSILON:
            raise ValueError("A chain lies too close to the longitudinal axis")
        return math.atan2(radial.dot(basis_v), radial.dot(basis_u))

    chains = tuple(sorted(chains, key=lambda chain: circular_angle(_mean_position(chain))))
    _validate_circular_structure(chains)

    level_count = len(chains[0])
    centers = []
    radii = []
    axial_offsets = []
    for level in range(level_count):
        level_vertices = tuple(chain[level] for chain in chains)
        center = _mean_position(level_vertices)
        offsets = tuple((vertex.co - center).dot(axis) for vertex in level_vertices)
        level_radii = tuple(
            ((vertex.co - center) - axis * offset).length
            for vertex, offset in zip(level_vertices, offsets)
        )
        radius = sum(level_radii) / len(level_radii)
        if radius <= _GEOMETRY_EPSILON:
            raise ValueError("A transverse level has a degenerate radius")
        centers.append(center.copy())
        radii.append(radius)
        axial_offsets.append(offsets)

    remove_count = len(chains) - target_segments
    removal_indices = set(_uniform_removal_indices(len(chains), remove_count))
    survivor_indices = tuple(
        index for index in range(len(chains)) if index not in removal_indices
    )
    if len(survivor_indices) != target_segments:
        raise ValueError("The requested number of surviving chains was not produced")

    anchor_index = survivor_indices[0]
    anchor_relative = _mean_position(chains[anchor_index]) - representative_center
    anchor_radial = anchor_relative - axis * anchor_relative.dot(axis)
    if anchor_radial.length <= _GEOMETRY_EPSILON:
        raise ValueError("Could not preserve a stable angular reference")
    start_angle = math.atan2(anchor_radial.dot(basis_v), anchor_radial.dot(basis_u))

    survivor_chains = tuple(chains[index] for index in survivor_indices)
    edges_to_dissolve = tuple(
        edge
        for index, component in enumerate(chains)
        if index in removal_indices
        for first, second in zip(component, component[1:])
        for edge in (_find_connecting_edge(first, second),)
        if edge is not None
    )
    expected_edge_count = remove_count * (level_count - 1)
    if len(edges_to_dissolve) != expected_edge_count:
        raise ValueError("Could not resolve every selected edge marked for removal")

    survivor_offsets = tuple(
        tuple(axial_offsets[level][index] for index in survivor_indices)
        for level in range(level_count)
    )
    return ReductionPlan(
        ordered_chains=chains,
        survivor_chains=survivor_chains,
        edges_to_dissolve=edges_to_dissolve,
        centers=tuple(centers),
        radii=tuple(radii),
        axial_offsets=survivor_offsets,
        basis_u=basis_u,
        basis_v=basis_v,
        axis=axis,
        start_angle=start_angle,
        target_segments=target_segments,
    )


def redistribute_surviving_chains(plan: ReductionPlan) -> None:
    """Place survivor vertices on uniform circles using one shared chain order."""
    angle_step = math.tau / plan.target_segments
    for chain_index, chain in enumerate(plan.survivor_chains):
        angle = plan.start_angle + chain_index * angle_step
        radial_direction = (
            math.cos(angle) * plan.basis_u
            + math.sin(angle) * plan.basis_v
        )
        for level, vertex in enumerate(chain):
            if not vertex.is_valid:
                raise RuntimeError("A surviving vertex was removed unexpectedly")
            vertex.co = (
                plan.centers[level]
                + plan.axial_offsets[level][chain_index] * plan.axis
                + plan.radii[level] * radial_direction
            )
