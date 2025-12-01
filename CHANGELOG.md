# Changelog

<!-- All notable changes to this project will be documented in this file. -->

<!-- The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), -->
<!-- and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). -->

<!-- Template

## Unreleased

### Breaking changes

### Changed

### Added

### Fixed

### Removed

### Deprecated

-->

## Unreleased

### Breaking changes

- **Encoding format change**: KeyPackage (kind:443) and Welcome (kind:444) events now support version-tagged dual-format encoding for the `content` field:
  - **Version 1 (base64)**: Prefix `v1:` followed by base64-encoded content (preferred, ~33% smaller)
  - **Legacy (hex)**: No prefix, hex-encoded content (backward compatibility only)

  The version tag eliminates ambiguity for strings that are valid in both hex and base64 but decode to different bytes. Implementations MUST support reading both formats. New implementations SHOULD use base64 encoding with the `v1:` prefix.

### Changed

### Added

### Fixed

### Removed

### Deprecated
