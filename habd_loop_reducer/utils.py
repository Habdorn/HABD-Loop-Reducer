"""Small shared helpers for HABD Loop Reducer."""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from mathutils import Vector


_GEOMETRY_EPSILON = 1.0e-8


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
