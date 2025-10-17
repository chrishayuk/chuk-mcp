# Release Process

This document outlines the process for releasing new versions of chuk-mcp.

## Pre-Release Checklist

- [ ] All tests pass (`make test` or `uv run pytest`)
- [ ] Type checking passes (`make typecheck` or `uv run mypy src`)
- [ ] Linting passes (`make lint` or `uv run ruff check .`)
- [ ] Coverage is ≥85% (`uv run pytest --cov`)
- [ ] All examples work (`make examples`)
- [ ] Documentation is up to date
- [ ] CHANGELOG.md is updated with changes
- [ ] Version bumped in `pyproject.toml`

## Release Steps

### 1. Update Version

Edit `pyproject.toml`:

```toml
[project]
name = "chuk-mcp"
version = "X.Y.Z"  # Update this
```

### 2. Update CHANGELOG.md

Add a new section for the release:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features...

### Changed
- Breaking changes...

### Fixed
- Bug fixes...
```

### 3. Commit Changes

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Release vX.Y.Z"
git push origin main
```

### 4. Create Git Tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

### 5. Build Distribution

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build with uv
uv build

# Verify build
ls -lh dist/
```

### 6. Upload to PyPI

```bash
# Test upload (optional)
twine upload --repository testpypi dist/*

# Production upload
twine upload dist/*
```

### 7. Create GitHub Release

1. Go to https://github.com/chrishayuk/chuk-mcp/releases/new
2. Select the tag `vX.Y.Z`
3. Title: `Release vX.Y.Z`
4. Copy CHANGELOG.md content for this version
5. Attach distribution files from `dist/`
6. Publish release

### 8. Verify Installation

```bash
# Install from PyPI
uv pip install --upgrade chuk-mcp

# Verify version
python -c "import chuk_mcp; print(chuk_mcp.__version__)"
```

## Post-Release

- [ ] Announce on relevant channels
- [ ] Update documentation site (if applicable)
- [ ] Close milestone on GitHub
- [ ] Update project board

## Version Numbering

chuk-mcp follows [Semantic Versioning](https://semver.org/):

- **Major (X.0.0)**: Breaking changes to public APIs
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, backward compatible

## Emergency Hotfix Process

For critical bugs requiring immediate release:

1. Create hotfix branch from tag: `git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z`
2. Fix bug and add tests
3. Update version to X.Y.Z+1
4. Follow steps 2-8 above
5. Merge hotfix back to main: `git checkout main && git merge hotfix/vX.Y.Z+1`

## Rollback Procedure

If a release has critical issues:

1. Yank the release from PyPI: `twine upload --repository pypi --skip-existing dist/old-version/*`
2. Mark GitHub release as pre-release
3. Announce the issue and rollback
4. Prepare hotfix as described above
