# Release Process for Hoppy Whisper

## Pre-Release Checklist

- [ ] Update `pyproject.toml` version
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run `poetry run pytest` locally - all tests pass
- [ ] Run `poetry run ruff check --fix` and `poetry run ruff format` - no linting errors
- [ ] Run `poetry run mypy src/app` - no type errors
- [ ] Test the app locally with the default build
- [ ] Test GPU/DirectML variant if changes affect ONNX Runtime

## Creating a Release

### Option 1: Manual via Git (Recommended)

```powershell
# Ensure all changes are committed
git status

# Create an annotated tag (triggers CI/CD)
git tag -a v1.0.0 -m "Release version 1.0.0"

# Push the tag to GitHub (triggers release workflow)
git push origin v1.0.0

# Monitor the workflow at https://github.com/lsj5031/parakeet/actions
```

### Option 2: GitHub Web UI

1. Go to **Releases** tab on GitHub
2. Click **Draft a new release**
3. Choose tag: enter `vX.Y.Z` (e.g., `v1.0.0`)
4. Click **Create new tag on publish**
5. Add release title and description
6. Click **Publish release** - this triggers the workflow

## What Happens Automatically

When a tag matching `v*` is pushed, the `release.yml` workflow:

1. ✅ Checks out code
2. ✅ Runs full test suite
3. ✅ Builds CPU variant (PyInstaller)
4. ✅ Builds GPU/DirectML variant
5. ✅ Generates SHA256 checksums
6. ✅ Creates GitHub Release with:
   - Both executables attached
   - Checksums file
   - Auto-generated release notes
   - Custom installation instructions

## Version Naming Convention

Use **semantic versioning**: `vMAJOR.MINOR.PATCH`

Examples:
- `v0.1.0` - Initial release
- `v0.2.0` - New features
- `v0.2.1` - Bug fixes
- `v1.0.0` - First stable release

## Release Notes Template

```markdown
## Release v0.2.0

### New Features
- Feature A
- Feature B

### Bug Fixes
- Fixed issue #123
- Fixed issue #456

### Known Issues
- Known issue A (workaround: ...)

### Downloads
- **Hoppy Whisper-CPU.exe** - For standard CPUs
- **Hoppy Whisper-GPU.exe** - For GPUs with DirectML

### Installation
1. Download the appropriate exe
2. Run installer
3. Launch from Windows Start menu

### Verification
```powershell
(Get-FileHash -Path 'Hoppy Whisper-CPU.exe' -Algorithm SHA256).Hash
```
Compare with SHA256SUMS.txt
```

## Troubleshooting CI/CD Failures

### Build fails on PyInstaller step
- Check `HoppyWhisper_onefile.spec` and `HoppyWhisper_DML_onefile.spec` exist
- Verify Poetry lock file is up-to-date: `poetry lock --refresh`
- Check hidden imports in spec files for missing dependencies

### Tests fail
- Run locally: `poetry run pytest -v`
- Check for platform-specific issues (tests may differ on Windows vs CI)

### Model prefetch fails
- Hugging Face hub may be rate-limited
- Retry the workflow run from GitHub Actions UI
- Check internet connectivity in workflow logs

### Release not created
- Verify tag format: `v` + semver (e.g., `v1.0.0`)
- Check for typos: `git tag -l` lists all tags
- Ensure `GITHUB_TOKEN` has `contents: write` permission (auto-granted)

## Rollback

If a release has issues:

1. Delete the GitHub Release (don't delete the tag)
2. Fix the issue locally
3. Amend the tag: `git tag -d v1.0.0 && git tag -a v1.0.0 -m "..."`
4. Force push: `git push origin v1.0.0 --force-with-lease`
5. Re-run the workflow from GitHub Actions

Or create a new patch version:
```powershell
git tag -a v1.0.1 -m "Hotfix for v1.0.0"
git push origin v1.0.1
```

## After Release

1. ✅ Verify downloads work on GitHub Releases page
2. ✅ Test the downloaded executable
3. ✅ Announce in project README or discussions
4. ✅ Update version in `pyproject.toml` to next dev version (e.g., `0.2.1-dev`)
5. ✅ Commit: `git commit -am "Bump version to 0.2.1-dev"`
6. ✅ Push to main: `git push origin main`

## Continuous Integration Workflows

### `release.yml` (Tag-triggered)
- Runs on: `push` with tag `v*`
- Builds both CPU and GPU variants
- Creates GitHub Release with artifacts

### `build-preview.yml` (Branch-triggered)
- Runs on: push to `main`, PRs, manual trigger
- Builds CPU variant only (faster)
- Uploads to artifacts (7-day retention)
- Comments on PRs with download link

### `droid-exec.yml` (Issue-triggered)
- Runs on: `/droid` comment on issues/PRs
- Executes AI-assisted code generation
- Creates PR with changes

## Monitoring

- Check workflow status: https://github.com/lsj5031/parakeet/actions
- Set up release notifications (GitHub Star > Watch > Releases)
- Consider GitHub Discussions for community feedback
