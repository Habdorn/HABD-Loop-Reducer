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
_PROFILE_FLAT_ANGLE_TOLERANCE = math.radians(2.0)
_PROFILE_MAX_BEVEL_TURN = math.radians(80.0)
_PROFILE_ISOLATED_FLAT_LENGTH_RATIO = 1.75
_PROFILE_MIN_FLAT_RUN_LENGTH_RATIO = 0.12
_PROFILE_TURN_AXIS_DOT_TOLERANCE = 0.25


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


class ProfileType(str, Enum):
    """Transverse topology detected for a profile band."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ProfileStructure(str, Enum):
    """Dispatch classification for PROFILE geometry."""

    FULL_OPEN = "FULL_OPEN"
    FULL_CLOSED = "FULL_CLOSED"
    BEVEL_REGIONS = "BEVEL_REGIONS"


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
class RadialIncreasePlan:
    """Fully validated data needed to rebuild one tubular surface."""

    current_segments: int
    target_segments: int
    ordered_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    centers: tuple[Vector, ...]
    tangents: tuple[Vector, ...]
    normals: tuple[Vector, ...]
    binormals: tuple[Vector, ...]
    radii: tuple[float, ...]
    reference_angles: tuple[float, ...]
    axial_offsets: tuple[tuple[float, ...], ...]
    lateral_faces: tuple[tuple[Any, ...], ...]
    end_types: tuple[TubeEndType, TubeEndType]
    cap_faces: tuple[Any | None, Any | None]
    cap_normals: tuple[Vector | None, Vector | None]
    cap_material_indices: tuple[int | None, int | None]
    lateral_winding_sign: int


@dataclass(frozen=True)
class RadialIncreaseResult:
    """New longitudinal chains and topology counts after an increase."""

    success: bool
    message: str
    chains: tuple[tuple[Any, ...], ...]
    vertex_count_before: int
    vertex_count_after: int
    edge_count_before: int
    edge_count_after: int
    face_count_before: int
    face_count_after: int


@dataclass(frozen=True)
class ProfileAnalysis:
    """Connectivity-derived analysis of one selected profile band."""

    valid: bool
    status: str
    profile_type: ProfileType | None
    structure: ProfileStructure | None
    ordered_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    band_faces: tuple[tuple[Any, ...], ...]
    regions: tuple["ProfileRegion", ...]


@dataclass(frozen=True)
class ProfileRegion:
    """One monotonic bevel span bounded by preserved longitudinal rails."""

    region_index: int
    chain_indices: tuple[int, ...]
    ordered_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    band_faces: tuple[tuple[Any, ...], ...]

    @property
    def current_segments(self) -> int:
        """Return the current sample count for this region."""
        return len(self.ordered_chains)


@dataclass(frozen=True)
class ProfileResamplePlan:
    """Complete immutable plan for one open or closed profile resample."""

    profile_type: ProfileType
    current_segments: int
    target_segments: int
    ordered_chains: tuple[tuple[Any, ...], ...]
    levels: tuple[tuple[Any, ...], ...]
    band_faces: tuple[tuple[Any, ...], ...]
    positions: tuple[tuple[Vector, ...], ...]
    source_face_indices: tuple[tuple[int, ...], ...]
    source_face_normals: tuple[tuple[Vector, ...], ...]
    source_face_materials: tuple[tuple[int, ...], ...]
    end_types: tuple[TubeEndType, TubeEndType] | None
    cap_faces: tuple[Any | None, Any | None]
    cap_normals: tuple[Vector | None, Vector | None]
    cap_material_indices: tuple[int | None, int | None]
    endpoint_coordinates: tuple[tuple[Vector, Vector], ...]
    external_elements: tuple[Any, ...]


@dataclass(frozen=True)
class ProfileResampleResult:
    """New chains and topology counts after a PROFILE operation."""

    success: bool
    message: str
    chains: tuple[tuple[Any, ...], ...]
    vertex_count_before: int
    vertex_count_after: int
    edge_count_before: int
    edge_count_after: int
    face_count_before: int
    face_count_after: int


@dataclass(frozen=True)
class ProfileBoundaryFacePlan:
    """One solid end face whose profile boundary must be resampled."""

    source_face: Any
    source_vertices: tuple[Any, ...]
    normal: Vector
    material_index: int


@dataclass(frozen=True)
class ProfileRegionsPlan:
    """Atomic collection of independently resampled bevel-region plans."""

    analysis: ProfileAnalysis
    target_segments: int
    region_plans: tuple[ProfileResamplePlan, ...]
    boundary_face_plans: tuple[ProfileBoundaryFacePlan, ...]
    preserved_vertices: tuple[Any, ...]
    preserved_vertex_coordinates: tuple[Vector, ...]
    preserved_edges: tuple[Any, ...]
    preserved_faces: tuple[Any, ...]
    preserved_face_materials: tuple[int, ...]


@dataclass(frozen=True)
class ProfileRegionsResult:
    """Result of one all-regions PROFILE operation."""

    success: bool
    message: str
    region_count: int
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
    if target_segments == current_segments:
        return result(True, "Compatible; target matches current segments")
    if target_segments > current_segments:
        return result(
            True,
            f"Compatible; increase by {target_segments - current_segments}",
        )
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


def _collect_lateral_faces(
    chains: Sequence[Sequence[Any]],
) -> tuple[tuple[Any, ...], ...]:
    """Resolve the regular quad band between every adjacent chain pair."""
    rows = []
    for chain_index, chain in enumerate(chains):
        next_chain = chains[(chain_index + 1) % len(chains)]
        row = []
        for level_index in range(len(chain) - 1):
            face = _find_lateral_face(
                chain[level_index],
                chain[level_index + 1],
                next_chain[level_index],
                next_chain[level_index + 1],
            )
            if face is None or len(face.verts) != 4:
                raise ValueError("Increase requires one regular quad lateral band")
            row.append(face)
        rows.append(tuple(row))
    if len({face for row in rows for face in row}) != len(chains) * (
        len(chains[0]) - 1
    ):
        raise ValueError("Lateral faces are duplicated or shared unexpectedly")
    return tuple(rows)


def _validate_isolated_tube_band(
    levels: Sequence[Sequence[Any]],
    lateral_faces: Sequence[Sequence[Any]],
    end_infos: Sequence[TubeEndInfo],
) -> None:
    """Reject attachments that would be lost when the selected band is rebuilt."""
    allowed_faces = {face for row in lateral_faces for face in row}
    allowed_faces.update(
        info.cap_face for info in end_infos if info.cap_face is not None
    )
    tube_vertices = {vertex for level in levels for vertex in level}
    for vertex in tube_vertices:
        if any(face not in allowed_faces for face in vertex.link_faces):
            raise ValueError("Increase does not support geometry attached to the tube")
        if any(
            edge.other_vert(vertex) not in tube_vertices for edge in vertex.link_edges
        ):
            raise ValueError("Increase does not support geometry attached to the tube")


def _interpolate_periodic_values(
    values: Sequence[float],
    target_segments: int,
) -> tuple[float, ...]:
    """Linearly sample circular per-chain values at uniform target angles."""
    count = len(values)
    sampled = []
    for target_index in range(target_segments):
        source_position = target_index * count / target_segments
        first_index = int(math.floor(source_position)) % count
        fraction = source_position - math.floor(source_position)
        second_index = (first_index + 1) % count
        sampled.append(
            values[first_index] * (1.0 - fraction)
            + values[second_index] * fraction
        )
    average = sum(sampled) / len(sampled)
    return tuple(value - average for value in sampled)


def _build_increase_plan(
    *,
    ordered_chains: Sequence[Sequence[Any]],
    centers: Sequence[Vector],
    tangents: Sequence[Vector],
    normals: Sequence[Vector],
    binormals: Sequence[Vector],
    radii: Sequence[float],
    reference_angles: Sequence[float],
    axial_offsets: Sequence[Sequence[float]],
    target_segments: int,
) -> RadialIncreasePlan:
    """Validate common topology and freeze all data before increasing."""
    current_segments = len(ordered_chains)
    if target_segments <= current_segments:
        raise ValueError("Target must be greater than current segment count")
    if target_segments < 3:
        raise ValueError("Target must be at least 3")
    levels = build_longitudinal_levels(ordered_chains)
    if not (
        len(levels)
        == len(centers)
        == len(tangents)
        == len(normals)
        == len(binormals)
        == len(radii)
        == len(reference_angles)
        == len(axial_offsets)
    ):
        raise ValueError("Increase geometry data is incomplete")
    for tangent, normal, binormal in zip(tangents, normals, binormals):
        _validate_orthonormal_frame(tangent, normal, binormal)
    if any(radius <= _GEOMETRY_EPSILON for radius in radii):
        raise ValueError("A transverse level has a degenerate radius")
    if any(len(offsets) != current_segments for offsets in axial_offsets):
        raise ValueError("Increase axial data is incomplete")

    lateral_faces = _collect_lateral_faces(ordered_chains)
    end_infos = classify_tube_ends(levels)
    for end_info in end_infos:
        if end_info.end_type is TubeEndType.UNSUPPORTED:
            raise ValueError(end_info.status)
    _validate_isolated_tube_band(levels, lateral_faces, end_infos)
    winding_sign = _calculate_lateral_winding_sign(ordered_chains, centers)
    sampled_offsets = tuple(
        _interpolate_periodic_values(offsets, target_segments)
        for offsets in axial_offsets
    )
    return RadialIncreasePlan(
        current_segments=current_segments,
        target_segments=target_segments,
        ordered_chains=tuple(tuple(chain) for chain in ordered_chains),
        levels=levels,
        centers=tuple(center.copy() for center in centers),
        tangents=tuple(tangent.copy() for tangent in tangents),
        normals=tuple(normal.copy() for normal in normals),
        binormals=tuple(binormal.copy() for binormal in binormals),
        radii=tuple(radii),
        reference_angles=tuple(reference_angles),
        axial_offsets=sampled_offsets,
        lateral_faces=lateral_faces,
        end_types=tuple(info.end_type for info in end_infos),
        cap_faces=tuple(info.cap_face for info in end_infos),
        cap_normals=tuple(
            info.cap_face.normal.copy() if info.cap_face is not None else None
            for info in end_infos
        ),
        cap_material_indices=tuple(
            info.cap_face.material_index if info.cap_face is not None else None
            for info in end_infos
        ),
        lateral_winding_sign=winding_sign,
    )


def build_straight_increase_plan(
    selected_edges: Iterable[Any],
    target_segments: int,
) -> RadialIncreasePlan:
    """Prepare a straight radial increase without mutating BMesh."""
    selected_edges = tuple(selected_edges)
    analysis = analyze_selected_chains(selected_edges, target_segments)
    if not analysis.compatible:
        raise ValueError(analysis.status)
    if target_segments <= analysis.current_segments:
        raise ValueError("Target must be greater than current segment count")

    components = separate_connected_edge_components(selected_edges)
    chains = tuple(_ordered_component_vertices(component) for component in components)
    axis = _calculate_axis(chains)
    chains = _orient_chains_to_axis(chains, axis)
    basis_u, basis_v = _perpendicular_basis(axis)
    representatives = tuple(_mean_position(chain) for chain in chains)
    representative_center = sum(
        representatives, Vector((0.0, 0.0, 0.0))
    ) / len(representatives)

    def circular_angle(chain: Sequence[Any]) -> float:
        relative = _mean_position(chain) - representative_center
        radial = relative - axis * relative.dot(axis)
        if radial.length <= _GEOMETRY_EPSILON:
            raise ValueError("A chain lies too close to the longitudinal axis")
        return math.atan2(radial.dot(basis_v), radial.dot(basis_u))

    chains = tuple(sorted(chains, key=circular_angle))
    _validate_circular_structure(chains)
    levels = build_longitudinal_levels(chains)
    centers = calculate_level_centers(levels)
    radii = []
    offsets = []
    for level, center in zip(levels, centers):
        raw_offsets = tuple((vertex.co - center).dot(axis) for vertex in level)
        level_radii = tuple(
            ((vertex.co - center) - axis * offset).length
            for vertex, offset in zip(level, raw_offsets)
        )
        radii.append(sum(level_radii) / len(level_radii))
        offset_average = sum(raw_offsets) / len(raw_offsets)
        offsets.append(tuple(value - offset_average for value in raw_offsets))
    start_angle = circular_angle(chains[0])
    return _build_increase_plan(
        ordered_chains=chains,
        centers=centers,
        tangents=(axis,) * len(levels),
        normals=(basis_u,) * len(levels),
        binormals=(basis_v,) * len(levels),
        radii=radii,
        reference_angles=(start_angle,) * len(levels),
        axial_offsets=offsets,
        target_segments=target_segments,
    )


def collect_curved_increase_data(
    analysis: CurvedTubeAnalysis,
    target_segments: int,
) -> RadialIncreasePlan:
    """Reuse curved analysis frames to prepare a radial increase."""
    if not analysis.valid:
        raise ValueError(analysis.status)
    if target_segments <= len(analysis.ordered_chains):
        raise ValueError("Target must be greater than current segment count")
    ordered_chains = order_curved_chains_circularly(analysis)
    reference_angles = calculate_reference_angles_per_level(
        ordered_chains[0], analysis.level_info
    )
    offsets = []
    for level_index, info in enumerate(analysis.level_info):
        raw = tuple(
            (chain[level_index].co - info.center).dot(info.tangent)
            for chain in ordered_chains
        )
        average = sum(raw) / len(raw)
        offsets.append(tuple(value - average for value in raw))
    return _build_increase_plan(
        ordered_chains=ordered_chains,
        centers=tuple(info.center for info in analysis.level_info),
        tangents=tuple(info.tangent for info in analysis.level_info),
        normals=tuple(info.normal for info in analysis.level_info),
        binormals=tuple(info.binormal for info in analysis.level_info),
        radii=tuple(info.average_radius for info in analysis.level_info),
        reference_angles=reference_angles,
        axial_offsets=offsets,
        target_segments=target_segments,
    )


def _copy_custom_data_layers(
    destination: Any,
    source: Any,
    layer_access: Any,
) -> None:
    """Copy assignable custom-data values without copying BMesh structure."""
    for collection_name in dir(layer_access):
        if collection_name.startswith("_"):
            continue
        collection = getattr(layer_access, collection_name, None)
        if collection is None or not hasattr(collection, "keys"):
            continue
        for layer_name in collection.keys():
            layer = collection.get(layer_name)
            try:
                value = source[layer]
                copier = getattr(value, "copy", None)
                destination[layer] = copier() if copier is not None else value
            except (AttributeError, KeyError, TypeError, ValueError):
                # Some Blender-managed layer values are intentionally read-only.
                continue


def _create_increased_geometry(
    edit_mesh: Any,
    plan: RadialIncreasePlan,
) -> tuple[tuple[Any, ...], ...]:
    """Create a complete replacement band before deleting original geometry."""
    level_count = len(plan.levels)
    new_levels = []
    created_vertices = []
    try:
        for level_index in range(level_count):
            level = []
            center = plan.centers[level_index]
            tangent = plan.tangents[level_index]
            normal = plan.normals[level_index]
            binormal = plan.binormals[level_index]
            for target_index in range(plan.target_segments):
                angle = (
                    plan.reference_angles[level_index]
                    + target_index * math.tau / plan.target_segments
                )
                coordinate = (
                    center
                    + plan.axial_offsets[level_index][target_index] * tangent
                    + plan.radii[level_index]
                    * (math.cos(angle) * normal + math.sin(angle) * binormal)
                )
                vertex = edit_mesh.verts.new(coordinate)
                level.append(vertex)
                created_vertices.append(vertex)
            new_levels.append(tuple(level))

        for target_index in range(plan.target_segments):
            for level_index in range(level_count - 1):
                edit_mesh.edges.new(
                    (
                        new_levels[level_index][target_index],
                        new_levels[level_index + 1][target_index],
                    )
                )

        for level_index in range(level_count):
            for target_index in range(plan.target_segments):
                following = (target_index + 1) % plan.target_segments
                edit_mesh.edges.new(
                    (
                        new_levels[level_index][target_index],
                        new_levels[level_index][following],
                    )
                )

        for target_index in range(plan.target_segments):
            following = (target_index + 1) % plan.target_segments
            source_index = int(
                math.floor(target_index * plan.current_segments / plan.target_segments)
            ) % plan.current_segments
            for level_index in range(level_count - 1):
                vertices = (
                    new_levels[level_index][target_index],
                    new_levels[level_index][following],
                    new_levels[level_index + 1][following],
                    new_levels[level_index + 1][target_index],
                )
                if plan.lateral_winding_sign < 0:
                    vertices = tuple(reversed(vertices))
                face = edit_mesh.faces.new(vertices)
                source_face = plan.lateral_faces[source_index][level_index]
                face.material_index = source_face.material_index
                _copy_custom_data_layers(
                    face, source_face, edit_mesh.faces.layers
                )
                for destination_loop, source_loop in zip(
                    face.loops, source_face.loops
                ):
                    _copy_custom_data_layers(
                        destination_loop, source_loop, edit_mesh.loops.layers
                    )

        for end_index, end_type in enumerate(plan.end_types):
            if end_type is TubeEndType.OPEN:
                continue
            level = new_levels[0 if end_index == 0 else -1]
            cap = edit_mesh.faces.new(level)
            cap.normal_update()
            expected_normal = plan.cap_normals[end_index]
            if expected_normal is not None and cap.normal.dot(expected_normal) < 0.0:
                cap.normal_flip()
            source_cap = plan.cap_faces[end_index]
            if source_cap is not None:
                cap.material_index = plan.cap_material_indices[end_index]
                _copy_custom_data_layers(
                    cap, source_cap, edit_mesh.faces.layers
                )
                for destination_loop, source_loop in zip(
                    cap.loops, source_cap.loops
                ):
                    _copy_custom_data_layers(
                        destination_loop, source_loop, edit_mesh.loops.layers
                    )
        return tuple(
            tuple(new_levels[level][chain] for level in range(level_count))
            for chain in range(plan.target_segments)
        )
    except Exception:
        valid_created = [vertex for vertex in created_vertices if vertex.is_valid]
        if valid_created:
            bmesh.ops.delete(edit_mesh, geom=valid_created, context="VERTS")
        raise


def validate_increased_result(
    edit_mesh: Any,
    plan: RadialIncreasePlan,
    chains: Sequence[Sequence[Any]],
    before: tuple[int, int, int],
) -> None:
    """Check counts, rings, connectivity, winding, ends, and selection."""
    levels = build_longitudinal_levels(chains)
    if len(chains) != plan.target_segments or len(levels) != len(plan.levels):
        raise RuntimeError("Increase produced the wrong chain or level count")
    _validate_circular_structure(chains)
    scale = max(max(plan.radii), 1.0)
    tolerance = max(
        _GEOMETRY_EPSILON * 100.0,
        scale * _CURVE_RESULT_TOLERANCE_RATIO,
    )
    for level_index, level in enumerate(levels):
        center = _mean_position(level)
        if (center - plan.centers[level_index]).length > tolerance:
            raise RuntimeError("Increase changed a transverse center")
        angles = []
        for vertex in level:
            relative = vertex.co - plan.centers[level_index]
            radial = relative - plan.tangents[level_index] * relative.dot(
                plan.tangents[level_index]
            )
            if abs(radial.length - plan.radii[level_index]) > tolerance:
                raise RuntimeError("Increase did not preserve a level radius")
            angles.append(
                math.atan2(
                    radial.dot(plan.binormals[level_index]),
                    radial.dot(plan.normals[level_index]),
                )
            )
        unwrapped = unwrap_angle_sequence(angles)
        expected_step = math.tau / plan.target_segments
        differences = tuple(
            (unwrapped[(index + 1) % len(unwrapped)] - unwrapped[index]) % math.tau
            for index in range(len(unwrapped))
        )
        if any(abs(value - expected_step) > tolerance for value in differences):
            raise RuntimeError("Increase produced non-uniform radial spacing")

    new_vertices = {vertex for level in levels for vertex in level}
    new_edges = {edge for vertex in new_vertices for edge in vertex.link_edges}
    new_faces = {face for vertex in new_vertices for face in vertex.link_faces}
    if any(not vertex.link_edges for vertex in new_vertices):
        raise RuntimeError("Increase produced loose vertices")
    if any(not edge.link_faces for edge in new_edges):
        raise RuntimeError("Increase produced loose edges")
    if any(face.calc_area() <= _GEOMETRY_EPSILON for face in new_faces):
        raise RuntimeError("Increase produced a degenerate face")
    if (
        _calculate_lateral_winding_sign(chains, plan.centers)
        != plan.lateral_winding_sign
    ):
        raise RuntimeError("Increase inverted lateral face winding")
    end_infos = classify_tube_ends(levels)
    for index, end_info in enumerate(end_infos):
        if end_info.end_type is not plan.end_types[index]:
            raise RuntimeError("Increase changed endpoint closure")
        if end_info.cap_face is not None:
            if len(end_info.cap_face.verts) != plan.target_segments:
                raise RuntimeError("Increase produced an invalid end cap")
            if end_info.cap_face.normal.dot(plan.cap_normals[index]) <= 0.0:
                raise RuntimeError("Increase inverted an end cap")
            if end_info.cap_face.material_index != plan.cap_material_indices[index]:
                raise RuntimeError("Increase changed an end-cap material")

    delta = plan.target_segments - plan.current_segments
    expected = (
        before[0] + delta * len(levels),
        before[1] + delta * (2 * len(levels) - 1),
        before[2] + delta * (len(levels) - 1),
    )
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    if after != expected:
        raise RuntimeError("Increase produced unexpected topology counts")
    if (
        sum(vertex.select for vertex in edit_mesh.verts)
        != plan.target_segments * len(levels)
    ):
        raise RuntimeError("Increase left an invalid vertex selection")
    if (
        sum(edge.select for edge in edit_mesh.edges)
        != plan.target_segments * (len(levels) - 1)
    ):
        raise RuntimeError("Increase left an invalid edge selection")
    if any(face.select for face in edit_mesh.faces):
        raise RuntimeError("Increase selected faces unexpectedly")


def increase_tube_segments(
    edit_mesh: Any,
    plan: RadialIncreasePlan,
    *,
    curved: bool,
) -> RadialIncreaseResult:
    """Rebuild only the selected tube band at a larger radial resolution."""
    before = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    new_chains = _create_increased_geometry(edit_mesh, plan)
    old_vertices = tuple(vertex for level in plan.levels for vertex in level)
    bmesh.ops.delete(edit_mesh, geom=old_vertices, context="VERTS")
    edit_mesh.verts.ensure_lookup_table()
    edit_mesh.edges.ensure_lookup_table()
    edit_mesh.faces.ensure_lookup_table()
    select_curved_survivors(edit_mesh, new_chains)
    edit_mesh.normal_update()
    validate_increased_result(edit_mesh, plan, new_chains, before)
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    geometry_label = "curved tube" if curved else "segments"
    return RadialIncreaseResult(
        success=True,
        message=(
            f"Increased {geometry_label}: {plan.current_segments} → "
            f"{plan.target_segments} | Levels: {len(plan.levels)}"
        ),
        chains=new_chains,
        vertex_count_before=before[0],
        vertex_count_after=after[0],
        edge_count_before=before[1],
        edge_count_after=after[1],
        face_count_before=before[2],
        face_count_after=after[2],
    )


def _profile_chain_key(chain: Sequence[Any]) -> tuple[int, int]:
    """Provide a stable tie-breaker for a topologically symmetric profile."""
    indices = tuple(vertex.index for vertex in chain if vertex.index >= 0)
    return (min(indices, default=-1), len(chain))


def _orient_and_order_profile_chains(
    components: Sequence[Sequence[Any]],
) -> tuple[ProfileType, tuple[tuple[Any, ...], ...]]:
    """Derive profile type, longitudinal orientation, and transverse order."""
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
                raise ValueError(
                    "Profile correspondence is inconsistent between levels"
                )
            adjacency[first_index].append((second_index, is_reversed))
            adjacency[second_index].append((first_index, is_reversed))

    degrees = tuple(len(neighbors) for neighbors in adjacency)
    if degrees and all(degree == 2 for degree in degrees):
        profile_type = ProfileType.CLOSED
    elif (
        degrees.count(1) == 2
        and all(degree in {1, 2} for degree in degrees)
    ):
        profile_type = ProfileType.OPEN
    else:
        raise ValueError("Selected chains do not form one open or closed profile")

    start_index = min(
        (
            index
            for index, degree in enumerate(degrees)
            if profile_type is ProfileType.CLOSED or degree == 1
        ),
        key=lambda index: _profile_chain_key(raw_chains[index]),
    )
    orientation = {start_index: False}
    pending = [start_index]
    while pending:
        current = pending.pop()
        for neighbor, reverses in adjacency[current]:
            expected = orientation[current] ^ reverses
            if neighbor in orientation:
                if orientation[neighbor] != expected:
                    raise ValueError("Profile chain orientation is inconsistent")
                continue
            orientation[neighbor] = expected
            pending.append(neighbor)
    if len(orientation) != len(raw_chains):
        raise ValueError("Selection contains more than one profile band")

    order = [start_index]
    previous = None
    current = start_index
    while True:
        candidates = [
            neighbor for neighbor, _ in adjacency[current] if neighbor != previous
        ]
        if not candidates:
            break
        if previous is None and len(candidates) > 1:
            next_index = min(
                candidates, key=lambda index: _profile_chain_key(raw_chains[index])
            )
        else:
            next_index = candidates[0]
        if next_index == start_index:
            break
        if next_index in order:
            raise ValueError("Profile order is ambiguous")
        order.append(next_index)
        previous, current = current, next_index
    if len(order) != len(raw_chains):
        raise ValueError("Profile transverse order is incomplete")

    ordered = tuple(
        tuple(reversed(raw_chains[index]))
        if orientation[index]
        else tuple(raw_chains[index])
        for index in order
    )
    return profile_type, ordered


def _collect_profile_band_faces(
    chains: Sequence[Sequence[Any]],
    profile_type: ProfileType,
) -> tuple[tuple[Any, ...], ...]:
    """Resolve every regular quad in an open or closed profile band."""
    interval_count = (
        len(chains) if profile_type is ProfileType.CLOSED else len(chains) - 1
    )
    rows = []
    for chain_index in range(interval_count):
        following = (chain_index + 1) % len(chains)
        row = []
        for level_index in range(len(chains[0]) - 1):
            face = _find_lateral_face(
                chains[chain_index][level_index],
                chains[chain_index][level_index + 1],
                chains[following][level_index],
                chains[following][level_index + 1],
            )
            if face is None or len(face.verts) != 4:
                raise ValueError("PROFILE requires one regular quad band")
            row.append(face)
        rows.append(tuple(row))
    expected = interval_count * (len(chains[0]) - 1)
    if len({face for row in rows for face in row}) != expected:
        raise ValueError("Profile faces are duplicated or shared unexpectedly")
    return tuple(rows)


def _profile_interval_measurements(
    levels: Sequence[Sequence[Any]],
    profile_type: ProfileType,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Measure median interval lengths and maximum turns across all levels."""
    interval_count = (
        len(levels[0])
        if profile_type is ProfileType.CLOSED
        else len(levels[0]) - 1
    )
    lengths_by_interval = [[] for _ in range(interval_count)]
    turn_count = (
        interval_count
        if profile_type is ProfileType.CLOSED
        else interval_count - 1
    )
    turns_by_boundary = [[] for _ in range(turn_count)]
    for level in levels:
        directions = []
        for interval in range(interval_count):
            following = (interval + 1) % len(level)
            edge_vector = level[following].co - level[interval].co
            lengths_by_interval[interval].append(edge_vector.length)
            directions.append(edge_vector.normalized())
        for boundary in range(turn_count):
            following = (boundary + 1) % interval_count
            turns_by_boundary[boundary].append(
                math.acos(
                    max(-1.0, min(1.0, directions[boundary].dot(directions[following])))
                )
            )
    median_lengths = tuple(
        sorted(values)[len(values) // 2] for values in lengths_by_interval
    )
    maximum_turns = tuple(max(values) for values in turns_by_boundary)
    return median_lengths, maximum_turns


def _profile_flat_interval_mask(
    levels: Sequence[Sequence[Any]],
    profile_type: ProfileType,
) -> tuple[bool, ...]:
    """Classify flat intervals using direction plateaus and isolated long spans."""
    lengths, turns = _profile_interval_measurements(levels, profile_type)
    interval_count = len(lengths)
    flat = [False] * interval_count
    for boundary, angle in enumerate(turns):
        if angle <= _PROFILE_FLAT_ANGLE_TOLERANCE:
            flat[boundary] = True
            flat[(boundary + 1) % interval_count] = True

    for interval in range(interval_count):
        if flat[interval]:
            continue
        if profile_type is ProfileType.OPEN and interval == 0:
            neighbor_length = lengths[1]
        elif profile_type is ProfileType.OPEN and interval == interval_count - 1:
            neighbor_length = lengths[-2]
        else:
            previous = (interval - 1) % interval_count
            following = (interval + 1) % interval_count
            neighbor_length = max(lengths[previous], lengths[following])
        if (
            neighbor_length > _GEOMETRY_EPSILON
            and lengths[interval]
            >= neighbor_length * _PROFILE_ISOLATED_FLAT_LENGTH_RATIO
        ):
            flat[interval] = True
    total_length = sum(lengths)
    if total_length <= _GEOMETRY_EPSILON or not any(flat):
        return tuple(flat)
    qualifying = [False] * interval_count
    remaining = {index for index, value in enumerate(flat) if value}
    while remaining:
        first = remaining.pop()
        run = {first}
        pending = [first]
        while pending:
            interval = pending.pop()
            neighbor_boundaries = []
            if interval > 0:
                neighbor_boundaries.append((interval - 1, interval - 1))
            elif profile_type is ProfileType.CLOSED:
                neighbor_boundaries.append((interval_count - 1, interval_count - 1))
            if interval < interval_count - 1:
                neighbor_boundaries.append((interval + 1, interval))
            elif profile_type is ProfileType.CLOSED:
                neighbor_boundaries.append((0, interval_count - 1))
            for neighbor, boundary in neighbor_boundaries:
                if (
                    neighbor in remaining
                    and turns[boundary] <= _PROFILE_FLAT_ANGLE_TOLERANCE
                ):
                    remaining.remove(neighbor)
                    run.add(neighbor)
                    pending.append(neighbor)
        if sum(lengths[item] for item in run) >= (
            total_length * _PROFILE_MIN_FLAT_RUN_LENGTH_RATIO
        ):
            for item in run:
                qualifying[item] = True
    return tuple(qualifying)


def _profile_flat_run_count(
    flat_mask: Sequence[bool],
    profile_type: ProfileType,
) -> int:
    """Count separated flat sections in an open or periodic interval mask."""
    if not any(flat_mask):
        return 0
    if profile_type is ProfileType.OPEN:
        return sum(
            value and (index == 0 or not flat_mask[index - 1])
            for index, value in enumerate(flat_mask)
        )
    return sum(
        value and not flat_mask[index - 1]
        for index, value in enumerate(flat_mask)
    ) or 1


def _profile_nonflat_runs(
    flat_mask: Sequence[bool],
    profile_type: ProfileType,
) -> tuple[tuple[int, ...], ...]:
    """Return non-flat interval runs that are bounded by preserved flats."""
    interval_count = len(flat_mask)
    runs = []
    if profile_type is ProfileType.OPEN:
        index = 0
        while index < interval_count:
            if flat_mask[index]:
                index += 1
                continue
            start = index
            while index < interval_count and not flat_mask[index]:
                index += 1
            if start > 0 and index < interval_count:
                runs.append(tuple(range(start, index)))
        return tuple(runs)

    if not any(flat_mask):
        return ()
    anchor = next(index for index, value in enumerate(flat_mask) if value)
    current = []
    for offset in range(1, interval_count + 1):
        interval = (anchor + offset) % interval_count
        if flat_mask[interval]:
            if current:
                runs.append(tuple(current))
                current = []
        else:
            current.append(interval)
    if current:
        runs.append(tuple(current))
    return tuple(runs)


def _validate_monotonic_profile_region(
    levels: Sequence[Sequence[Any]],
) -> None:
    """Require a gradual, consistently turning polyline in every level."""
    for level in levels:
        directions = tuple(
            (second.co - first.co).normalized()
            for first, second in zip(level, level[1:])
        )
        axes = []
        for first, second in zip(directions, directions[1:]):
            angle = math.acos(max(-1.0, min(1.0, first.dot(second))))
            if angle <= _PROFILE_FLAT_ANGLE_TOLERANCE:
                continue
            if angle >= _PROFILE_MAX_BEVEL_TURN:
                raise ValueError("A bevel region contains an abrupt corner")
            axis = first.cross(second)
            if axis.length > _GEOMETRY_EPSILON:
                axes.append(axis.normalized())
        if not axes:
            raise ValueError("A bevel region is geometrically flat")
        for first, second in zip(axes, axes[1:]):
            if first.dot(second) < _PROFILE_TURN_AXIS_DOT_TOLERANCE:
                raise ValueError("A bevel region changes turning direction")


def detect_profile_regions(
    profile_type: ProfileType,
    ordered_chains: Sequence[Sequence[Any]],
    levels: Sequence[Sequence[Any]],
    band_faces: Sequence[Sequence[Any]],
) -> tuple[ProfileRegion, ...]:
    """Detect monotonic bevel spans separated by preserved flat intervals."""
    flat_mask = _profile_flat_interval_mask(levels, profile_type)
    if profile_type is ProfileType.CLOSED and _profile_flat_run_count(
        flat_mask, profile_type
    ) < 2:
        return ()
    interval_runs = _profile_nonflat_runs(flat_mask, profile_type)
    regions = []
    for interval_run in interval_runs:
        if len(interval_run) < 2:
            continue
        chain_indices = interval_run + (
            (interval_run[-1] + 1) % len(ordered_chains),
        )
        region_chains = tuple(ordered_chains[index] for index in chain_indices)
        region_levels = build_longitudinal_levels(region_chains)
        _validate_monotonic_profile_region(region_levels)
        regions.append(
            ProfileRegion(
                region_index=len(regions),
                chain_indices=chain_indices,
                ordered_chains=region_chains,
                levels=region_levels,
                band_faces=tuple(band_faces[index] for index in interval_run),
            )
        )
    return tuple(regions)


def _detect_integrated_open_profile_region(
    ordered_chains: Sequence[Sequence[Any]],
    levels: Sequence[Sequence[Any]],
    band_faces: Sequence[Sequence[Any]],
) -> tuple[ProfileRegion, ...]:
    """Recognize one selected bevel bounded by unselected flat side faces."""
    try:
        _validate_monotonic_profile_region(levels)
    except ValueError:
        return ()

    band_face_set = {face for row in band_faces for face in row}
    profile_vertices = {vertex for level in levels for vertex in level}
    endpoint_vertices = set(levels[0]) | set(levels[-1])
    boundary_vertices = set(ordered_chains[0]) | set(ordered_chains[-1])

    # Both longitudinal boundary rails must continue into a real exterior
    # surface. This is what distinguishes an integrated bevel from FULL_OPEN.
    for chain in (ordered_chains[0], ordered_chains[-1]):
        for first, second in zip(chain, chain[1:]):
            rail_edge = next(
                (
                    edge
                    for edge in first.link_edges
                    if edge.other_vert(first) is second
                ),
                None,
            )
            if rail_edge is None:
                return ()
            exterior_faces = tuple(
                face for face in rail_edge.link_faces if face not in band_face_set
            )
            if len(exterior_faces) != 1:
                return ()

    # Interior samples may touch only terminal solid faces. Arbitrary side
    # attachments remain a FULL_OPEN validation error during Apply.
    terminal_faces = set()
    for vertex in profile_vertices - boundary_vertices:
        for face in vertex.link_faces:
            if face in band_face_set:
                continue
            attached_profile_vertices = set(face.verts) & profile_vertices
            if not attached_profile_vertices or not (
                attached_profile_vertices <= set(levels[0])
                or attached_profile_vertices <= set(levels[-1])
            ):
                return ()
            terminal_faces.add(face)
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            if other in profile_vertices:
                continue
            if vertex not in endpoint_vertices or not any(
                face in terminal_faces for face in edge.link_faces
            ):
                return ()

    return (
        ProfileRegion(
            region_index=0,
            chain_indices=tuple(range(len(ordered_chains))),
            ordered_chains=tuple(tuple(chain) for chain in ordered_chains),
            levels=tuple(tuple(level) for level in levels),
            band_faces=tuple(tuple(row) for row in band_faces),
        ),
    )


def analyze_profile(selected_edges: Iterable[Any]) -> ProfileAnalysis:
    """Analyze selected longitudinal chains as an open or closed profile."""
    selected_edges = tuple(selected_edges)

    def result(
        valid: bool,
        status: str,
        *,
        profile_type: ProfileType | None = None,
        structure: ProfileStructure | None = None,
        ordered_chains: tuple[tuple[Any, ...], ...] = (),
        levels: tuple[tuple[Any, ...], ...] = (),
        band_faces: tuple[tuple[Any, ...], ...] = (),
        regions: tuple[ProfileRegion, ...] = (),
    ) -> ProfileAnalysis:
        return ProfileAnalysis(
            valid=valid,
            status=status,
            profile_type=profile_type,
            structure=structure,
            ordered_chains=ordered_chains,
            levels=levels,
            band_faces=band_faces,
            regions=regions,
        )

    if not selected_edges:
        return result(False, "No selected longitudinal chains")
    components = separate_connected_edge_components(selected_edges)
    component_info = tuple(classify_edge_component(item) for item in components)
    if any(item.is_branched for item in component_info):
        return result(False, "Selection contains branched longitudinal chains")
    if any(item.is_closed for item in component_info):
        return result(False, "Longitudinal chains must be open")
    if any(not item.is_open_chain for item in component_info):
        return result(False, "Selection contains invalid longitudinal chains")
    if len(components) < 3:
        return result(False, "Select at least 3 longitudinal profile samples")
    if len({item.edge_count for item in component_info}) != 1:
        return result(False, "Selected chains have different level counts")
    try:
        profile_type, ordered_chains = _orient_and_order_profile_chains(components)
        levels = build_longitudinal_levels(ordered_chains)
        band_faces = _collect_profile_band_faces(ordered_chains, profile_type)
        for level_index, level in enumerate(levels):
            interval_count = (
                len(level)
                if profile_type is ProfileType.CLOSED
                else len(level) - 1
            )
            for index in range(interval_count):
                following = (index + 1) % len(level)
                if (level[following].co - level[index].co).length <= _GEOMETRY_EPSILON:
                    raise ValueError(
                        f"Profile level {level_index + 1} contains a zero-length edge"
                    )
        regions = ()
        if profile_type is ProfileType.OPEN:
            regions = _detect_integrated_open_profile_region(
                ordered_chains, levels, band_faces
            )
        if not regions:
            regions = detect_profile_regions(
                profile_type, ordered_chains, levels, band_faces
            )
        structure = (
            ProfileStructure.BEVEL_REGIONS
            if regions
            else (
                ProfileStructure.FULL_CLOSED
                if profile_type is ProfileType.CLOSED
                else ProfileStructure.FULL_OPEN
            )
        )
        status = (
            f"Bevel regions are compatible ({len(regions)} detected)"
            if regions
            else f"{profile_type.value.title()} profile is compatible"
        )
        return result(
            True,
            status,
            profile_type=profile_type,
            structure=structure,
            ordered_chains=ordered_chains,
            levels=levels,
            band_faces=band_faces,
            regions=regions,
        )
    except ValueError as error:
        return result(False, str(error))


def _profile_cumulative_lengths(
    level: Sequence[Any],
    profile_type: ProfileType,
) -> tuple[tuple[float, ...], float]:
    """Return cumulative polyline distances and total profile length."""
    interval_count = (
        len(level) if profile_type is ProfileType.CLOSED else len(level) - 1
    )
    cumulative = [0.0]
    for index in range(interval_count):
        following = (index + 1) % len(level)
        length = (level[following].co - level[index].co).length
        if length <= _GEOMETRY_EPSILON:
            raise ValueError("Profile contains a zero-length edge")
        cumulative.append(cumulative[-1] + length)
    if cumulative[-1] <= _GEOMETRY_EPSILON:
        raise ValueError("Profile has zero total length")
    return tuple(cumulative), cumulative[-1]


def _profile_segment_at_distance(
    cumulative: Sequence[float],
    distance: float,
) -> tuple[int, float]:
    """Locate and interpolate one distance along a cumulative polyline."""
    total = cumulative[-1]
    distance = max(0.0, min(distance, total))
    for index in range(len(cumulative) - 1):
        if distance <= cumulative[index + 1] or index == len(cumulative) - 2:
            span = cumulative[index + 1] - cumulative[index]
            return index, (distance - cumulative[index]) / span
    raise ValueError("Could not locate a profile sample")


def _sample_profile_level(
    level: Sequence[Any],
    profile_type: ProfileType,
    target_segments: int,
) -> tuple[tuple[Vector, ...], tuple[float, ...], tuple[float, ...]]:
    """Sample one transverse polyline uniformly by cumulative arc length."""
    cumulative, total = _profile_cumulative_lengths(level, profile_type)
    denominator = (
        target_segments
        if profile_type is ProfileType.CLOSED
        else target_segments - 1
    )
    fractions = tuple(index / denominator for index in range(target_segments))
    positions = []
    for index, fraction in enumerate(fractions):
        if profile_type is ProfileType.OPEN and index == 0:
            positions.append(level[0].co.copy())
            continue
        if profile_type is ProfileType.OPEN and index == target_segments - 1:
            positions.append(level[-1].co.copy())
            continue
        segment, blend = _profile_segment_at_distance(
            cumulative, fraction * total
        )
        following = (segment + 1) % len(level)
        positions.append(level[segment].co.lerp(level[following].co, blend))
    return tuple(positions), fractions, cumulative


def _validate_profile_external_geometry(
    analysis: ProfileAnalysis,
) -> tuple[tuple[Any, ...], tuple[tuple[Vector, Vector], ...]]:
    """Allow exterior attachments only on preserved OPEN boundary rails."""
    band_faces = {face for row in analysis.band_faces for face in row}
    tube_vertices = {
        vertex for level in analysis.levels for vertex in level
    }
    if analysis.profile_type is ProfileType.CLOSED:
        end_infos = classify_tube_ends(analysis.levels)
        _validate_isolated_tube_band(
            analysis.levels, analysis.band_faces, end_infos
        )
        return (), ()

    boundary_vertices = {
        vertex
        for chain in (
            analysis.ordered_chains[0],
            analysis.ordered_chains[-1],
        )
        for vertex in chain
    }
    external = set()
    for vertex in tube_vertices:
        for face in vertex.link_faces:
            if face in band_faces:
                continue
            if vertex not in boundary_vertices:
                raise ValueError(
                    "External geometry is attached inside the open profile"
                )
            external.add(face)
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            if other in tube_vertices:
                continue
            if vertex not in boundary_vertices:
                raise ValueError(
                    "External geometry is attached inside the open profile"
                )
            external.add(edge)
            external.add(other)
    endpoint_coordinates = tuple(
        (level[0].co.copy(), level[-1].co.copy())
        for level in analysis.levels
    )
    return tuple(external), endpoint_coordinates


def _build_profile_resample_plan(
    analysis: ProfileAnalysis,
    target_segments: int,
    external_elements: Sequence[Any],
    endpoint_coordinates: Sequence[tuple[Vector, Vector]],
) -> ProfileResamplePlan:
    """Build a resample plan after structure-specific attachment validation."""
    if not analysis.valid or analysis.profile_type is None:
        raise ValueError(analysis.status)
    current_segments = len(analysis.ordered_chains)
    if target_segments < 3:
        raise ValueError("Target must be at least 3 profile samples")
    if target_segments == current_segments:
        raise ValueError("Target already matches current profile samples")

    positions = []
    source_face_indices = []
    interval_target_count = (
        target_segments
        if analysis.profile_type is ProfileType.CLOSED
        else target_segments - 1
    )
    for level in analysis.levels:
        level_positions, _, cumulative = _sample_profile_level(
            level, analysis.profile_type, target_segments
        )
        positions.append(level_positions)
        total = cumulative[-1]
        denominator = interval_target_count
        indices = []
        for target_interval in range(interval_target_count):
            midpoint_fraction = (target_interval + 0.5) / denominator
            source_index, _ = _profile_segment_at_distance(
                cumulative, midpoint_fraction * total
            )
            indices.append(source_index)
        source_face_indices.append(tuple(indices))

    for level_index in range(len(positions) - 1):
        for interval in range(interval_target_count):
            following = (interval + 1) % target_segments
            a = positions[level_index][interval]
            b = positions[level_index][following]
            c = positions[level_index + 1][following]
            d = positions[level_index + 1][interval]
            area = (b - a).cross(d - a).length + (c - b).cross(d - b).length
            if area <= _GEOMETRY_EPSILON:
                raise ValueError("PROFILE would create a degenerate quad")

    source_face_normals = []
    source_face_materials = []
    for level_index in range(len(analysis.levels) - 1):
        normals = []
        materials = []
        for interval in range(interval_target_count):
            source_index = source_face_indices[level_index][interval]
            source_face = analysis.band_faces[source_index][level_index]
            normals.append(source_face.normal.copy())
            materials.append(source_face.material_index)
        source_face_normals.append(tuple(normals))
        source_face_materials.append(tuple(materials))

    end_types = None
    cap_faces: tuple[Any | None, Any | None] = (None, None)
    cap_normals: tuple[Vector | None, Vector | None] = (None, None)
    cap_materials: tuple[int | None, int | None] = (None, None)
    if analysis.profile_type is ProfileType.CLOSED:
        end_infos = classify_tube_ends(analysis.levels)
        for info in end_infos:
            if info.end_type is TubeEndType.UNSUPPORTED:
                raise ValueError(info.status)
        end_types = tuple(info.end_type for info in end_infos)
        cap_faces = tuple(info.cap_face for info in end_infos)
        cap_normals = tuple(
            info.cap_face.normal.copy() if info.cap_face is not None else None
            for info in end_infos
        )
        cap_materials = tuple(
            info.cap_face.material_index if info.cap_face is not None else None
            for info in end_infos
        )

    return ProfileResamplePlan(
        profile_type=analysis.profile_type,
        current_segments=current_segments,
        target_segments=target_segments,
        ordered_chains=analysis.ordered_chains,
        levels=analysis.levels,
        band_faces=analysis.band_faces,
        positions=tuple(positions),
        source_face_indices=tuple(source_face_indices),
        source_face_normals=tuple(source_face_normals),
        source_face_materials=tuple(source_face_materials),
        end_types=end_types,
        cap_faces=cap_faces,
        cap_normals=cap_normals,
        cap_material_indices=cap_materials,
        endpoint_coordinates=tuple(endpoint_coordinates),
        external_elements=tuple(external_elements),
    )


def build_profile_resample_plan(
    analysis: ProfileAnalysis,
    target_segments: int,
) -> ProfileResamplePlan:
    """Plan a complete FULL_OPEN or FULL_CLOSED profile reconstruction."""
    if not analysis.valid or analysis.profile_type is None:
        raise ValueError(analysis.status)
    current_segments = len(analysis.ordered_chains)
    if target_segments < 3:
        raise ValueError("Target must be at least 3 profile samples")
    if target_segments == current_segments:
        raise ValueError("Target already matches current profile samples")
    external_elements, endpoint_coordinates = _validate_profile_external_geometry(
        analysis
    )
    return _build_profile_resample_plan(
        analysis,
        target_segments,
        external_elements,
        endpoint_coordinates,
    )


def _cyclic_sequence_direction(
    face_vertices: Sequence[Any],
    sequence: Sequence[Any],
) -> int:
    """Return 1/-1 when a sequence occurs contiguously in a face loop."""
    if len(sequence) > len(face_vertices):
        return 0
    count = len(face_vertices)
    for start in range(count):
        if all(
            face_vertices[(start + offset) % count] is vertex
            for offset, vertex in enumerate(sequence)
        ):
            return 1
        if all(
            face_vertices[(start + offset) % count] is vertex
            for offset, vertex in enumerate(reversed(sequence))
        ):
            return -1
    return 0


def _collect_profile_boundary_face_plans(
    analysis: ProfileAnalysis,
    changed_regions: Sequence[ProfileRegion],
) -> tuple[ProfileBoundaryFacePlan, ...]:
    """Classify solid terminal faces that require boundary substitution."""
    changed_faces = {
        face
        for region in changed_regions
        for row in region.band_faces
        for face in row
    }
    changed_interior_vertices = {
        vertex
        for region in changed_regions
        for level in region.levels
        for vertex in level[1:-1]
    }
    candidates = {
        face
        for vertex in changed_interior_vertices
        for face in vertex.link_faces
        if face not in changed_faces
    }
    profile_vertices = {
        vertex for level in analysis.levels for vertex in level
    }
    endpoint_sets = (set(analysis.levels[0]), set(analysis.levels[-1]))
    plans = []
    for face in candidates:
        attached = set(face.verts) & profile_vertices
        matching_ends = tuple(
            index for index, vertices in enumerate(endpoint_sets)
            if attached and attached <= vertices
        )
        if len(matching_ends) != 1:
            raise ValueError(
                "External geometry is attached inside a bevel region"
            )
        end_index = matching_ends[0]
        face_vertices = tuple(face.verts)
        for region in changed_regions:
            sequence = region.levels[0 if end_index == 0 else -1]
            interiors = set(sequence[1:-1])
            if not (interiors & attached):
                continue
            if not interiors <= attached or not _cyclic_sequence_direction(
                face_vertices, sequence
            ):
                raise ValueError(
                    "A solid end face does not contain a complete bevel boundary"
                )
        plans.append(
            ProfileBoundaryFacePlan(
                source_face=face,
                source_vertices=face_vertices,
                normal=face.normal.copy(),
                material_index=face.material_index,
            )
        )
    return tuple(plans)


def _validate_profile_region_geometry(
    analysis: ProfileAnalysis,
    boundary_faces: Sequence[Any],
) -> tuple[tuple[Any, ...], tuple[tuple[Vector, Vector], ...]]:
    """Validate one bevel region without applying FULL_OPEN isolation rules."""
    band_faces = {face for row in analysis.band_faces for face in row}
    region_vertices = {vertex for level in analysis.levels for vertex in level}
    boundary_vertices = set(analysis.ordered_chains[0]) | set(
        analysis.ordered_chains[-1]
    )
    replaceable_faces = set(boundary_faces)
    replaceable_edges = {
        edge for face in replaceable_faces for edge in face.edges
    }
    external = set()
    for vertex in region_vertices:
        for face in vertex.link_faces:
            if face in band_faces or face in replaceable_faces:
                continue
            if vertex not in boundary_vertices:
                raise ValueError(
                    "External geometry is attached inside a bevel region"
                )
            external.add(face)
        for edge in vertex.link_edges:
            other = edge.other_vert(vertex)
            if other in region_vertices or edge in replaceable_edges:
                continue
            if vertex not in boundary_vertices:
                raise ValueError(
                    "External geometry is attached inside a bevel region"
                )
            external.add(edge)
            external.add(other)
    endpoint_coordinates = tuple(
        (level[0].co.copy(), level[-1].co.copy())
        for level in analysis.levels
    )
    return tuple(external), endpoint_coordinates


def build_profile_regions_plan(
    analysis: ProfileAnalysis,
    target_segments: int,
) -> ProfileRegionsPlan:
    """Plan every detected bevel region before any BMesh mutation."""
    if (
        not analysis.valid
        or analysis.structure is not ProfileStructure.BEVEL_REGIONS
        or not analysis.regions
    ):
        raise ValueError("A valid bevel-regions analysis is required")
    if target_segments < 3:
        raise ValueError("Target must be at least 3 samples per region")

    changed_regions = tuple(
        region
        for region in analysis.regions
        if region.current_segments != target_segments
    )
    if not changed_regions:
        raise ValueError("All bevel regions already match Target Samples")
    boundary_face_plans = _collect_profile_boundary_face_plans(
        analysis, changed_regions
    )
    boundary_faces = tuple(
        item.source_face for item in boundary_face_plans
    )

    region_plans = []
    changed_interior_vertices = set()
    changed_faces = set()
    external_elements = set()
    for region in changed_regions:
        region_analysis = ProfileAnalysis(
            valid=True,
            status="Open bevel region is compatible",
            profile_type=ProfileType.OPEN,
            structure=ProfileStructure.BEVEL_REGIONS,
            ordered_chains=region.ordered_chains,
            levels=region.levels,
            band_faces=region.band_faces,
            regions=(),
        )
        external, endpoints = _validate_profile_region_geometry(
            region_analysis, boundary_faces
        )
        plan = _build_profile_resample_plan(
            region_analysis,
            target_segments,
            external,
            endpoints,
        )
        region_plans.append(plan)
        changed_interior_vertices.update(
            vertex for level in region.levels for vertex in level[1:-1]
        )
        changed_faces.update(face for row in region.band_faces for face in row)
        external_elements.update(plan.external_elements)
    profile_vertices = {
        vertex for level in analysis.levels for vertex in level
    }
    preserved_vertices = profile_vertices - changed_interior_vertices
    preserved_edges = set()
    preserved_faces = {
        face
        for row in analysis.band_faces
        for face in row
        if face not in changed_faces and face not in set(boundary_faces)
    }
    for face_plan in boundary_face_plans:
        preserved_vertices.update(
            vertex
            for vertex in face_plan.source_vertices
            if vertex not in changed_interior_vertices
        )
        preserved_edges.update(
            edge
            for edge in face_plan.source_face.edges
            if not set(edge.verts) & changed_interior_vertices
        )
    for element in external_elements:
        if hasattr(element, "co") and hasattr(element, "link_edges"):
            preserved_vertices.add(element)
        elif hasattr(element, "loops"):
            preserved_faces.add(element)
            preserved_vertices.update(element.verts)
            preserved_edges.update(element.edges)
        elif hasattr(element, "verts"):
            preserved_edges.add(element)
            preserved_vertices.update(element.verts)
    for vertex in preserved_vertices:
        preserved_edges.update(
            edge
            for edge in vertex.link_edges
            if edge not in {
                linked
                for interior in changed_interior_vertices
                for linked in interior.link_edges
            }
        )
    return ProfileRegionsPlan(
        analysis=analysis,
        target_segments=target_segments,
        region_plans=tuple(region_plans),
        boundary_face_plans=boundary_face_plans,
        preserved_vertices=tuple(preserved_vertices),
        preserved_vertex_coordinates=tuple(
            vertex.co.copy() for vertex in preserved_vertices
        ),
        preserved_edges=tuple(preserved_edges),
        preserved_faces=tuple(preserved_faces),
        preserved_face_materials=tuple(
            face.material_index for face in preserved_faces
        ),
    )


def _create_profile_geometry(
    edit_mesh: Any,
    plan: ProfileResamplePlan,
) -> tuple[tuple[Any, ...], ...]:
    """Create the replacement profile while retaining OPEN boundary rails."""
    level_count = len(plan.levels)
    new_levels = []
    created_vertices = []
    try:
        for level_index in range(level_count):
            level = []
            for sample_index in range(plan.target_segments):
                preserve_endpoint = (
                    plan.profile_type is ProfileType.OPEN
                    and sample_index in {0, plan.target_segments - 1}
                )
                if preserve_endpoint:
                    vertex = plan.levels[level_index][
                        0 if sample_index == 0 else -1
                    ]
                else:
                    vertex = edit_mesh.verts.new(
                        plan.positions[level_index][sample_index]
                    )
                    created_vertices.append(vertex)
                level.append(vertex)
            new_levels.append(tuple(level))

        for sample_index in range(plan.target_segments):
            preserved_rail = (
                plan.profile_type is ProfileType.OPEN
                and sample_index in {0, plan.target_segments - 1}
            )
            if preserved_rail:
                continue
            for level_index in range(level_count - 1):
                edit_mesh.edges.new(
                    (
                        new_levels[level_index][sample_index],
                        new_levels[level_index + 1][sample_index],
                    )
                )

        interval_count = (
            plan.target_segments
            if plan.profile_type is ProfileType.CLOSED
            else plan.target_segments - 1
        )
        for level_index in range(level_count):
            for interval in range(interval_count):
                following = (interval + 1) % plan.target_segments
                edit_mesh.edges.new(
                    (
                        new_levels[level_index][interval],
                        new_levels[level_index][following],
                    )
                )

        for level_index in range(level_count - 1):
            for interval in range(interval_count):
                following = (interval + 1) % plan.target_segments
                face = edit_mesh.faces.new(
                    (
                        new_levels[level_index][interval],
                        new_levels[level_index][following],
                        new_levels[level_index + 1][following],
                        new_levels[level_index + 1][interval],
                    )
                )
                face.normal_update()
                expected_normal = plan.source_face_normals[level_index][interval]
                if face.normal.dot(expected_normal) < 0.0:
                    face.normal_flip()
                source_index = plan.source_face_indices[level_index][interval]
                source_face = plan.band_faces[source_index][level_index]
                face.material_index = plan.source_face_materials[level_index][interval]
                _copy_custom_data_layers(
                    face, source_face, edit_mesh.faces.layers
                )
                for destination_loop, source_loop in zip(
                    face.loops, source_face.loops
                ):
                    _copy_custom_data_layers(
                        destination_loop, source_loop, edit_mesh.loops.layers
                    )

        if plan.profile_type is ProfileType.CLOSED:
            for end_index, end_type in enumerate(plan.end_types):
                if end_type is TubeEndType.OPEN:
                    continue
                level = new_levels[0 if end_index == 0 else -1]
                cap = edit_mesh.faces.new(level)
                cap.normal_update()
                if cap.normal.dot(plan.cap_normals[end_index]) < 0.0:
                    cap.normal_flip()
                source_cap = plan.cap_faces[end_index]
                cap.material_index = plan.cap_material_indices[end_index]
                _copy_custom_data_layers(
                    cap, source_cap, edit_mesh.faces.layers
                )
                for destination_loop, source_loop in zip(
                    cap.loops, source_cap.loops
                ):
                    _copy_custom_data_layers(
                        destination_loop, source_loop, edit_mesh.loops.layers
                    )
        return tuple(
            tuple(new_levels[level][sample] for level in range(level_count))
            for sample in range(plan.target_segments)
        )
    except Exception:
        valid_created = [vertex for vertex in created_vertices if vertex.is_valid]
        if valid_created:
            bmesh.ops.delete(edit_mesh, geom=valid_created, context="VERTS")
        raise


def validate_profile_result(
    edit_mesh: Any,
    plan: ProfileResamplePlan,
    chains: Sequence[Sequence[Any]],
    before: tuple[int, int, int],
) -> None:
    """Validate profile topology, endpoints, external geometry, and counts."""
    selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
    analysis = analyze_profile(selected_edges)
    if not analysis.valid:
        raise RuntimeError(f"PROFILE reanalysis failed: {analysis.status}")
    if analysis.profile_type is not plan.profile_type:
        raise RuntimeError("PROFILE changed open/closed topology")
    if len(analysis.ordered_chains) != plan.target_segments:
        raise RuntimeError("PROFILE produced the wrong sample count")
    if len(analysis.levels) != len(plan.levels):
        raise RuntimeError("PROFILE changed the level count")

    result_levels = build_longitudinal_levels(chains)
    result_band_faces = _collect_profile_band_faces(chains, plan.profile_type)
    new_vertices = {vertex for chain in chains for vertex in chain}
    new_edges = {edge for vertex in new_vertices for edge in vertex.link_edges}
    new_faces = {
        face for row in result_band_faces for face in row
    }
    if any(not vertex.link_edges for vertex in new_vertices):
        raise RuntimeError("PROFILE produced loose vertices")
    if any(not edge.link_faces for edge in new_edges if edge.select):
        raise RuntimeError("PROFILE produced loose longitudinal edges")
    if any(face.calc_area() <= _GEOMETRY_EPSILON for face in new_faces):
        raise RuntimeError("PROFILE produced a degenerate face")
    for level_index in range(len(analysis.levels) - 1):
        for interval, face in enumerate(
            tuple(row[level_index] for row in result_band_faces)
        ):
            if face.normal.dot(plan.source_face_normals[level_index][interval]) <= 0.0:
                raise RuntimeError("PROFILE inverted face winding")
            if face.material_index != plan.source_face_materials[level_index][interval]:
                raise RuntimeError("PROFILE changed a lateral material")

    if plan.profile_type is ProfileType.OPEN:
        for level_index, level in enumerate(result_levels):
            expected_first, expected_last = plan.endpoint_coordinates[level_index]
            actual = (level[0].co, level[-1].co)
            if not (
                actual[0] == expected_first and actual[1] == expected_last
            ):
                raise RuntimeError("PROFILE moved an open-profile endpoint")
        if any(not element.is_valid for element in plan.external_elements):
            raise RuntimeError("PROFILE damaged attached exterior geometry")
    else:
        end_infos = classify_tube_ends(result_levels)
        if tuple(info.end_type for info in end_infos) != plan.end_types:
            raise RuntimeError("PROFILE changed endpoint caps")
        for index, info in enumerate(end_infos):
            if info.cap_face is None:
                continue
            if info.cap_face.normal.dot(plan.cap_normals[index]) <= 0.0:
                raise RuntimeError("PROFILE inverted an end cap")
            if info.cap_face.material_index != plan.cap_material_indices[index]:
                raise RuntimeError("PROFILE changed an end-cap material")

    delta = plan.target_segments - plan.current_segments
    level_count = len(plan.levels)
    expected = (
        before[0] + delta * level_count,
        before[1] + delta * (2 * level_count - 1),
        before[2] + delta * (level_count - 1),
    )
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    if after != expected:
        raise RuntimeError("PROFILE produced unexpected topology counts")
    expected_selected_vertices = plan.target_segments * level_count
    expected_selected_edges = plan.target_segments * (level_count - 1)
    if sum(vertex.select for vertex in edit_mesh.verts) != expected_selected_vertices:
        raise RuntimeError("PROFILE left an invalid vertex selection")
    if sum(edge.select for edge in edit_mesh.edges) != expected_selected_edges:
        raise RuntimeError("PROFILE left an invalid edge selection")
    if any(face.select for face in edit_mesh.faces):
        raise RuntimeError("PROFILE selected faces unexpectedly")


def resample_profile(
    edit_mesh: Any,
    plan: ProfileResamplePlan,
) -> ProfileResampleResult:
    """Reconstruct one profile band from its cumulative-length plan."""
    before = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    new_chains = _create_profile_geometry(edit_mesh, plan)
    if plan.profile_type is ProfileType.CLOSED:
        old_vertices = tuple(vertex for level in plan.levels for vertex in level)
    else:
        old_vertices = tuple(
            vertex
            for level in plan.levels
            for vertex in level[1:-1]
        )
    bmesh.ops.delete(edit_mesh, geom=old_vertices, context="VERTS")
    edit_mesh.verts.ensure_lookup_table()
    edit_mesh.edges.ensure_lookup_table()
    edit_mesh.faces.ensure_lookup_table()
    select_curved_survivors(edit_mesh, new_chains)
    edit_mesh.normal_update()
    validate_profile_result(edit_mesh, plan, new_chains, before)
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    return ProfileResampleResult(
        success=True,
        message=(
            f"Resampled {plan.profile_type.value.lower()} profile: "
            f"{plan.current_segments} → {plan.target_segments} samples | "
            f"Levels: {len(plan.levels)}"
        ),
        chains=new_chains,
        vertex_count_before=before[0],
        vertex_count_after=after[0],
        edge_count_before=before[1],
        edge_count_after=after[1],
        face_count_before=before[2],
        face_count_after=after[2],
    )


def _validate_resampled_region_geometry(
    plan: ProfileResamplePlan,
    chains: Sequence[Sequence[Any]],
) -> None:
    """Validate one region without assuming it is the entire selection."""
    levels = build_longitudinal_levels(chains)
    if len(chains) != plan.target_segments or len(levels) != len(plan.levels):
        raise RuntimeError("A bevel region produced invalid topology counts")
    band_faces = _collect_profile_band_faces(chains, ProfileType.OPEN)
    for level_index in range(len(levels) - 1):
        for interval, face in enumerate(
            tuple(row[level_index] for row in band_faces)
        ):
            if face.calc_area() <= _GEOMETRY_EPSILON:
                raise RuntimeError("A bevel region produced a degenerate face")
            if face.normal.dot(plan.source_face_normals[level_index][interval]) <= 0.0:
                raise RuntimeError("A bevel region inverted face winding")
            if face.material_index != plan.source_face_materials[level_index][interval]:
                raise RuntimeError("A bevel region changed a material")
    for level_index, level in enumerate(levels):
        expected_first, expected_last = plan.endpoint_coordinates[level_index]
        if level[0].co != expected_first or level[-1].co != expected_last:
            raise RuntimeError("A bevel region moved a boundary rail")
    if any(not element.is_valid for element in plan.external_elements):
        raise RuntimeError("A bevel region damaged preserved exterior geometry")


def _replace_cyclic_face_sequence(
    face_vertices: Sequence[Any],
    old_sequence: Sequence[Any],
    new_sequence: Sequence[Any],
) -> tuple[Any, ...] | None:
    """Replace one contiguous boundary span while retaining face winding."""
    count = len(face_vertices)
    for start in range(count):
        for old, new in (
            (tuple(old_sequence), tuple(new_sequence)),
            (tuple(reversed(old_sequence)), tuple(reversed(new_sequence))),
        ):
            if all(
                face_vertices[(start + offset) % count] is vertex
                for offset, vertex in enumerate(old)
            ):
                rotated = tuple(face_vertices[start:]) + tuple(
                    face_vertices[:start]
                )
                return new + rotated[len(old):]
    return None


def _create_profile_boundary_faces(
    edit_mesh: Any,
    plan: ProfileRegionsPlan,
    new_region_chains: Sequence[Sequence[Sequence[Any]]],
) -> tuple[Any, ...]:
    """Create solid end-face replacements before deleting their originals."""
    created_faces = []
    try:
        for face_plan in plan.boundary_face_plans:
            vertices = face_plan.source_vertices
            replacement_count = 0
            for region_plan, chains in zip(
                plan.region_plans, new_region_chains
            ):
                for end_index in (0, -1):
                    old_sequence = region_plan.levels[end_index]
                    if not set(old_sequence[1:-1]) & set(
                        face_plan.source_vertices
                    ):
                        continue
                    new_sequence = tuple(
                        chain[end_index] for chain in chains
                    )
                    replaced = _replace_cyclic_face_sequence(
                        vertices, old_sequence, new_sequence
                    )
                    if replaced is None:
                        raise RuntimeError(
                            "Could not substitute a bevel in its solid end face"
                        )
                    vertices = replaced
                    replacement_count += 1
            if not replacement_count:
                raise RuntimeError("A planned solid end face had no bevel span")
            face = edit_mesh.faces.new(vertices)
            face.normal_update()
            if face.normal.dot(face_plan.normal) < 0.0:
                face.normal_flip()
            face.material_index = face_plan.material_index
            _copy_custom_data_layers(
                face, face_plan.source_face, edit_mesh.faces.layers
            )
            for destination_loop, source_loop in zip(
                face.loops, face_plan.source_face.loops
            ):
                _copy_custom_data_layers(
                    destination_loop, source_loop, edit_mesh.loops.layers
                )
            created_faces.append(face)
        return tuple(created_faces)
    except Exception:
        valid_faces = [face for face in created_faces if face.is_valid]
        if valid_faces:
            bmesh.ops.delete(
                edit_mesh, geom=valid_faces, context="FACES_ONLY"
            )
        raise


def resample_profile_regions(
    edit_mesh: Any,
    plan: ProfileRegionsPlan,
) -> ProfileRegionsResult:
    """Create all regions first, then replace every old interior atomically."""
    before = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    new_region_chains = []
    new_boundary_faces = ()
    try:
        for region_plan in plan.region_plans:
            new_region_chains.append(
                _create_profile_geometry(edit_mesh, region_plan)
            )
        new_boundary_faces = _create_profile_boundary_faces(
            edit_mesh, plan, new_region_chains
        )
    except Exception:
        created_vertices = {
            vertex
            for chains in new_region_chains
            for chain in chains[1:-1]
            for vertex in chain
            if vertex.is_valid
        }
        if created_vertices:
            bmesh.ops.delete(
                edit_mesh, geom=tuple(created_vertices), context="VERTS"
            )
        raise

    old_interior_vertices = {
        vertex
        for region_plan in plan.region_plans
        for level in region_plan.levels
        for vertex in level[1:-1]
    }
    bmesh.ops.delete(
        edit_mesh, geom=tuple(old_interior_vertices), context="VERTS"
    )
    edit_mesh.verts.ensure_lookup_table()
    edit_mesh.edges.ensure_lookup_table()
    edit_mesh.faces.ensure_lookup_table()

    final_chains = []
    seen_chains = set()
    for chain in plan.analysis.ordered_chains:
        if all(vertex.is_valid for vertex in chain):
            key = tuple(chain)
            if key not in seen_chains:
                seen_chains.add(key)
                final_chains.append(chain)
    for region_chains in new_region_chains:
        for chain in region_chains:
            key = tuple(chain)
            if key not in seen_chains:
                seen_chains.add(key)
                final_chains.append(chain)
    select_curved_survivors(edit_mesh, final_chains)
    edit_mesh.normal_update()

    for region_plan, chains in zip(plan.region_plans, new_region_chains):
        _validate_resampled_region_geometry(region_plan, chains)
    for face_plan, face in zip(
        plan.boundary_face_plans, new_boundary_faces
    ):
        if (
            not face.is_valid
            or face.normal.dot(face_plan.normal) <= 0.0
            or face.material_index != face_plan.material_index
        ):
            raise RuntimeError("PROFILE damaged a solid end face")
    for vertex, coordinate in zip(
        plan.preserved_vertices, plan.preserved_vertex_coordinates
    ):
        if not vertex.is_valid or vertex.co != coordinate:
            raise RuntimeError("PROFILE changed preserved flat geometry")
    if any(not edge.is_valid for edge in plan.preserved_edges):
        raise RuntimeError("PROFILE removed a preserved flat edge")
    for face, material in zip(
        plan.preserved_faces, plan.preserved_face_materials
    ):
        if not face.is_valid or face.material_index != material:
            raise RuntimeError("PROFILE changed a preserved flat face")

    selected_edges = tuple(edge for edge in edit_mesh.edges if edge.select)
    final_analysis = analyze_profile(selected_edges)
    if (
        not final_analysis.valid
        or final_analysis.structure is not ProfileStructure.BEVEL_REGIONS
        or len(final_analysis.regions) != len(plan.analysis.regions)
    ):
        raise RuntimeError(
            "PROFILE could not reanalyze the bevel regions: "
            f"{final_analysis.status}; structure={final_analysis.structure}; "
            f"regions={len(final_analysis.regions)}"
        )
    final_region_counts = tuple(
        region.current_segments for region in final_analysis.regions
    )
    if any(count != plan.target_segments for count in final_region_counts):
        raise RuntimeError(
            "PROFILE produced the wrong samples per region: "
            f"{final_region_counts}; flat mask="
            f"{_profile_flat_interval_mask(final_analysis.levels, final_analysis.profile_type)}"
        )

    level_count = len(plan.analysis.levels)
    total_delta = sum(
        region_plan.target_segments - region_plan.current_segments
        for region_plan in plan.region_plans
    )
    expected = (
        before[0] + total_delta * level_count,
        before[1] + total_delta * (2 * level_count - 1),
        before[2] + total_delta * (level_count - 1),
    )
    after = (len(edit_mesh.verts), len(edit_mesh.edges), len(edit_mesh.faces))
    if after != expected:
        raise RuntimeError("PROFILE regions produced unexpected topology counts")
    expected_chain_count = len(plan.analysis.ordered_chains) + total_delta
    if sum(vertex.select for vertex in edit_mesh.verts) != expected_chain_count * level_count:
        raise RuntimeError("PROFILE regions left an invalid vertex selection")
    if sum(edge.select for edge in edit_mesh.edges) != expected_chain_count * (
        level_count - 1
    ):
        raise RuntimeError("PROFILE regions left an invalid edge selection")
    if any(face.select for face in edit_mesh.faces):
        raise RuntimeError("PROFILE regions selected faces unexpectedly")
    return ProfileRegionsResult(
        success=True,
        message=(
            f"Resampled {len(plan.analysis.regions)} bevel region(s) to "
            f"{plan.target_segments} samples each | Levels: {level_count}"
        ),
        region_count=len(plan.analysis.regions),
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
