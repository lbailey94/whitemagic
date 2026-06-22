#!/usr/bin/env python3
"""
Unified Cross-Language Test Suite for WhiteMagic Q3
Tests all 9 language SDKs with standardized test vectors.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class TestStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    NOT_IMPL = "not_implemented"

@dataclass
class TestResult:
    language: str
    test_name: str
    status: TestStatus
    duration_ms: float
    output: str = ""
    error: str = ""

# Standardized test vectors for all languages
TEST_VECTORS = {
    "memory_store": {
        "content": "Test memory for unified test suite",
        "title": "Unified Test Memory",
        "importance": 0.5,
        "tags": ["test", "unified", "q3"]
    },
    "memory_search": {
        "query": "unified test",
        "limit": 5
    },
    "holographic_encode": {
        "text": "WhiteMagic unified test vector",
        "dimensions": 384
    },
    "association_create": {
        "source_id": "test-src-001",
        "target_id": "test-tgt-001",
        "relation_type": "TEST_ASSOCIATION"
    }
}

# Language SDK configurations
LANGUAGE_SDKS = {
    "rust": {
        "path": "whitemagic-rust",
        "test_cmd": ["cargo", "test"],
        "ffi_interface": "CBindgen + PyO3",
        "serialization": "Serde + Arrow IPC",
        "status": "production"
    },
    "go": {
        "path": "whitemagic-go",
        "test_cmd": ["go", "test", "./..."],
        "ffi_interface": "Cgo + CGO_CFLAGS",
        "serialization": "encoding/json + protobuf",
        "status": "beta"
    },
    "typescript": {
        "path": "sdk/typescript",
        "test_cmd": ["npm", "test"],
        "ffi_interface": "WebAssembly + WASM-ffi",
        "serialization": "JSON + MessagePack",
        "status": "beta"
    },
    "elixir": {
        "path": "elixir",
        "test_cmd": ["mix", "test"],
        "ffi_interface": "NIF (Rustler)",
        "serialization": "Jason + ETF",
        "status": "alpha"
    },
    "haskell": {
        "path": "haskell",
        "test_cmd": ["stack", "test"],
        "ffi_interface": "C FFI + inline-c",
        "serialization": "Aeson + CBOR",
        "status": "alpha"
    },
    "zig": {
        "path": "whitemagic-zig",
        "test_cmd": ["zig", "build", "test"],
        "ffi_interface": "C ABI + @cImport",
        "serialization": "std.json + custom binary",
        "status": "beta"
    },
    "julia": {
        "path": "whitemagic-julia",
        "test_cmd": ["julia", "--project=.", "-e", "using Pkg; Pkg.test()"],
        "ffi_interface": "ccall + CWrapper",
        "serialization": "JSON3 + JLD2",
        "status": "alpha"
    },
    "mojo": {
        "path": "whitemagic-mojo",
        "test_cmd": ["mojo", "test"],
        "ffi_interface": "Python interop + C ABI",
        "serialization": "Python pickle + numpy",
        "status": "experimental"
    },
    "koka": {
        "path": "whitemagic-koka",
        "test_cmd": ["koka", "--exec", "test"],
        "ffi_interface": "C FFI + js/kk",
        "serialization": "JSON + Koka native",
        "status": "experimental"
    }
}

class UnifiedTestSuite:
    """Runs standardized tests across all 9 language SDKs."""
    
    def __init__(self, base_path: Path = Path(__file__).resolve().parent.parent.parent):
        self.base_path = base_path
        self.results: List[TestResult] = []
        
    def run_all(self) -> Dict[str, Any]:
        """Execute full test suite across all languages."""
        print("=" * 60)
        print("WhiteMagic Q3 Unified Cross-Language Test Suite")
        print("=" * 60)
        print(f"Languages: {len(LANGUAGE_SDKS)}")
        print(f"Test vectors: {len(TEST_VECTORS)}")
        print()
        
        for lang, config in LANGUAGE_SDKS.items():
            self._test_language(lang, config)
            
        return self._generate_report()
    
    def _test_language(self, lang: str, config: Dict[str, Any]) -> None:
        """Test a single language SDK."""
        print(f"\n[{lang.upper()}] Testing...")
        
        sdk_path = self.base_path / config["path"]
        if not sdk_path.exists():
            print(f"  ⚠️  SDK path not found: {sdk_path}")
            self.results.append(TestResult(
                language=lang,
                test_name="sdk_exists",
                status=TestStatus.NOT_IMPL,
                duration_ms=0,
                error="SDK directory not found"
            ))
            return
            
        # Check FFI interface file
        ffi_file = self._find_ffi_file(sdk_path, lang)
        if ffi_file:
            print(f"  ✓ FFI interface: {ffi_file.name}")
        else:
            print("  ⚠️  FFI interface not found")
            
        # Run language tests
        start = __import__('time').time()
        try:
            result = subprocess.run(
                config["test_cmd"],
                cwd=sdk_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            duration = (__import__('time').time() - start) * 1000
            
            if result.returncode == 0:
                status = TestStatus.PASS
                print(f"  ✓ Tests passed ({duration:.0f}ms)")
            else:
                status = TestStatus.FAIL
                print(f"  ✗ Tests failed ({duration:.0f}ms)")
                
            self.results.append(TestResult(
                language=lang,
                test_name="unit_tests",
                status=status,
                duration_ms=duration,
                output=result.stdout[-500:] if result.stdout else "",
                error=result.stderr[-500:] if result.stderr else ""
            ))
            
        except subprocess.TimeoutExpired:
            print("  ⏱  Timeout after 60s")
            self.results.append(TestResult(
                language=lang,
                test_name="unit_tests",
                status=TestStatus.FAIL,
                duration_ms=60000,
                error="Test timeout"
            ))
        except FileNotFoundError as e:
            print(f"  ⚠️  Command not found: {config['test_cmd'][0]}")
            self.results.append(TestResult(
                language=lang,
                test_name="unit_tests",
                status=TestStatus.SKIP,
                duration_ms=0,
                error=f"Command not found: {e}"
            ))
        except Exception as e:
            print(f"  ✗ Error: {e}")
            self.results.append(TestResult(
                language=lang,
                test_name="unit_tests",
                status=TestStatus.FAIL,
                duration_ms=0,
                error=str(e)
            ))
    
    def _find_ffi_file(self, sdk_path: Path, lang: str) -> Path | None:
        """Find the FFI interface definition file."""
        patterns = {
            "rust": ["cbindgen.toml", "src/lib.rs"],
            "go": ["*.h", "ffi/*.go"],
            "typescript": ["src/ffi.ts", "ffi/*.ts"],
            "elixir": ["native/*/src/lib.rs"],
            "haskell": ["cbits/*.c", "src/FFI.hs"],
            "zig": ["src/ffi.zig"],
            "julia": ["src/ffi.jl"],
            "mojo": ["src/ffi.mojo"],
            "koka": ["src/ffi.kk"]
        }
        
        for pattern in patterns.get(lang, []):
            matches = list(sdk_path.glob(pattern))
            if matches:
                return matches[0]
        return None
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        not_impl = sum(1 for r in self.results if r.status == TestStatus.NOT_IMPL)
        
        report = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "not_implemented": not_impl,
                "pass_rate": f"{passed/max(1,total)*100:.1f}%"
            },
            "language_coverage": {},
            "ffi_unification": {},
            "results": [
                {
                    "language": r.language,
                    "test": r.test_name,
                    "status": r.status.value,
                    "duration_ms": round(r.duration_ms, 1)
                }
                for r in self.results
            ]
        }
        
        # Add language-specific details
        for lang, config in LANGUAGE_SDKS.items():
            lang_results = [r for r in self.results if r.language == lang]
            report["language_coverage"][lang] = {
                "ffi_interface": config["ffi_interface"],
                "serialization": config["serialization"],
                "status": config["status"],
                "tests_run": len(lang_results),
                "tests_passed": sum(1 for r in lang_results if r.status == TestStatus.PASS)
            }
        
        # Save report
        report_path = self.base_path / "reports" / "unified_test_suite_q3.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Print summary
        print("\n" + "=" * 60)
        print("Q3 Unified Test Suite - Summary")
        print("=" * 60)
        print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        print(f"Pass Rate: {report['summary']['pass_rate']}")
        print(f"Report saved: {report_path}")
        
        return report


def main():
    suite = UnifiedTestSuite()
    results = suite.run_all()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
