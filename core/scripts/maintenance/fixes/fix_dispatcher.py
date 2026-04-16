
with open("whitemagic/core/acceleration/hybrid_dispatcher_v2.py") as f:
    content = f.read()

# Replace PythonFastPath methods to use Rust
# First import rs
content = content.replace(
    "import subprocess",
    "import subprocess\nimport whitemagic_rust as rs"
)

# Fix prat_route
content = content.replace(
    """    @classmethod
    def prat_route(cls, tool: str) -> str:
        return cls.TOOL_TO_GANA.get(tool, "gana_ghost")""",
    """    @classmethod
    def prat_route(cls, tool: str) -> str:
        try:
            return rs.prat_route(tool)
        except Exception:
            return cls.TOOL_TO_GANA.get(tool, "gana_ghost")"""
)

# Fix get_predecessor
content = content.replace(
    """    @classmethod
    def get_predecessor(cls, gana: str) -> str:
        idx = cls.GANA_INDEX.get(gana, 0)
        return cls.GANA_ORDER[(idx - 1) % 28]""",
    """    @classmethod
    def get_predecessor(cls, gana: str) -> str:
        try:
            return rs.resonance_predecessor(gana)
        except Exception:
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx - 1) % 28]"""
)

# Fix get_successor
content = content.replace(
    """    @classmethod
    def get_successor(cls, gana: str) -> str:
        idx = cls.GANA_INDEX.get(gana, 0)
        return cls.GANA_ORDER[(idx + 1) % 28]""",
    """    @classmethod
    def get_successor(cls, gana: str) -> str:
        try:
            return rs.resonance_successor(gana)
        except Exception:
            idx = cls.GANA_INDEX.get(gana, 0)
            return cls.GANA_ORDER[(idx + 1) % 28]"""
)

# Replace HybridDispatcherV2 methods
# Fix prat_route instance method
content = content.replace(
    """    def prat_route(self, tool: str) -> str:
        operation = "prat_route"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            result = self._get_pool("prat").call({"op": "check", "tool": tool})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return result.get("gana", "gana_ghost")
        else:
            result = PythonFastPath.prat_route(tool)
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return result""",
    """    def prat_route(self, tool: str) -> str:
        operation = "prat_route"
        start = time.perf_counter()

        try:
            result = rs.prat_route(tool)
        except Exception:
            result = PythonFastPath.prat_route(tool)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result"""
)

# Fix prat_route_batch instance method
content = content.replace(
    """    def prat_route_batch(self, tools: list[str]) -> list[str]:
        \"\"\"Route multiple tools in batch (single IPC overhead if using Koka).\"\"\"
        if self._should_use_koka("prat_route"):
            requests = [{"op": "check", "tool": t} for t in tools]
            start = time.perf_counter()
            results = self._get_pool("prat").call_parallel(requests)
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency / len(tools), "prat_route")
            return [r.get("gana", "gana_ghost") for r in results]
        else:
            return [PythonFastPath.prat_route(t) for t in tools]""",
    """    def prat_route_batch(self, tools: list[str]) -> list[str]:
        \"\"\"Route multiple tools in batch\"\"\"
        start = time.perf_counter()
        try:
            results = rs.prat_route_batch(tools)
        except Exception:
            results = [PythonFastPath.prat_route(t) for t in tools]

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency / max(1, len(tools)), "prat_route")
        return results"""
)

with open("whitemagic/core/acceleration/hybrid_dispatcher_v2.py", "w") as f:
    f.write(content)
