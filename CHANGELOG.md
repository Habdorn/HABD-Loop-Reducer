# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-09-06

### Added

- Longitudinal Increase and Reduce for regular quad bands using Rails or Cross Loops input.
- Separate OPEN_PATH / CLOSED_PATH detection and OPEN / CLOSED transverse-section topology.
- Preserve and Smooth path shaping, including periodic centripetal Catmull–Rom sampling for closed paths.
- Physical base preservation for open paths and physical anchor preservation for closed paths.
- Periodic arc-length and full last → anchor handling in geometry, winding, materials, UVs, and compatible custom data.
- Independent closing-twist and oriented quaternion seam validation for Smooth CLOSED_PATH, with a 5° discrepancy tolerance and conservative near-180° rejection.

### Improved

- Transactional longitudinal staging and validation before a single final source deletion, with rollback of staged geometry, selection, selection history, selection mode, and normals on pre-commit failure.
- Stable anchor, direction, phase, and transverse ordering across accepted consecutive closed-path resamplings, guarded using current and projected post-delete vertex indices.
- Conservative rejection of ambiguous Rails / Cross Loops interpretations, dual-axis tori, chords, external attachments, Möbius topology, and non-trivial monodromy or permutations.

### Fixed

- Straight Increase false spacing-validation failures by checking generated coordinates against frozen planner targets before destructive mutation.

### Known limitations

- Closed-path resampling may reject otherwise regular geometry when seam continuity or canonical stability cannot be preserved conservatively.
- No automatic twist distribution, new parallel transport, or seam correction is introduced.
- UV/custom-data transfer retains the existing copy-based contract; exact UV redistribution is not guaranteed.
- A partial failure inside Blender's final native deletion cannot restore original BMesh element identity; all Python-side longitudinal validation precedes that boundary.

## [0.3.0] - 2026-08-08

### Added

- Bidirectional segment resampling with the target interpreted as the final count.
- Increased radial segment counts for Straight and Curved geometry.
- Profile geometry mode with accumulated-length, shape-preserving resampling.
- Open and closed full-profile resampling.
- Automatic bevel-region detection within compatible solid geometry.
- Single- and multi-region bevel resampling, including regions with different current sample counts.
- Preservation of compatible flat areas, profile boundary rails, exterior geometry, materials, custom data, and ngon caps.

### Improved

- Curved and S-curve resampling for both lower and higher target counts.
- Target semantics and no-op handling when Target matches Current.
- Interface wording and feedback, including **Apply Segments** and signed **Change** values.
- Pre-mutation planning, topology validation, post-operation reanalysis, and geometry checks.

### Fixed

- Fixed `External geometry is attached inside the open profile` for valid integrated bevel regions on solids.
- Prevented FULL_OPEN external-geometry validation from being reused for BEVEL_REGIONS.
- Fixed a single integrated bevel not being classified as `Regions = 1`.

## [0.2.0] - 2026-08-02

### Added

- Added official Blender Extension packaging support.
- Straight and Curved geometry modes.
- Non-destructive curved tube analysis.
- Destructive segment reduction for curved tubes and hoses.
- Per-level geometric ring planes.
- Continuous local frames for curved paths.
- Support for multiple bends and S-shaped tubes.
- Support for curves across different planes.
- Preservation of the original centerline.
- Preservation of the average radius of each transverse level.
- Support for gradual radius variation.
- Support for open ends and compatible ngon caps.
- Support for mixed open and capped tube ends.
- Validation of frame continuity, circularity and planarity.
- Safe rejection of incompatible end-cap topology.

### Changed

- The Reduce Loops operator now dispatches between Straight and Curved algorithms.
- Curved redistribution now uses the real geometric plane of every ring.
- Error messages now identify invalid levels and unsupported cap topology more clearly.
- The panel now displays curved path, radius, turn-angle and frame-continuity information.

### Fixed

- Fixed deformation caused by using a single global axis on curved tubes.
- Fixed false axial-offset errors near S-curve inflection points.
- Fixed local frame instability across multiple bends.
- Fixed preservation of open and ngon-capped tube ends.
- Prevented accidental changes to the tube centerline during curved redistribution.
- Prevented unexpected twists, frame flips and crossed side faces.

### Known limitations

- Triangulated caps and center-pole caps are not supported.
- Branched or intersecting tubes are not supported.
- Strongly oval or non-planar cross sections may be rejected.
- Perfect UV redistribution is not guaranteed.
- Shape keys block destructive reduction for safety.

## [0.1.0] - 2026-08-01

### Added

- Initial public release.
- Dynamic detection of longitudinal edge chains.
- Controlled target segment reduction.
- Evenly distributed chain removal.
- Circular redistribution for straight cylindrical meshes.
- Support for multiple transverse levels.
- Support for even and odd segment counts.
- Preservation of compatible ngon caps.
- Undo support.
- Blender 5.2 LTS compatibility.

### Known limitations

- Curved tubes and hoses are not yet supported correctly.
- Perfect UV preservation is not guaranteed.
- Complex topology, holes, branches and partial selections may be rejected.
