# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
