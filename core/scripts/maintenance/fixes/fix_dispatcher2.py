
with open("whitemagic/core/acceleration/hybrid_dispatcher_v2.py") as f:
    content = f.read()

# Fix get_predecessor instance method
content = content.replace(
    """    def get_predecessor(self, gana: str) -> str:
        operation = "resonance_predecessor"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            result = self._get_pool("resonance").call({"op": "predecessor", "gana": gana})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return result.get("predecessor", "gana_horn")
        else:
            result = PythonFastPath.get_predecessor(gana)
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return result""",
    """    def get_predecessor(self, gana: str) -> str:
        operation = "resonance_predecessor"
        start = time.perf_counter()
        try:
            result = rs.resonance_predecessor(gana)
        except Exception:
            result = PythonFastPath.get_predecessor(gana)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result"""
)

# Fix get_successor instance method
content = content.replace(
    """    def get_successor(self, gana: str) -> str:
        operation = "resonance_successor"
        use_koka = self._should_use_koka(operation)

        start = time.perf_counter()
        if use_koka:
            result = self._get_pool("resonance").call({"op": "successor", "gana": gana})
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(True, latency, operation)
            return result.get("successor", "gana_horn")
        else:
            result = PythonFastPath.get_successor(gana)
            latency = (time.perf_counter() - start) * 1_000_000
            self._record_latency(False, latency, operation)
            return result""",
    """    def get_successor(self, gana: str) -> str:
        operation = "resonance_successor"
        start = time.perf_counter()
        try:
            result = rs.resonance_successor(gana)
        except Exception:
            result = PythonFastPath.get_successor(gana)

        latency = (time.perf_counter() - start) * 1_000_000
        self._record_latency(False, latency, operation)
        return result"""
)

with open("whitemagic/core/acceleration/hybrid_dispatcher_v2.py", "w") as f:
    f.write(content)
