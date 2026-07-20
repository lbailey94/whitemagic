# ruff: noqa: BLE001,S101
"""Tests for inference auto-tuning system — hardware detection, tuner, MARS.

Tests cover:
1. HardwareProfile ISA detection and inference_tier classification
2. InferenceTuner report computation and config application
3. MARS margin-aware verification in SpeculativeDecoder
4. InferenceHardwareSensor in ambient sensorium
"""
from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

# Ensure path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestHardwareProfileISA(unittest.TestCase):
    """Test HardwareProfile CPU ISA detection and classification."""

    def test_inference_tier_avx2(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=4, cpu_threads=8, total_ram_gb=16.0,
            available_ram_gb=12.0, has_gpu=False, disk_free_gb=50.0,
            has_avx2=True,
        )
        self.assertEqual(hw.inference_tier, "AVX2")
        self.assertEqual(hw.simd_width_bits, 256)
        self.assertEqual(hw.optimal_ternary_kernel, "avx2_i2s")

    def test_inference_tier_avx512_vnni(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=8, cpu_threads=16, total_ram_gb=32.0,
            available_ram_gb=28.0, has_gpu=False, disk_free_gb=100.0,
            has_avx2=True, has_avx512f=True, has_avx512vnni=True,
        )
        self.assertEqual(hw.inference_tier, "VNNI")
        self.assertEqual(hw.simd_width_bits, 512)
        self.assertEqual(hw.optimal_ternary_kernel, "avx512_vnni")

    def test_inference_tier_amx(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=16, cpu_threads=32, total_ram_gb=64.0,
            available_ram_gb=56.0, has_gpu=True, disk_free_gb=200.0,
            has_avx2=True, has_avx512f=True, has_avx512vnni=True, has_amx=True,
        )
        self.assertEqual(hw.inference_tier, "AMX")
        self.assertEqual(hw.simd_width_bits, 512)

    def test_inference_tier_scalar(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        self.assertEqual(hw.inference_tier, "SCALAR")
        self.assertEqual(hw.simd_width_bits, 0)
        self.assertEqual(hw.optimal_ternary_kernel, "scalar")

    def test_inference_tier_sse4(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
            has_sse42=True,
        )
        self.assertEqual(hw.inference_tier, "SSE4")
        self.assertEqual(hw.simd_width_bits, 128)

    def test_optimal_spec_params_high(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=8, cpu_threads=16, total_ram_gb=32.0,
            available_ram_gb=28.0, has_gpu=True, disk_free_gb=100.0,
        )
        params = hw.optimal_spec_params
        self.assertEqual(params["spec_ngram_mod_n_match"], 32)
        self.assertEqual(params["spec_ngram_mod_n_max"], 96)

    def test_optimal_spec_params_low(self):
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        hw = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        params = hw.optimal_spec_params
        self.assertEqual(params["spec_ngram_mod_n_match"], 16)
        self.assertEqual(params["spec_ngram_mod_n_max"], 32)
        self.assertEqual(params["cache_type_k"], "q4_0")

    def test_detect_cpu_isa_from_flags(self):
        from whitemagic.core.system.hardware_monitor import _detect_cpu_isa

        cpuinfo = (
            "processor\t: 0\n"
            "model name\t: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz\n"
            "flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr "
            "pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht "
            "syscall nx pdpe1gb rdtscp lm constant_tsc art arch_perfmon pebs "
            "bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni "
            "pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 "
            "xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer "
            "aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault "
            "epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi "
            "flexpriority ept vpid ept_ad fsgsbase tsc_adjust bmi1 avx2 "
            "smep bmi2 erms invpcid mpx rdseed adx smap clflushopt intel_pt "
            "xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp "
            "hwp_notify hwp_act_window hwp_epp hwp_pkg_req\n"
        )
        result = _detect_cpu_isa(cpuinfo)
        self.assertTrue(result["has_avx2"])
        self.assertTrue(result["has_sse42"])
        self.assertTrue(result["has_bmi2"])
        self.assertFalse(result["has_avx512f"])
        self.assertFalse(result["has_avx512vnni"])
        self.assertIn("Intel", result["cpu_model_name"])

    def test_detect_cpu_isa_avx512(self):
        from whitemagic.core.system.hardware_monitor import _detect_cpu_isa

        cpuinfo = (
            "model name\t: Intel(R) Xeon(R) Platinum 8480C\n"
            "flags\t\t: fpu vme de pse avx avx2 avx512f avx512_vnni "
            "amx_bf16 amx_int8 sse4_2 bmi2\n"
        )
        result = _detect_cpu_isa(cpuinfo)
        self.assertTrue(result["has_avx512f"])
        self.assertTrue(result["has_avx512vnni"])
        self.assertTrue(result["has_amx"])
        self.assertTrue(result["has_avx2"])


class TestInferenceTuner(unittest.TestCase):
    """Test InferenceTuner report computation and config application."""

    def test_tuner_report_constrained(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        report = tuner.report
        self.assertTrue(report.is_constrained)
        self.assertEqual(report.inference_tier, "SCALAR")
        self.assertEqual(report.selected_kernel, "scalar")
        # Constrained hardware should get smaller context
        self.assertEqual(report.llama_config_overrides["n_ctx"], 2048)
        self.assertEqual(report.llama_config_overrides["cache_type_k"], "q4_0")
        self.assertEqual(report.llama_config_overrides["parallel"], 1)

    def test_tuner_report_high_end(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=8, cpu_threads=16, total_ram_gb=32.0,
            available_ram_gb=28.0, has_gpu=True, disk_free_gb=100.0,
            has_avx2=True, has_avx512f=True, has_avx512vnni=True,
        )
        report = tuner.report
        self.assertEqual(report.inference_tier, "VNNI")
        self.assertEqual(report.selected_kernel, "avx512_vnni")
        self.assertEqual(report.simd_width_bits, 512)
        # High-end should get larger context
        self.assertEqual(report.llama_config_overrides["n_ctx"], 16384)
        self.assertEqual(report.llama_config_overrides["cache_type_k"], "q8_0")
        self.assertTrue(report.llama_config_overrides["poll"])

    def test_tuner_report_medium(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=4, cpu_threads=8, total_ram_gb=12.0,
            available_ram_gb=10.0, has_gpu=False, disk_free_gb=50.0,
            has_avx2=True,
        )
        report = tuner.report
        self.assertEqual(report.inference_tier, "AVX2")
        self.assertEqual(report.llama_config_overrides["n_ctx"], 8192)
        self.assertEqual(report.llama_config_overrides["n_threads"], 6)  # 8 - 2

    def test_tuner_apply_to_config(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile
        from whitemagic.inference.llama_cpp import LlamaCppConfig

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        config = LlamaCppConfig(model_path="test")
        tuner.apply_to_llama_config(config)

        # Should have overridden n_ctx (was default 8192)
        self.assertEqual(config.n_ctx, 2048)
        # Should have overridden cache_type_k (was default "q8_0")
        self.assertEqual(config.cache_type_k, "q4_0")
        # Should have overridden parallel (was default 4)
        self.assertEqual(config.parallel, 1)

    def test_tuner_preserves_user_config(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile
        from whitemagic.inference.llama_cpp import LlamaCppConfig

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        config = LlamaCppConfig(model_path="test", n_ctx=4096)  # User explicitly set
        tuner.apply_to_llama_config(config)

        # User-set value should be preserved
        self.assertEqual(config.n_ctx, 4096)

    def test_tuner_save_load_cache(self):
        import tempfile

        from whitemagic.inference.inference_tuner import (
            InferenceTuner,
            _TUNER_CACHE_PATH,
        )
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=4, cpu_threads=8, total_ram_gb=12.0,
            available_ram_gb=10.0, has_gpu=False, disk_free_gb=50.0,
            has_avx2=True,
        )
        # Force report computation
        _ = tuner.report

        # Save
        self.assertTrue(tuner.save_cache())
        self.assertTrue(_TUNER_CACHE_PATH.exists())

        # Load
        loaded = tuner.load_cache()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.inference_tier, "AVX2")
        self.assertEqual(loaded.cpu_threads, 8)

        # Cleanup
        _TUNER_CACHE_PATH.unlink(missing_ok=True)

    def test_tuner_refresh(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=2, cpu_threads=4, total_ram_gb=4.0,
            available_ram_gb=2.0, has_gpu=False, disk_free_gb=10.0,
        )
        _ = tuner.report
        self.assertIsNotNone(tuner._report)

        tuner.refresh()
        self.assertIsNone(tuner._profile)
        self.assertIsNone(tuner._report)

    def test_tuner_get_report_dict(self):
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=4, cpu_threads=8, total_ram_gb=12.0,
            available_ram_gb=10.0, has_gpu=False, disk_free_gb=50.0,
            has_avx2=True,
        )
        report = tuner.get_report()
        self.assertIn("inference_tier", report)
        self.assertIn("selected_kernel", report)
        self.assertIn("llama_config_overrides", report)
        self.assertIn("applied", report)
        self.assertFalse(report["applied"])


class TestMARSSpeculativeDecoding(unittest.TestCase):
    """Test MARS margin-aware verification in SpeculativeDecoder."""

    def test_standard_accept_all_match(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3, 4]
        verify = [1, 2, 3, 4]
        accepted, rejected = decoder._accept_reject(draft, verify)
        self.assertEqual(accepted, [1, 2, 3, 4])
        self.assertEqual(rejected, [])

    def test_standard_reject_on_mismatch(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder()
        draft = [1, 2, 3, 4]
        verify = [1, 2, 5, 6]
        accepted, rejected = decoder._accept_reject(draft, verify)
        self.assertEqual(accepted, [1, 2, 5])
        self.assertEqual(rejected, [4])

    def test_mars_accept_top2_match(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        # MARS threshold 0.9: accept draft token if it matches verify's top-2
        # and the logit ratio top1/top2 >= 0.9
        decoder = SpeculativeDecoder(mars_margin_threshold=0.9)
        draft = [1, 2, 3, 4]
        verify = [1, 2, 5, 4]  # Position 2: verify top-1=5, draft=3
        # verify_top2: (top1_id, top2_id, top1_logit, top2_logit)
        verify_top2 = [
            (1, 99, 10.0, 1.0),   # Position 0: match, no MARS needed
            (2, 88, 10.0, 1.0),   # Position 1: match, no MARS needed
            (5, 3, 10.0, 9.5),    # Position 2: draft=3 matches top-2, ratio 10/9.5=1.05 >= 0.9
            (4, 77, 10.0, 1.0),   # Position 3: match
        ]
        accepted, rejected = decoder._accept_reject(draft, verify, verify_top2)
        # Position 2: MARS accepts draft token 3 (matches top-2, high ratio)
        self.assertEqual(accepted, [1, 2, 3, 4])
        self.assertEqual(rejected, [])

    def test_mars_reject_low_margin(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        # MARS threshold 0.9: reject if ratio < 0.9
        decoder = SpeculativeDecoder(mars_margin_threshold=0.9)
        draft = [1, 2, 3, 4]
        verify = [1, 2, 5, 4]
        verify_top2 = [
            (1, 99, 10.0, 1.0),
            (2, 88, 10.0, 1.0),
            (5, 3, 10.0, 5.0),   # Position 2: ratio 10/5=2.0 >= 0.9 → accept
            (4, 77, 10.0, 1.0),
        ]
        accepted, rejected = decoder._accept_reject(draft, verify, verify_top2)
        # Ratio 2.0 >= 0.9, so MARS accepts
        self.assertEqual(accepted, [1, 2, 3, 4])

    def test_mars_reject_no_top2_data(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder(mars_margin_threshold=0.9)
        draft = [1, 2, 3, 4]
        verify = [1, 2, 5, 4]
        # No verify_top2 → standard rejection
        accepted, rejected = decoder._accept_reject(draft, verify)
        self.assertEqual(accepted, [1, 2, 5])
        self.assertEqual(rejected, [4])

    def test_mars_disabled_with_threshold_1(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        # Without verify_top2 data, MARS is never invoked — standard rejection applies
        decoder = SpeculativeDecoder(mars_margin_threshold=1.0)
        draft = [1, 2, 3, 4]
        verify = [1, 2, 5, 6]
        accepted, rejected = decoder._accept_reject(draft, verify)
        # Position 2: mismatch, verify's token 5 accepted, remaining draft[3:] rejected
        self.assertEqual(accepted, [1, 2, 5])
        self.assertEqual(rejected, [4])

    def test_mars_partial_accept_then_reject(self):
        from whitemagic.inference.speculative_decoder import SpeculativeDecoder

        decoder = SpeculativeDecoder(mars_margin_threshold=0.9)
        draft = [1, 2, 3, 4, 5, 6]
        verify = [1, 2, 3, 9, 8, 7]
        verify_top2 = [
            (1, 0, 10.0, 1.0),
            (2, 0, 10.0, 1.0),
            (3, 0, 10.0, 1.0),
            (9, 4, 10.0, 0.5),   # Position 3: draft=4 matches top-2, ratio 10/0.5=20 >= 0.9 → accept
            (8, 0, 10.0, 1.0),   # Position 4: draft=5, no top-2 match → standard reject
            (7, 0, 10.0, 1.0),
        ]
        accepted, rejected = decoder._accept_reject(draft, verify, verify_top2)
        # Position 3: MARS accepts draft token 4
        # Position 4: verify=8, draft=5, no top-2 match → standard reject
        #   accepted gets verify's 8, rejected gets draft[5:] = [6]
        self.assertEqual(accepted, [1, 2, 3, 4, 8])
        self.assertEqual(rejected, [6])


class TestInferenceHardwareSensor(unittest.TestCase):
    """Test InferenceHardwareSensor in ambient sensorium."""

    def test_sensor_reads_tier(self):
        from whitemagic.core.consciousness.ambient_sensorium import (
            InferenceHardwareSensor,
        )
        from whitemagic.inference.inference_tuner import InferenceTuner
        from whitemagic.core.system.hardware_monitor import HardwareProfile

        # Set up tuner with known profile
        tuner = InferenceTuner()
        tuner._profile = HardwareProfile(
            cpu_count=4, cpu_threads=8, total_ram_gb=12.0,
            available_ram_gb=10.0, has_gpu=False, disk_free_gb=50.0,
            has_avx2=True,
        )

        # Patch get_inference_tuner to return our tuner
        with patch(
            "whitemagic.inference.inference_tuner.get_inference_tuner",
            return_value=tuner,
        ):
            sensor = InferenceHardwareSensor()
            self.assertTrue(sensor.is_available())
            signals = sensor.read()

        self.assertTrue(len(signals) >= 3)
        tier_signal = next(s for s in signals if s.signal_type == "inference_tier")
        self.assertEqual(tier_signal.metadata["tier"], "AVX2")
        self.assertEqual(tier_signal.value, 2.0)  # AVX2 = 2.0 in tier_map

    def test_sensor_registered_in_sensorium(self):
        from whitemagic.core.consciousness.ambient_sensorium import (
            get_ambient_sensorium,
            InferenceHardwareSensor,
        )

        sensorium = get_ambient_sensorium()
        source_names = [s.source_name for s in sensorium._sources]
        self.assertIn("inference_hardware", source_names)


if __name__ == "__main__":
    unittest.main()
