# Contributing to VisionFlow

We welcome contributions! This document provides guidelines for contributing to VisionFlow.

## Getting Started

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/visionflow.git
cd visionflow
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode**
```bash
pip install -e ".[dev]"
```

4. **Install pre-commit hooks (optional)**
```bash
pre-commit install
```

## Development Workflow

### Code Style

- **Format**: Use `black` for code formatting
```bash
black visionflow/ tests/
```

- **Imports**: Use `isort` to sort imports
```bash
isort visionflow/ tests/
```

- **Linting**: Use `flake8` to check for issues
```bash
flake8 visionflow/ tests/
```

- **Type Checking**: Use `mypy` for static type analysis
```bash
mypy visionflow/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=visionflow tests/

# Run specific test file
pytest tests/test_events.py

# Run specific test
pytest tests/test_events.py::TestEvent::test_event_creation
```

### Making Changes

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Write clear, documented code
   - Add or update tests for new functionality
   - Update documentation as needed

3. **Check code quality**
```bash
black visionflow/ tests/
isort visionflow/ tests/
flake8 visionflow/ tests/
mypy visionflow/
pytest
```

4. **Commit with clear messages**
```bash
git commit -m "feat: add support for custom event generators"
```

5. **Push to your fork and create a PR**

## Code Guidelines

### Type Hints

Always use type hints for function arguments and return types:

```python
def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
    """Process frame and return results."""
    pass
```

### Documentation

- Add docstrings to all classes and public methods (Google style):

```python
def start(self) -> None:
    """
    Start the pipeline.
    
    Raises:
        RuntimeError: If pipeline is already running
    """
    pass
```

- Add examples in class docstrings for complex classes
- Update README.md and docs/ for user-facing changes

### Testing

- Write tests for all new functionality
- Aim for >80% code coverage
- Use pytest fixtures for common setup
- Use pytest.mark.asyncio for async tests

Example:
```python
@pytest.mark.asyncio
async def test_event_emission() -> None:
    """Test that events are properly emitted."""
    engine = EventEngine()
    received = []
    
    async def handler(event: Event) -> None:
        received.append(event)
    
    engine.on("test", handler)
    await engine.emit(Event(event_type="test", ...))
    
    assert len(received) == 1
```

### Async Design

- Use `async`/`await` for I/O operations
- Use `asyncio.gather()` for concurrent operations
- Handle `asyncio.CancelledError` for graceful shutdown

## Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test updates
- `chore`: Maintenance

Example:
```
feat: add Kafka output handler

- Implement KafkaOutput class for publishing events to Kafka topics
- Support configurable brokers and topic names
- Add tests for Kafka integration

Closes #42
```

## Adding New Features

### New Source Implementation

1. Create file: `visionflow/ingestion/my_source.py`
2. Inherit from `BaseSource`
3. Implement `connect()`, `disconnect()`, `read_frame()`
4. Add to `visionflow/ingestion/__init__.py`
5. Add tests in `tests/test_ingestion.py`
6. Update documentation

### New Worker Implementation

1. Create file: `visionflow/processing/my_worker.py`
2. Inherit from `BaseWorker`
3. Implement `initialize()`, `cleanup()`, `process_frame()`
4. Add to `visionflow/processing/__init__.py`
5. Add tests
6. Update documentation

### New Output Implementation

1. Create file: `visionflow/outputs/my_output.py`
2. Inherit from `BaseOutput`
3. Implement `start()`, `stop()`, `send_event()`
4. Add to `visionflow/outputs/__init__.py`
5. Add tests
6. Update documentation

## Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update docs/ with any new documentation
3. Ensure all tests pass: `pytest --cov=visionflow tests/`
4. Ensure code style: `black`, `isort`, `flake8`, `mypy`
5. Request review from maintainers

## Reporting Issues

When reporting issues, include:
- Python version
- VisionFlow version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error traceback if applicable

## Questions?

Feel free to open a discussion or issue on GitHub!

## License

By contributing to VisionFlow, you agree that your contributions will be licensed under its Apache 2.0 License.
