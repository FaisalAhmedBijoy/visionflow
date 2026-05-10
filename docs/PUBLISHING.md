# Publishing VisionFlow to PyPI

This guide explains how to build and publish the VisionFlow package to PyPI (Python Package Index).

## Prerequisites

- Python 3.10 or higher
- A PyPI account at [pypi.org](https://pypi.org)
- Admin access to the VisionFlow package on PyPI

## Step 1: Install Build Tools

Install the required build and upload tools:

```bash
pip install build twine
```

- `build`: Creates distribution packages (.tar.gz and .whl files)
- `twine`: Securely uploads packages to PyPI

## Step 2: Prepare the Release

### Update Version Number

Edit `pyproject.toml` and update the version:

```toml
[project]
name = "visionflow"
version = "0.2.0"  # Update this to your new version
```

Follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)

### Update CHANGELOG (Optional but Recommended)

Create or update a `CHANGELOG.md` file documenting changes in this release.

### Commit Changes

```bash
git add pyproject.toml
git commit -m "Release version 0.2.0"
git tag v0.2.0
git push origin main --tags
```

## Step 3: Build Distribution Packages

Build the source distribution and wheel:

```bash
python -m build
```

This creates:
- `dist/visionflow-0.2.0.tar.gz` (source distribution)
- `dist/visionflow-0.2.0-py3-none-any.whl` (wheel distribution)

## Step 4: Verify the Build

### Check Package Contents

```bash
# List contents of wheel
unzip -l dist/visionflow-0.2.0-py3-none-any.whl

# List contents of source distribution
tar -tzf dist/visionflow-0.2.0.tar.gz
```

### Test Installation Locally

```bash
pip install dist/visionflow-0.2.0-py3-none-any.whl
```

Verify the package works:

```bash
python -c "import visionflow; print(visionflow.__version__)"
visionflow --help
```

## Step 5: Configure PyPI Authentication

### Option A: Using API Token (Recommended)

1. Log in to [pypi.org](https://pypi.org)
2. Go to Settings → API tokens
3. Create a new token (name it something like "visionflow-publish")
4. Copy the token

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers = pypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-AgEIcHlwaS5vcmc...
```

Replace the password with your actual API token.

### Option B: Using keyring (More Secure)

```bash
pip install keyring
keyring set https://upload.pypi.org/legacy/ __token__ pypi-AgEIcHlwaS5vcmc...
```

## Step 6: Test on TestPyPI (Optional but Recommended)

Before uploading to production PyPI, test on TestPyPI:

```bash
python -m twine upload --repository testpypi dist/*
```

Then install and test:

```bash
pip install -i https://test.pypi.org/simple/ visionflow
```

## Step 7: Upload to PyPI

Upload your package to the official PyPI:

```bash
python -m twine upload dist/*
```

You'll be prompted for your username and password (use `__token__` as username and your API token as password if using tokens).

## Step 8: Verify Publication

1. Visit https://pypi.org/project/visionflow/
2. Verify the new version appears
3. Test installation from PyPI:

```bash
pip install visionflow==0.2.0
```

## Troubleshooting

### "File already exists" Error

Each version can only be uploaded once. If you need to re-upload:
1. Delete the version from PyPI (requires maintenance role)
2. Or increment the version number

### Authentication Issues

Check your credentials:
```bash
# For token-based auth
grep -A 2 "\[pypi\]" ~/.pypirc
```

### Package Validation Errors

Check the package metadata:
```bash
twine check dist/*
```

## Best Practices

1. **Always test before publishing**: Use TestPyPI or local installation
2. **Use semantic versioning**: MAJOR.MINOR.PATCH
3. **Keep dependencies updated**: Regularly audit and update dependencies
4. **Document changes**: Maintain a CHANGELOG.md file
5. **Use tags**: Tag releases in git for easy reference
6. **Automate with CI/CD**: Consider using GitHub Actions for automated publishing

## GitHub Actions Automation

Add this to `.github/workflows/publish.yml` for automated publishing:

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install build twine
    - name: Build
      run: python -m build
    - name: Publish
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
      run: twine upload dist/*
```

Then create a secret `PYPI_TOKEN` in your GitHub repository settings.

## Additional Resources

- [PyPI Help](https://pypi.org/help/)
- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
