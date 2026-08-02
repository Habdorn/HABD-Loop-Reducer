# HABD Loop Reducer

HABD Loop Reducer is a free and open-source Blender add-on for controlled segment reduction on straight and curved cylindrical meshes.

## Status

Active Development — Version 0.2.0

## Compatibility

Blender 5.2 LTS or later.

## Current Features

- Dynamic detection of selected longitudinal edge chains.
- Controlled reduction to a user-defined target segment count.
- Support for arbitrary even and odd segment counts.
- Evenly distributed removal of longitudinal chains.
- Undo support.
- Straight and Curved geometry modes.
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
- Shape key safety validation.
- Rejection of incompatible topology before modification.

## Geometry Modes

### Straight

Use Straight mode for straight cylinders and tubes with one or multiple transverse loops. It supports arbitrary object rotation and displaced origins. The mode uses circular redistribution optimized around a straight axis.

### Curved

Use Curved mode for bent pipes, hoses, S-shaped tubes, tubes with multiple bends, curves across different planes, and gradual radius changes. It derives geometric ring planes and continuous local frames from the mesh, preserving the per-level centers and average radii during redistribution.

## Installation

1. Download `habd_loop_reducer-v0.2.0.zip`.
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
7. Run **Detect Segments** for Straight or **Analyze Curved Tube** for Curved.
8. Set **Target Segments**.
9. Run **Reduce Loops**.
10. Inspect the result and use Undo if necessary.

Always test destructive topology operations on a copy of important production meshes.

Example reductions include:

- Straight cylinder: 32 → 30
- Straight cylinder: 31 → 29
- Curved tube: 20 → 18
- S-shaped tube: 32 → 28
- Variable-radius curved tube: 32 → 26

## Supported Topology

- Complete longitudinal edge chains.
- Equivalent chain topology.
- Predominantly quad-based tube sides.
- At least three longitudinal chains.
- At least two transverse levels.
- Open ends.
- One compatible ngon cap per closed end.
- Circular or approximately circular transverse sections.

## Current Limitations

- Triangulated caps are not currently supported.
- End caps with center poles are not currently supported.
- Complex cap topology, holes, and multiple filling faces are rejected.
- Branched tubes and intersections are not supported.
- Partial longitudinal selections are rejected.
- Cross sections must remain approximately circular.
- Strongly oval or non-planar sections may be rejected.
- Perfect UV redistribution is not guaranteed.
- UV layers are preserved, but moved vertices may change texture distortion.
- Shape keys prevent destructive reduction for safety.
- After Undo, rerun **Detect Segments** or **Analyze Curved Tube** to refresh panel results when necessary.

## Roadmap

- Improved UV redistribution.
- Shape-preserving support for oval sections.
- Support for additional cap topologies.
- Better viewport feedback and previews.
- Blender Extensions packaging.
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
