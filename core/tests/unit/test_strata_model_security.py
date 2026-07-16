"""Tests for STRATA model file format security checkers."""
import tempfile
from pathlib import Path

import pytest

from whitemagic.tools.strata.checkers import get_checkers
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _run_checkers(project_path: Path) -> list[Finding]:
    """Run all registered checkers and return findings."""
    file_index = FileIndex(project_path)
    findings: list[Finding] = []
    for checker in get_checkers():
        checker(project_path, file_index, findings)
    return findings


def _write_and_scan(content: str, filename: str = "model_utils.py") -> list[Finding]:
    """Write content to a temp project and scan it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        (project / filename).write_text(content)
        return _run_checkers(project)


def _filter(findings: list[Finding], category: str) -> list[Finding]:
    return [f for f in findings if f.category == category]


class TestUnsafePickleDeserialization:
    def test_pickle_load_detected(self):
        findings = _write_and_scan("import pickle\ndata = pickle.load(open('model.pkl', 'rb'))")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_pickle_loads_detected(self):
        findings = _write_and_scan("import pickle\ndata = pickle.loads(raw_bytes)")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 1

    def test_marshal_load_detected(self):
        findings = _write_and_scan("import marshal\ndata = marshal.load(f)")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 1

    def test_dill_load_detected(self):
        findings = _write_and_scan("import dill\ndata = dill.load(f)")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 1

    def test_joblib_load_detected(self):
        findings = _write_and_scan("from joblib import load\nmodel = load('model.joblib')")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 1

    def test_safetensors_not_flagged(self):
        findings = _write_and_scan("from safetensors import load_file\nmodel = load_file('model.safetensors')")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 0

    def test_comment_not_flagged(self):
        findings = _write_and_scan("# pickle.load(open('model.pkl', 'rb'))")
        results = _filter(findings, "unsafe_deserialization")
        assert len(results) == 0


class TestUnsafeTorchLoad:
    def test_torch_load_without_weights_only(self):
        findings = _write_and_scan("import torch\nmodel = torch.load('checkpoint.pth')")
        results = _filter(findings, "unsafe_torch_load")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_torch_load_with_weights_only_safe(self):
        findings = _write_and_scan("import torch\nmodel = torch.load('checkpoint.pth', weights_only=True)")
        results = _filter(findings, "unsafe_torch_load")
        assert len(results) == 0

    def test_torch_jit_load_detected(self):
        findings = _write_and_scan("import torch\nmodel = torch.jit.load('model.pt')")
        results = _filter(findings, "unsafe_torch_load")
        assert len(results) == 1


class TestUnsafeKerasLoad:
    def test_keras_load_model_detected(self):
        findings = _write_and_scan("import tensorflow as tf\nmodel = tf.keras.models.load_model('model.keras')")
        results = _filter(findings, "unsafe_keras_load")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.WARNING

    def test_keras_lambda_layer_detected(self):
        findings = _write_and_scan("from keras.layers import Lambda\nlayer = Lambda(lambda x: x * 2)")
        results = _filter(findings, "keras_lambda_rce")
        assert len(results) == 1

    def test_keras_custom_objects_detected(self):
        findings = _write_and_scan("model = load_model('m.h5', custom_objects={'MyLayer': MyLayer})")
        results = _filter(findings, "keras_custom_objects")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.INFO


class TestHFTrustRemoteCode:
    def test_trust_remote_code_true_detected(self):
        findings = _write_and_scan(
            "from transformers import AutoModel\nmodel = AutoModel.from_pretrained('repo', trust_remote_code=True)"
        )
        results = _filter(findings, "hf_trust_remote_code")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_trust_remote_code_false_not_flagged(self):
        findings = _write_and_scan(
            "from transformers import AutoModel\nmodel = AutoModel.from_pretrained('repo', trust_remote_code=False)"
        )
        results = _filter(findings, "hf_trust_remote_code")
        assert len(results) == 0


class TestModelPathTraversal:
    def test_user_input_in_model_path(self):
        findings = _write_and_scan(
            "import torch\npath = request.args.get('model')\nmodel = torch.load(path)"
        )
        results = _filter(findings, "model_path_traversal")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.WARNING

    def test_safe_path_not_flagged(self):
        findings = _write_and_scan(
            "import torch\npath = safe_join(MODEL_DIR, request.args.get('model'))\nmodel = torch.load(path)"
        )
        results = _filter(findings, "model_path_traversal")
        assert len(results) == 0


class TestPickleReduceExploit:
    def test_reduce_with_exec_detected(self):
        content = """
class Evil:
    def __reduce__(self):
        return (exec, ("import os; os.system('id')",))
"""
        findings = _write_and_scan(content)
        results = _filter(findings, "pickle_reduce_exploit")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_reduce_without_exec_not_flagged(self):
        content = """
class Point:
    def __reduce__(self):
        return (self.__class__, (self.x, self.y))
"""
        findings = _write_and_scan(content)
        results = _filter(findings, "pickle_reduce_exploit")
        assert len(results) == 0


class TestUnsafeYamlLoad:
    def test_yaml_load_without_loader_detected(self):
        findings = _write_and_scan("import yaml\nconfig = yaml.load(data)")
        results = _filter(findings, "unsafe_yaml_load")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_yaml_load_with_safe_loader_not_flagged(self):
        findings = _write_and_scan("import yaml\nconfig = yaml.load(data, Loader=yaml.SafeLoader)")
        results = _filter(findings, "unsafe_yaml_load")
        assert len(results) == 0

    def test_yaml_safe_load_not_flagged(self):
        findings = _write_and_scan("import yaml\nconfig = yaml.safe_load(data)")
        results = _filter(findings, "unsafe_yaml_load")
        assert len(results) == 0


class TestOnnxUnsafeLoad:
    def test_onnx_load_from_user_input(self):
        findings = _write_and_scan(
            "import onnx\nmodel = onnx.load(request.args.get('model_file'))"
        )
        results = _filter(findings, "onnx_unsafe_load")
        assert len(results) == 1

    def test_onnx_load_from_safe_path(self):
        findings = _write_and_scan(
            "import onnx\nmodel = onnx.load(safe_join(MODEL_DIR, 'model.onnx'))"
        )
        results = _filter(findings, "onnx_unsafe_load")
        assert len(results) == 0


class TestNumpyUnsafeLoad:
    def test_numpy_load_allow_pickle_true(self):
        findings = _write_and_scan("import numpy as np\ndata = np.load('data.npy', allow_pickle=True)")
        results = _filter(findings, "numpy_unsafe_load")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.ERROR

    def test_numpy_load_npy_info(self):
        findings = _write_and_scan("import numpy as np\ndata = np.load('data.npy')")
        results = _filter(findings, "numpy_object_array")
        assert len(results) == 1
        assert results[0].severity == FindingSeverity.INFO


class TestPickleFilesInRepo:
    def test_pkl_file_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "model.pkl").write_bytes(b"\x80\x02\x00")
            findings = _run_checkers(project)
            results = _filter(findings, "pickle_file_in_repo")
            assert len(results) == 1
            assert results[0].severity == FindingSeverity.INFO

    def test_pt_file_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "checkpoint.pt").write_bytes(b"\x80\x02\x00")
            findings = _run_checkers(project)
            results = _filter(findings, "pickle_file_in_repo")
            assert len(results) == 1

    def test_safetensors_file_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / "model.safetensors").write_bytes(b"{}")
            findings = _run_checkers(project)
            results = _filter(findings, "pickle_file_in_repo")
            assert len(results) == 1  # .safetensors is in _PICKLE_EXT for scanning

    def test_test_fixture_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            test_dir = project / "tests" / "fixtures"
            test_dir.mkdir(parents=True)
            (test_dir / "sample.pkl").write_bytes(b"\x80\x02\x00")
            findings = _run_checkers(project)
            results = _filter(findings, "pickle_file_in_repo")
            assert len(results) == 0
