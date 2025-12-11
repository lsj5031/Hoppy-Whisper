# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-11

### Changed
- **Remote-first architecture**: `remote_transcription_enabled` now defaults to `true`
- CI/CD now builds with `HoppyWhisper_Remote.spec` for minimal ~20MB executable (no ONNX Runtime bundled)
- Removed model prefetch step from release workflow (no longer needed for remote-only build)
- Updated documentation to highlight remote-first design as primary use case
- Release notes updated to reflect remote-optimized distribution

### Added
- Build variant documentation for local ONNX processing fallback

### Notes
- Users can still opt into local ONNX transcription by using `HoppyWhisper_onefile.spec` or `HoppyWhisper_DML_onefile.spec`
- Remote transcription endpoint must be configured in `settings.json` before first use

## [0.1.0] - Unreleased

### Added
- Project scaffolding with Poetry configuration and modular `src/app` package layout.
- Windows CI + release automation to build single-file PyInstaller executable.
- Comprehensive PyInstaller spec file (`HoppyWhisper.spec`) with ONNX Runtime DirectML bundling.
- Smoke test checklist (`SMOKE_TEST.md`) for validating releases on clean Windows VMs.
- Release packaging workflow with automatic GitHub Release creation on version tags.
- End-user installation instructions and system requirements in README.
- Keyboard shortcuts reference and known limitations documentation.

### Changed
- Updated CI to use `HoppyWhisper.spec` instead of command-line PyInstaller invocation.
- Enhanced README with download instructions, release process, and comprehensive troubleshooting guide.

