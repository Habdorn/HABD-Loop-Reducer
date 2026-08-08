# HABD Loop Reducer

HABD Loop Reducer is a free and open-source Blender add-on for controlled segment resampling on straight and curved tubes and profile-based surfaces.

## Status

Active Development — Version 0.3.0

## Compatibility

Blender 5.2 LTS or later.

## Current Features

- Dynamic detection of selected longitudinal edge chains.
- Bidirectional resampling to a user-defined final target count.
- Reduction, increase, and no-op handling when Target equals Current.
- Support for arbitrary even and odd segment counts.
- Undo support.
- Straight, Curved, and Profile geometry modes.
- Circular redistribution for straight cylindrical meshes.
- Local ring frames for curved tubes and hoses.
- Support for multiple bends and S-shaped paths.
- Support for curves in different planes.
- Preservation of the original centerline within numerical tolerance.
- Preservation of the average radius of every transverse level.
- Support for gradual radius variation.
- Support for multiple transverse loops.
- Support for open tube ends.
- Preservation of compatible ngon caps.
- Support for mixed ends: OPEN / OPEN, OPEN / NGON_CAP, NGON_CAP / OPEN, and NGON_CAP / NGON_CAP.
- Accumulated-length resampling for open and closed profiles.
- Automatic detection and resampling of compatible bevel regions integrated into solids.
- Support for multiple bevel regions with different current sample counts.
- Preservation of compatible flat areas and bevel boundary rails.
- Shape key safety validation.
- Pre-mutation planning and rejection of incompatible topology.

## Target Behavior

**Target** is the final number of radial segments or profile samples. HABD Loop Reducer can reduce when Target is lower than Current, increase when it is higher, and leave the mesh unchanged when both values match.

## Geometry Modes

### Straight

Use Straight mode for straight cylinders and tubes with one or multiple transverse loops. It supports arbitrary object rotation and displaced origins. The mode uses circular redistribution optimized around a straight axis.

### Curved

Use Curved mode for bent pipes, hoses, S-shaped tubes, tubes with multiple bends, curves across different planes, and gradual radius changes. It derives geometric ring planes and continuous local frames from the mesh, preserving the per-level centers and average radii during redistribution.

### Profile

Use Profile mode for a regular quad band whose transverse section is an open or closed profile rather than a circular tube. Samples are placed by accumulated length along each profile level to preserve its overall shape.

Profile supports:

- **FULL_OPEN** profiles with preserved boundary rails.
- **FULL_CLOSED** profiles, including compatible open or ngon-capped longitudinal ends.
- **BEVEL_REGIONS** detected between preserved flat sections, including one or multiple regions and different current sample counts per region.

For integrated bevels, the operation plans every detected region before mutation and preserves compatible flats, boundaries, exterior geometry, materials, and custom data. Ambiguous attachments and unsupported solid boundaries are rejected rather than treated as universally safe.

## Installation

1. Download `habd_loop_reducer-0.3.0.zip`.
2. Open Blender Preferences.
3. Go to **Add-ons**.
4. Choose **Install from Disk**.
5. Select the ZIP.
6. Enable **HABD Loop Reducer**.
7. Open the **HABD** tab in the 3D Viewport Sidebar.

## Usage

1. Select a compatible cylindrical mesh.
2. Enter Edit Mode.
3. Select all complete longitudinal edge chains.
4. Open the 3D Viewport Sidebar with `N`.
5. Open the **HABD** tab.
6. Choose **Geometry Mode**:
   - **Straight**
   - **Curved**
   - **Profile**
7. Run **Detect Segments**, **Analyze Curved Tube**, or **Analyze Profile** for the selected mode.
8. Set the final **Target Segments** or **Target Samples**.
9. Run **Apply Segments**.
10. Inspect the result and use Undo if necessary.

Always test destructive topology operations on a copy of important production meshes.

## Blender Extensions

The repository supports official Blender Extension packaging through `blender_manifest.toml` and declares Blender 5.2.0 as its minimum compatible version.

Example resampling operations include:

- Straight cylinder: 32 → 30
- Straight cylinder: 31 → 29
- Curved tube: 20 → 18
- S-shaped tube: 32 → 28
- Variable-radius curved tube: 32 → 26
- Straight or curved tube increase: 16 → 24
- Open, closed, or bevel-region profile resampling to a final target sample count

## Supported Topology

- Complete longitudinal edge chains.
- Equivalent chain topology.
- Predominantly quad-based tube sides.
- At least three longitudinal chains.
- At least two transverse levels.
- Open ends.
- One compatible ngon cap per closed end.
- Circular or approximately circular transverse sections in Straight and Curved modes.
- Regular quad profile bands in Profile mode.
- Monotonic bevel spans bounded by compatible preserved flat sections.

## Current Limitations

- Triangulated caps and end caps with center poles are not currently supported.
- Complex caps, holes, and multiple filling faces may be rejected.
- Branched tubes and intersections are not supported.
- Partial longitudinal selections are rejected.
- Straight and Curved cross sections must remain approximately circular; strongly oval or non-planar sections may be rejected.
- Profile requires equivalent open longitudinal chains forming one regular quad band with at least three samples.
- Bevel Regions must be monotonic spans that can be separated from preserved flats; abrupt corners, direction reversals, ambiguous attachments, and incompatible solid boundaries may be rejected.
- Exact UV preservation is not guaranteed. Compatible custom data is copied where topology permits, but resampling may change texture distortion.
- Shape keys prevent destructive resampling for safety.
- After Undo, rerun the analysis action for the selected geometry mode to refresh panel results when necessary.

## Roadmap

- Improved UV redistribution.
- Support for additional cap topologies.
- Better viewport feedback and previews.
- Automated test suite and continuous integration.
- Additional topology validation.
- Optional preview of chains selected for removal.

## License

HABD Loop Reducer is licensed under the GNU General Public License v3.0 or later. SPDX-License-Identifier: `GPL-3.0-or-later`.

See [LICENSE](LICENSE) for the full license text.

## Author

Habdorn — [https://www.habdorn.com](https://www.habdorn.com)

## Contributing

Issues and pull requests are welcome.
