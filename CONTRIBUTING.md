# Contributing to WhiteMagic

Thank you for your interest in contributing to WhiteMagic! This document provides guidelines and instructions for contributing.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Project Structure](#project-structure)

---

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and professional in all interactions.

---

## Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Git**: For version control
- **PostgreSQL**: Optional for local API development (SQLite works too)
- **Redis**: Optional for rate limiting tests
- **Node.js**: 18+ for MCP server development

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/whitemagic.git
   cd whitemagic
   ```

3. Add upstream remote:

   ```bash
   git remote add upstream https://github.com/lbailey94/whitemagic.git
   ```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install -e .

# API dependencies
pip install -r requirements-api.txt

# Development tools
pip install black ruff mypy pytest pytest-asyncio pytest-cov pre-commit
```

### 3. Set Up Pre-Commit Hooks

```bash
pre-commit install
```

This will automatically run code quality checks before each commit.

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your local settings
```

### 5. Set Up Database (for API development)

```bash
# Run migrations
alembic upgrade head
```

---

## Making Changes

### 1. Create a Branch

Always create a new branch for your changes:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch naming conventions**:

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Write clear, concise code
- Follow the existing code style
- Add comments for complex logic
- **Update documentation as needed**
  - Run `whitemagic audit` (v2.2.8) to confirm version/doc consistency
  - Run `whitemagic docs-check docs/ README.md` to flag stale sections

### 3. Write Tests

- Add tests for new functionality
- Ensure all tests pass locally
- Aim for high test coverage

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=whitemagic --cov-report=term

# Upcoming automation (v2.2.8)
whitemagic exec plan plan.yaml  # Stage batched commands for approval
```

### 4. Update Documentation

- Update relevant `.md` files
- Add docstrings to new functions/classes
- Update `CHANGELOG.md` if applicable

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_memory_manager.py

# With verbose output
pytest tests/ -v

# With coverage report
pytest tests/ --cov=whitemagic --cov-report=html
```

### Test Structure

- **Unit tests**: `tests/test_*.py`
- **Integration tests**: `tests/test_api_*.py`
- **MCP tests**: `tests/test_mcp_*.py`

### Writing Tests

```python
import pytest
from whitemagic import MemoryManager


def test_create_memory():
    """Test memory creation."""
    manager = MemoryManager()
    result = manager.create_memory("Test", "Content", "short_term")
    assert result.exists()


@pytest.mark.asyncio
async def test_api_endpoint():
    """Test API endpoint."""
    # API test example
    pass
```

### Important: Rate Limiter Test Fixture

**`tests/conftest.py` contains an autouse fixture that mocks the rate limiter** for all tests. This prevents "Rate limiter not initialized" errors in unit tests that don't go through the full app lifespan.

**Why this exists**:

- FastAPI's rate limiter requires Redis initialization via the `lifespan` context
- Unit tests that directly call endpoints bypass this initialization
- The mock allows isolated testing without Redis dependency

**What it does**:

- Automatically patches the global rate limiter for all tests
- Returns mock "allowed" responses for rate limit checks
- Ensures tests remain fast and don't require Redis

**When to update**:

- If you modify `whitemagic/api/rate_limit.py`, ensure the mock in `tests/conftest.py` stays compatible
- If adding new rate limiter features, update the mock return values accordingly

See `tests/conftest.py` for implementation details.

---

## Submitting Changes

### 1. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature"
```

**Commit message format**:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create a Pull Request

1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the PR template
5. Submit the PR

### Pull Request Guidelines

- **Title**: Clear and descriptive
- **Description**: What changes were made and why
- **Testing**: How you tested the changes
- **Screenshots**: If UI/UX changes
- **References**: Link to related issues

---

## Code Style

### Python

We use **Black** for formatting and **Ruff** for linting.

```bash
# Format code
black whitemagic/ tests/

# Lint code
ruff check whitemagic/ tests/

# Type check
mypy whitemagic/ --ignore-missing-imports
```

### Style Guidelines

- **Line length**: 100 characters (Black default)
- **Imports**: Sorted with `isort`
- **Docstrings**: Google style
- **Type hints**: Use where helpful
- **Naming**:
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_CASE`

### Example

```python
from typing import Optional, List
from pathlib import Path


class MemoryManager:
    """
    Manages memory operations for AI agents.

    Attributes:
        base_dir: Base directory for memory storage

    Example:
        >>> manager = MemoryManager(base_dir="/path/to/memories")
        >>> manager.create_memory("Title", "Content", "short_term")
    """

    def __init__(self, base_dir: str) -> None:
        """Initialize the memory manager."""
        self.base_dir = Path(base_dir)

    def create_memory(
        self,
        title: str,
        content: str,
        memory_type: str,
        tags: Optional[List[str]] = None,
    ) -> Path:
        """
        Create a new memory file.

        Args:
            title: Memory title
            content: Memory content
            memory_type: Type (short_term or long_term)
            tags: Optional list of tags

        Returns:
            Path to created memory file

        Raises:
            ValueError: If memory_type is invalid
        """
        # Implementation
        pass
```

---

## Project Structure

```text
whitemagic/
├── whitemagic/          # Core package
│   ├── __init__.py      # Package exports
│   ├── core.py          # Memory manager
│   ├── models.py        # Pydantic models
│   ├── api/             # REST API
│   │   ├── app.py       # FastAPI app
│   │   ├── auth.py      # Authentication
│   │   ├── database.py  # Database models
│   │   └── routes/      # API routes
│   └── utils.py         # Utilities
├── tests/               # Test suite
│   ├── test_memory_manager.py
│   ├── test_api_*.py
│   └── test_mcp_*.py
├── docs/                # Documentation
│   ├── guides/
│   ├── development/
│   └── production/
├── whitemagic-mcp/      # MCP server (TypeScript)
├── alembic/             # Database migrations
├── scripts/             # Utility scripts
└── .github/             # CI/CD workflows
```

---

## Development Workflow

### 1. Stay Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge into your branch
git merge upstream/main
```

### 2. Run Quality Checks

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run tests
pytest tests/ -v

# Check types
mypy whitemagic/
```

### 3. Keep PRs Focused

- One feature/fix per PR
- Small, reviewable changes
- Clear commit history

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/lbailey94/whitemagic/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lbailey94/whitemagic/discussions)
- **Documentation**: See `DOCUMENTATION.md`

---

## Recognition

Contributors will be recognized in:

- `README.md` contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to WhiteMagic! 🎉
