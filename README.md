# HABD Loop Reducer

HABD Loop Reducer is a free and open-source Blender add-on for controlled segment reduction on straight cylindrical meshes.

## Status

Early Development — Version 0.1.0

## Compatibility

Blender 5.2 LTS or later.

## Current Features

- Dynamic segment detection.
- Controlled target segment count.
- Evenly distributed chain removal.
- Circular redistribution.
- Support for straight cylinders with multiple cross loops.
- Ngon cap preservation on compatible meshes.
- Undo support.
- Arbitrary even and odd segment counts.

## Installation

1. Download the project as a ZIP file.
2. Open Blender Preferences.
3. Go to **Add-ons**.
4. Choose **Install from Disk**.
5. Select the downloaded ZIP file.
6. Enable **HABD Loop Reducer**.

## Usage

1. Select a straight cylindrical mesh.
2. Enter Edit Mode.
3. Select all complete longitudinal chains.
4. Open the Sidebar with `N`.
5. Open the **HABD** tab.
6. Click **Detect Segments**.
7. Choose the **Target Segments** value.
8. Click **Reduce Loops**.

Example reductions include:

- 32 → 30
- 31 → 29
- 80 → 74

## Current Limitations

- Only straight cylindrical meshes are supported.
- Curved hoses and pipes are not yet supported correctly because redistribution currently uses a general longitudinal axis.
- Incomplete selections, branches, holes, and complex poles may be rejected.
- Perfect UV preservation is not guaranteed after redistribution.
- Always test on a copy and use Undo when necessary.

## Roadmap

- Curved tubes using local frames.
- Shape-preserving redistribution.
- Improved UV handling.
- Blender Extensions packaging.
- Additional validation and UI improvements.

## License

HABD Loop Reducer is licensed under the GNU General Public License v3.0 or later. SPDX-License-Identifier: `GPL-3.0-or-later`.

See [LICENSE](LICENSE) for the full license text.

## Author

Habdorn — [https://www.habdorn.com](https://www.habdorn.com)

## Contributing

Issues and pull requests are welcome.
