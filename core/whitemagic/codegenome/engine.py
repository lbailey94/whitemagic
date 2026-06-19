# ruff: noqa: BLE001
"""CodeGenome Template Engine
============================
Loads YAML code templates from $WM_STATE_ROOT/codegenome/ and built-in defaults.
Supports variable substitution, tiered variant selection, dependency tracking,
signature matching, and lineage for the Vibe Coding God-Kit.

Template format (YAML):
    name: fastapi_endpoint
    version: 1
    description: Minimal FastAPI endpoint with validation
    tier_variants:
      xianfeng: |
        @router.get("/{{path}}")
        def get_{{name}}():
            return {"ok": True}
      wei_wuzu: |
        @router.get("/{{path}}")
        def get_{{name}}():
            # TODO: add service layer
            return {"ok": True}
      huben: |
        @router.get("/{{path}}")
        async def get_{{name}}(
            db: AsyncSession = Depends(get_db),
        ):
            result = await service.get_{{name}}(db)
            return result
    default: |
        @router.get("/{{path}}")
        def get_{{name}}():
            return {"ok": True}
    variables:
      - path
      - name
    dependencies:
      - fastapi
      - sqlalchemy
    signature: "router.get -> JSONResponse"
    tags: [fastapi, endpoint, rest]
    parent_id: ""
    success_rate: 0.95

Usage:
    engine = get_codegenome_engine()
    code = engine.render("fastapi_endpoint", path="/items", name="items",
                         tier="xianfeng")
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

TIER_ELEMENTS = ("xianfeng", "wei_wuzu", "huben")

# Variable pattern: {{variable_name}}
_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass
class CodeTemplate:
    """A single code template with lineage tracking."""
    name: str
    description: str = ""
    version: int = 1
    default: str = ""
    tier_variants: dict[str, str] = field(default_factory=dict)
    variables: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    signature: str = ""
    tags: list[str] = field(default_factory=list)
    parent_id: str = ""  # For lineage: forked-from template name
    success_rate: float = 1.0
    last_used: str = ""  # ISO-8601 timestamp
    source: str = "builtin"  # "builtin" or file path

    def render(self, tier: str | None = None, **kwargs: Any) -> str:
        """Render the template with variable substitution."""
        if tier and tier in self.tier_variants:
            text = self.tier_variants[tier]
        else:
            text = self.default

        def _replace(match: Any) -> Any:
            var_name = match.group(1)
            return str(kwargs.get(var_name, f"{{{{{var_name}}}}}"))

        return _VAR_PATTERN.sub(_replace, text)

    def fork(self, new_name: str, body_delta: str = "") -> CodeTemplate:
        """Create a child template with incremented version."""
        return CodeTemplate(
            name=new_name,
            description=f"Forked from {self.name}: {self.description}",
            version=self.version + 1,
            default=body_delta or self.default,
            tier_variants=dict(self.tier_variants),
            variables=list(self.variables),
            dependencies=list(self.dependencies),
            signature=self.signature,
            tags=list(self.tags),
            parent_id=self.name,
            success_rate=1.0,
            source="forked",
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "variables": self.variables,
            "tier_variants": list(self.tier_variants.keys()),
            "dependencies": self.dependencies,
            "signature": self.signature,
            "tags": self.tags,
            "parent_id": self.parent_id,
            "success_rate": self.success_rate,
            "last_used": self.last_used,
            "source": self.source,
        }


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

_BUILTIN_TEMPLATES: list[CodeTemplate] = [
    CodeTemplate(
        name="fastapi_endpoint",
        description="Minimal FastAPI GET endpoint",
        version=1,
        default=(
            '@router.get("/{{path}}")\n'
            "def get_{{name}}():\n"
            '    return {"ok": True}\n'
        ),
        tier_variants={
            "xianfeng": (
                '@router.get("/{{path}}")\n'
                "def get_{{name}}():\n"
                '    return {"ok": True}\n'
            ),
            "wei_wuzu": (
                '@router.get("/{{path}}")\n'
                "def get_{{name}}():\n"
                "    # TODO: add validation\n"
                '    return {"ok": True}\n'
            ),
            "huben": (
                '@router.get("/{{path}}")\n'
                "async def get_{{name}}(\n"
                "    db: AsyncSession = Depends(get_db),\n"
                "):\n"
                "    result = await service.get_{{name}}(db)\n"
                "    return result\n"
            ),
        },
        variables=["path", "name"],
        dependencies=["fastapi"],
        signature="router.get -> JSONResponse",
        tags=["fastapi", "endpoint", "rest"],
    ),
    CodeTemplate(
        name="pytest_fixture",
        description="Reusable pytest fixture pattern",
        version=1,
        default=(
            "@pytest.fixture\n"
            "def {{name}}_fixture():\n"
            "    instance = create_{{name}}()\n"
            "    yield instance\n"
            "    cleanup(instance)\n"
        ),
        tier_variants={
            "xianfeng": (
                "@pytest.fixture\n"
                "def {{name}}_fixture():\n"
                "    return {{name}}()\n"
            ),
            "wei_wuzu": (
                "@pytest.fixture\n"
                "def {{name}}_fixture():\n"
                "    instance = create_{{name}}()\n"
                "    yield instance\n"
                "    cleanup(instance)\n"
            ),
            "huben": (
                "@pytest.fixture(scope=\"session\")\n"
                "def {{name}}_fixture():\n"
                "    with create_{{name}}() as instance:\n"
                "        yield instance\n"
            ),
        },
        variables=["name"],
        dependencies=["pytest"],
        signature="fixture -> yield resource",
        tags=["pytest", "testing", "fixture"],
    ),
    CodeTemplate(
        name="pydantic_model",
        description="Pydantic base model with validation",
        version=1,
        default=(
            "class {{name}}(BaseModel):\n"
            "    id: int\n"
            '    label: str = ""\n'
        ),
        tier_variants={
            "xianfeng": (
                "class {{name}}(BaseModel):\n"
                "    id: int\n"
            ),
            "wei_wuzu": (
                "class {{name}}(BaseModel):\n"
                "    id: int\n"
                '    label: str = ""\n'
            ),
            "huben": (
                "class {{name}}(BaseModel):\n"
                "    model_config = ConfigDict(from_attributes=True)\n\n"
                "    id: int\n"
                '    label: str = Field(default="", max_length=100)\n'
                "    created_at: datetime = Field(default_factory=utc_now)\n"
            ),
        },
        variables=["name"],
        dependencies=["pydantic"],
        signature="BaseModel subclass",
        tags=["pydantic", "model", "validation"],
    ),
    CodeTemplate(
        name="sqlalchemy_model",
        description="SQLAlchemy declarative base model",
        version=1,
        default=(
            "class {{name}}(Base):\n"
            "    __tablename__ = '{{table_name}}'\n\n"
            "    id: Mapped[int] = mapped_column(primary_key=True)\n"
        ),
        tier_variants={
            "xianfeng": (
                "class {{name}}(Base):\n"
                "    __tablename__ = '{{table_name}}'\n"
                "    id = Column(Integer, primary_key=True)\n"
            ),
            "wei_wuzu": (
                "class {{name}}(Base):\n"
                "    __tablename__ = '{{table_name}}'\n\n"
                "    id: Mapped[int] = mapped_column(primary_key=True)\n"
                "    created_at: Mapped[datetime] = mapped_column(\n"
                "        DateTime, default=datetime.utcnow\n"
                "    )\n"
            ),
            "huben": (
                "class {{name}}(Base):\n"
                "    __tablename__ = '{{table_name}}'\n\n"
                "    id: Mapped[int] = mapped_column(primary_key=True)\n"
                "    created_at: Mapped[datetime] = mapped_column(\n"
                "        DateTime, default=datetime.utcnow\n"
                "    )\n"
                "    updated_at: Mapped[datetime] = mapped_column(\n"
                "        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow\n"
                "    )\n\n"
                "    def __repr__(self) -> str:\n"
                '        return f"<{{name}}(id={self.id})>"\n'
            ),
        },
        variables=["name", "table_name"],
        dependencies=["sqlalchemy"],
        signature="Base declarative model",
        tags=["sqlalchemy", "orm", "database"],
    ),
    CodeTemplate(
        name="dockerfile",
        description="Multi-stage Dockerfile",
        version=1,
        default=(
            "FROM python:3.12-slim\n\n"
            "WORKDIR /app\n"
            "COPY . .\n"
            'CMD ["python", "main.py"]\n'
        ),
        tier_variants={
            "xianfeng": (
                "FROM python:3.12-slim\n\n"
                "WORKDIR /app\n"
                "COPY . .\n"
                'CMD ["python", "main.py"]\n'
            ),
            "wei_wuzu": (
                "FROM python:3.12-slim as builder\n\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\n\n"
                "COPY . .\n"
                'CMD ["python", "main.py"]\n'
            ),
            "huben": (
                "# Build stage\n"
                "FROM python:3.12-slim as builder\n\n"
                "WORKDIR /app\n"
                "COPY requirements.txt .\n"
                "RUN pip install --user --no-cache-dir -r requirements.txt\n\n"
                "# Runtime stage\n"
                "FROM python:3.12-slim\n\n"
                "WORKDIR /app\n"
                "COPY --from=builder /root/.local /root/.local\n"
                "COPY . .\n\n"
                "ENV PATH=/root/.local/bin:$PATH\n"
                'CMD ["python", "main.py"]\n'
            ),
        },
        variables=[],
        dependencies=["docker"],
        signature="Dockerfile multi-stage",
        tags=["docker", "container", "deployment"],
    ),
    CodeTemplate(
        name="github_action",
        description="GitHub Actions CI workflow",
        version=1,
        default=(
            "name: CI\n\n"
            "on: [push, pull_request]\n\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - run: pytest\n"
        ),
        tier_variants={
            "xianfeng": (
                "name: CI\n\n"
                "on: [push, pull_request]\n\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - run: pytest\n"
            ),
            "wei_wuzu": (
                "name: CI\n\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "  pull_request:\n\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    strategy:\n"
                "      matrix:\n"
                "        python-version: ['3.11', '3.12']\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: ${{ matrix.python-version }}\n"
                "      - run: pip install -r requirements.txt\n"
                "      - run: pytest\n"
            ),
            "huben": (
                "name: CI\n\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "  pull_request:\n\n"
                "jobs:\n"
                "  lint:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: '3.12'\n"
                "      - run: pip install ruff mypy\n"
                "      - run: ruff check .\n"
                "      - run: mypy .\n\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    strategy:\n"
                "      matrix:\n"
                "        python-version: ['3.11', '3.12']\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: ${{ matrix.python-version }}\n"
                "      - run: pip install -r requirements.txt\n"
                "      - run: pytest --cov=src --cov-report=xml\n"
                "      - uses: codecov/codecov-action@v3\n"
            ),
        },
        variables=[],
        dependencies=["github-actions"],
        signature=".github/workflows/ci.yml",
        tags=["github", "ci", "workflow", "devops"],
    ),
    CodeTemplate(
        name="pydantic_settings",
        description="Pydantic Settings with env var support",
        version=1,
        default=(
            "class Settings(BaseSettings):\n"
            "    app_name: str = '{{app_name}}'\n"
            '    debug: bool = False\n'
        ),
        tier_variants={
            "xianfeng": (
                "class Settings(BaseSettings):\n"
                "    app_name: str = '{{app_name}}'\n"
            ),
            "wei_wuzu": (
                "class Settings(BaseSettings):\n"
                "    model_config = SettingsConfigDict(env_file='.env')\n\n"
                "    app_name: str = '{{app_name}}'\n"
                "    debug: bool = False\n"
                "    database_url: str = 'sqlite:///app.db'\n"
            ),
            "huben": (
                "class Settings(BaseSettings):\n"
                "    model_config = SettingsConfigDict(\n"
                "        env_file='.env',\n"
                "        env_file_encoding='utf-8',\n"
                "        case_sensitive=False,\n"
                "    )\n\n"
                "    app_name: str = '{{app_name}}'\n"
                "    debug: bool = False\n"
                "    database_url: SecretStr = SecretStr('sqlite:///app.db')\n"
                "    log_level: str = 'INFO'\n\n"
                "    @field_validator('log_level')\n"
                "    @classmethod\n"
                "    def check_log_level(cls, v: str) -> str:\n"
                "        if v not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):\n"
                "            raise ValueError('Invalid log level')\n"
                "        return v\n"
            ),
        },
        variables=["app_name"],
        dependencies=["pydantic-settings"],
        signature="BaseSettings subclass",
        tags=["pydantic", "settings", "config"],
    ),
]


class CodeGenomeEngine:
    """Manages code templates from built-in defaults and YAML files.

    Templates in $WM_STATE_ROOT/codegenome/ override built-ins by name.
    """

    def __init__(self, codegenome_dir: str | None = None) -> None:
        self._templates: dict[str, CodeTemplate] = {}
        self._lock = threading.Lock()

        # Load built-ins
        for t in _BUILTIN_TEMPLATES:
            self._templates[t.name] = t

        # Load from disk
        from whitemagic.config.paths import WM_ROOT
        self._codegenome_dir = codegenome_dir or str(WM_ROOT / "codegenome")
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load YAML templates from the codegenome directory."""
        if not HAS_YAML:
            return

        cg_path = Path(self._codegenome_dir)
        if not cg_path.is_dir():
            return

        for yaml_file in sorted(list(cg_path.glob("*.yaml")) + list(cg_path.glob("*.yml"))):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict) or "name" not in data:
                    continue

                template = CodeTemplate(
                    name=data["name"],
                    description=data.get("description", ""),
                    version=data.get("version", 1),
                    default=data.get("default", ""),
                    tier_variants=data.get("tier_variants", {}),
                    variables=data.get("variables", []),
                    dependencies=data.get("dependencies", []),
                    signature=data.get("signature", ""),
                    tags=data.get("tags", []),
                    parent_id=data.get("parent_id", ""),
                    success_rate=data.get("success_rate", 1.0),
                    last_used=data.get("last_used", ""),
                    source=str(yaml_file),
                )
                self._templates[template.name] = template
                logger.debug("Loaded code template: %s from %s", template.name, yaml_file)
            except Exception as e:
                logger.warning("Failed to load code template %s: %s", yaml_file, e)

    def render(self, template_name: str, tier: str | None = None, **kwargs: Any) -> str:
        """Render a named template with variables."""
        template = self._templates.get(template_name)
        if template is None:
            return f"[unknown template: {template_name}]"
        return template.render(tier=tier, **kwargs)

    def list_templates(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List all available templates, optionally filtered by tag."""
        results = []
        for t in self._templates.values():
            if tag and tag not in t.tags:
                continue
            results.append(t.to_dict())
        return sorted(results, key=lambda x: x["name"])

    def get_template(self, name: str) -> CodeTemplate | None:
        """Get a template by name."""
        return self._templates.get(name)

    def register(self, template: CodeTemplate) -> None:
        """Register a template at runtime."""
        with self._lock:
            self._templates[template.name] = template

    def fork_template(self, name: str, new_name: str, body_delta: str = "") -> CodeTemplate | None:
        """Fork an existing template into a new one."""
        parent = self._templates.get(name)
        if parent is None:
            return None
        child = parent.fork(new_name, body_delta)
        with self._lock:
            self._templates[child.name] = child
        return child

    def reload(self) -> None:
        """Reload templates from disk (preserves built-ins)."""
        with self._lock:
            for t in _BUILTIN_TEMPLATES:
                self._templates[t.name] = t
            self._load_from_disk()

    def status(self) -> dict[str, Any]:
        """Get engine status."""
        return {
            "total_templates": len(self._templates),
            "builtin_count": sum(1 for t in self._templates.values() if t.source == "builtin"),
            "disk_count": sum(1 for t in self._templates.values() if t.source not in ("builtin", "forked")),
            "forked_count": sum(1 for t in self._templates.values() if t.source == "forked"),
            "codegenome_dir": self._codegenome_dir,
            "yaml_available": HAS_YAML,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine: CodeGenomeEngine | None = None
_engine_lock = threading.Lock()


def get_codegenome_engine() -> CodeGenomeEngine:
    """Get the global CodeGenomeEngine instance."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = CodeGenomeEngine()
    return _engine
