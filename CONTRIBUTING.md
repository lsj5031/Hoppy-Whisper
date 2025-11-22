# Contributing to Hoppy Whisper

Thank you for your interest in contributing to Hoppy Whisper! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- **Python 3.11 (64-bit)** - Required for development
- **Poetry** - Dependency management
- **Git** - Version control
- **Windows 10/11** - Required for testing (the app is Windows-specific)

### Development Setup

1. **Fork the repository** on GitHub

2. **Clone your fork:**
   ```powershell
   git clone https://github.com/YOUR_USERNAME/hoppy-whisper.git
   cd hoppy-whisper
   ```

3. **Install dependencies:**
   ```powershell
   py -3.11 -m poetry install --with dev
   ```

4. **Install pre-commit hooks:**
   ```powershell
   poetry run pre-commit install
   ```

5. **Verify the setup:**
   ```powershell
   poetry run pytest
   poetry run ruff check src/ tests/
   poetry run mypy src/app
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards (see below)

3. **Run tests:**
   ```powershell
   poetry run pytest
   ```

4. **Lint and format:**
   ```powershell
   poetry run ruff check src/ tests/ --fix
   poetry run ruff format src/ tests/
   ```

5. **Type check:**
   ```powershell
   poetry run mypy src/app
   ```

6. **Commit your changes:**
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```
   
   Pre-commit hooks will automatically run linting and formatting.

7. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Open a Pull Request** on GitHub

### Coding Standards

- **Language:** Python 3.11+ with type hints
- **Style:** Follow PEP 8; Ruff enforces formatting (88-char lines, double quotes)
- **Imports:** Use Ruff isort (stdlib, third-party, first-party)
- **Type hints:** Required on all function signatures
- **Docstrings:** Required for modules and public methods
- **Error handling:** Use custom exceptions with context; log before raising
- **Threading:** Use `threading.Event` and `Timer`; keep callbacks minimal
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes

See [AGENTS.md](AGENTS.md) for detailed coding guidelines.

### Testing

- Write tests for new features and bug fixes
- Place tests in the `tests/` directory
- Follow existing test patterns (use pytest fixtures from `conftest.py`)
- Aim for meaningful test coverage, not just high percentages
- Test on a clean Windows environment when possible

**Run specific tests:**
```powershell
poetry run pytest tests/test_module.py::test_function -xvs
```

### Building Locally

To build the PyInstaller executable:

```powershell
poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
```

The output will be in `dist/Hoppy Whisper.exe`. See [BUILD.md](BUILD.md) for details.

## Pull Request Process

1. **Update documentation** if your changes affect user-facing behavior
2. **Update CHANGELOG.md** under the `[Unreleased]` section
3. **Ensure all tests pass** and pre-commit hooks succeed
4. **Provide a clear PR description:**
   - What problem does this solve?
   - How did you test it?
   - Are there breaking changes?
5. **Link related issues** using keywords (e.g., "Fixes #123")
6. **Be responsive to review feedback**
7. **Squash commits** if requested before merge

### PR Checklist

Before submitting, verify:

- [ ] Code follows style guidelines (Ruff passes)
- [ ] Type hints are complete (mypy passes)
- [ ] Tests pass (`pytest`)
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] CHANGELOG.md updated
- [ ] Pre-commit hooks pass
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts with `main`

## Types of Contributions

### Bug Reports

Found a bug? Please open an issue with:

- **Clear title** describing the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment details:** Windows version, Python version (if relevant)
- **Logs or screenshots** if applicable

Use the bug report issue template.

### Feature Requests

Have an idea? Open an issue with:

- **Clear description** of the feature
- **Use case:** Why is this valuable?
- **Proposed implementation** (optional)
- **Alternatives considered** (optional)

Use the feature request issue template.

### Code Contributions

We welcome:

- Bug fixes
- Performance improvements
- Documentation improvements
- Test coverage improvements
- New features (discuss in an issue first for large changes)

### Documentation

Help improve:

- README clarity and accuracy
- Code comments and docstrings
- BUILD.md, SMOKE_TEST.md, and other guides
- Error messages and user-facing text

## Project Structure

```
hoppy-whisper/
├── src/app/               # Main application package
│   ├── __main__.py        # Entry point and AppRuntime
│   ├── audio/             # Audio capture and VAD
│   ├── hotkey/            # Global hotkey handling
│   ├── transcriber/       # ONNX speech recognition
│   ├── tray/              # System tray integration
│   ├── history/           # SQLite persistence
│   ├── cleanup/           # Text post-processing
│   ├── settings.py        # Configuration
│   └── metrics.py         # Optional telemetry
├── tests/                 # Pytest test suite
├── .github/workflows/     # CI/CD pipelines
├── HoppyWhisper.spec      # PyInstaller build config
└── pyproject.toml         # Poetry dependencies
```

See [CODEBASE_ANALYSIS.md](CODEBASE_ANALYSIS.md) for architectural details.

## Release Process

Releases are managed by maintainers:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` (move `[Unreleased]` to `[vX.Y.Z]`)
3. Commit: `git commit -m "Bump version to vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push origin main --tags`
6. GitHub Actions builds and creates the release automatically

See [RELEASE.md](RELEASE.md) for details.

## Questions?

- **General questions:** Open a discussion on GitHub
- **Bug reports:** Use the issue tracker
- **Security issues:** See [SECURITY.md](SECURITY.md)

## Recognition

Contributors are recognized in:

- GitHub's contributor graph
- Release notes for significant contributions
- CHANGELOG.md for bug fixes and features

Thank you for helping make Hoppy Whisper better!
