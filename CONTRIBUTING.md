# Contributing to Hoppy Whisper

Thank you for your interest in contributing to Hoppy Whisper! We welcome all contributions, whether it's bug reports, feature requests, or code improvements.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Hoppy-Whisper.git
   cd Hoppy-Whisper
   ```
3. **Install dependencies** with Poetry:
   ```powershell
   py -3.11 -m poetry install --with dev
   ```

## Development Workflow

### Running Tests
```powershell
poetry run pytest
```

### Linting & Formatting
```powershell
# Check for linting issues
poetry run ruff check src/ tests/

# Auto-fix issues
poetry run ruff check src/ tests/ --fix

# Format code
poetry run ruff format src/ tests/
```

### Type Checking
```powershell
poetry run mypy src/app
```

### Building Locally
```powershell
poetry run pyinstaller --noconfirm --clean HoppyWhisper_onefile.spec
```

The executable will be at `dist/Hoppy Whisper-CPU.exe`

## Code Style

- **Language**: Python 3.11+ with type hints
- **Formatting**: Ruff (88-char line length, double quotes)
- **Imports**: Sorted with isort
- **Types**: Full type annotations on function signatures
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings**: Required for modules and public methods

## Before Submitting a PR

1. **Write tests** for new functionality
2. **Run all checks**:
   ```powershell
   poetry run ruff check src/ tests/ --fix
   poetry run ruff format src/ tests/
   poetry run mypy src/app
   poetry run pytest
   ```
3. **Update documentation** if behavior changes
4. **Keep commits clean** - one feature per commit with clear messages

## Reporting Bugs

Create an issue with:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Windows version and system specs
- Error logs (if applicable)

## Feature Requests

Include:
- Use case and motivation
- Proposed solution (if any)
- Alternatives considered

## Questions?

Open an issue or start a discussion. We're here to help!

## License

By contributing, you agree your work will be licensed under the MIT License.
