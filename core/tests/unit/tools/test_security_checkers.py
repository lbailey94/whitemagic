"""Tests for Phase 1 security checkers — Solidity advanced, Python security, web vulns."""
import tempfile
from pathlib import Path

import pytest

from whitemagic.tools.strata.checkers import get_checkers
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding


def _run(sol_content: str, checker_name: str) -> list[Finding]:
    checker = None
    for c in get_checkers():
        if c.__name__ == checker_name:
            checker = c
            break
    if checker is None:
        pytest.fail(f"Checker {checker_name} not registered")
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        (project / "Test.sol").write_text(sol_content)
        fi = FileIndex(project)
        findings: list[Finding] = []
        checker(project, fi, findings)
        return findings


def _run_py(py_content: str, checker_name: str, filename: str = "app.py") -> list[Finding]:
    checker = None
    for c in get_checkers():
        if c.__name__ == checker_name:
            checker = c
            break
    if checker is None:
        pytest.fail(f"Checker {checker_name} not registered")
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        (project / filename).write_text(py_content)
        fi = FileIndex(project)
        findings: list[Finding] = []
        checker(project, fi, findings)
        return findings


class TestCheckerRegistration:
    @pytest.mark.parametrize("name", [
        "check_solidity_access_control",
        "check_solidity_oracle_manipulation",
        "check_solidity_unchecked_external",
        "check_solidity_arbitrary_transfer",
        "check_solidity_reentrancy_patterns",
        "check_python_secrets",
        "check_python_sqli",
        "check_python_path_traversal",
        "check_python_command_injection",
        "check_python_ssrf",
        "check_slither",
        "check_xss",
        "check_open_redirect",
        "check_csrf",
        "check_idor",
    ])
    def test_registered(self, name):
        for c in get_checkers():
            if c.__name__ == name:
                return
        pytest.fail(f"{name} not registered")


class TestSolidityAccessControl:
    def test_missing_access_control(self):
        sol = '''pragma solidity ^0.8.0;
contract Token {
    function mint(address to, uint256 amount) external {
        _balances[to] += amount;
    }
}'''
        f = _run(sol, "check_solidity_access_control")
        assert any(x.category == "sol_missing_access_control" for x in f)

    def test_has_access_control_no_finding(self):
        sol = '''pragma solidity ^0.8.0;
contract Token {
    address owner;
    modifier onlyOwner() { require(msg.sender == owner); _; }
    function mint(address to, uint256 amount) external onlyOwner {
        _balances[to] += amount;
    }
}'''
        f = _run(sol, "check_solidity_access_control")
        assert not any(x.category == "sol_missing_access_control" for x in f)


class TestSolidityOracle:
    def test_spot_price_detected(self):
        sol = '''pragma solidity ^0.8.0;
contract Oracle {
    function getPrice() public view returns (uint256) {
        (uint112 reserve0, uint112 reserve1, ) = IUniswapV3Pool(pool).getReserves();
        return reserve0;
    }
}'''
        f = _run(sol, "check_solidity_oracle_manipulation")
        assert any(x.category == "sol_spot_price_oracle" for x in f)


class TestSolidityUncheckedERC20:
    def test_unchecked_transfer_from(self):
        sol = '''pragma solidity ^0.8.0;
contract Vault {
    function deposit(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
    }
}'''
        f = _run(sol, "check_solidity_unchecked_external")
        assert any(x.category == "sol_unchecked_erc20" for x in f)


class TestSolidityArbitraryTransfer:
    def test_transfer_to_msg_sender(self):
        sol = '''pragma solidity ^0.8.0;
contract Faucet {
    function drip() external {
        payable(msg.sender).transfer(1 ether);
    }
}'''
        f = _run(sol, "check_solidity_arbitrary_transfer")
        assert any(x.category == "sol_arbitrary_transfer" for x in f)


class TestSolidityCEIViolation:
    def test_state_after_call(self):
        sol = '''pragma solidity ^0.8.0;
contract Vulnerable {
    mapping(address => uint256) public balances;
    function withdraw(uint256 amount) external {
        (bool ok, ) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }
}'''
        f = _run(sol, "check_solidity_reentrancy_patterns")
        assert any(x.category == "sol_cei_violation" for x in f)

    def test_safe_with_guard(self):
        sol = '''pragma solidity ^0.8.0;
import "@openzeppelin/ReentrancyGuard.sol";
contract Safe is ReentrancyGuard {
    mapping(address => uint256) public balances;
    function withdraw(uint256 amount) external nonReentrant {
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
    }
}'''
        f = _run(sol, "check_solidity_reentrancy_patterns")
        assert not any(x.category == "sol_cei_violation" for x in f)


class TestPythonSecrets:
    def test_hardcoded_api_key(self):
        py = 'api_key = "sk-1234567890abcdefghij1234567890abcdefghij"'
        f = _run_py(py, "check_python_secrets")
        assert any(x.category == "hardcoded_secret" for x in f)

    def test_env_var_no_finding(self):
        py = 'api_key = os.getenv("API_KEY")'
        f = _run_py(py, "check_python_secrets")
        assert not any(x.category == "hardcoded_secret" for x in f)

    def test_github_token(self):
        py = 'token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz1234"'
        f = _run_py(py, "check_python_secrets")
        assert any(x.category == "hardcoded_secret" for x in f)


class TestPythonSQLi:
    def test_fstring_sqli(self):
        py = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        f = _run_py(py, "check_python_sqli")
        assert any(x.category == "py_sql_injection" for x in f)

    def test_parameterized_no_finding(self):
        py = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
        f = _run_py(py, "check_python_sqli")
        assert not any(x.category == "py_sql_injection" for x in f)


class TestPythonPathTraversal:
    def test_user_input_in_open(self):
        py = 'data = open(request.GET["file"]).read()'
        f = _run_py(py, "check_python_path_traversal")
        assert any(x.category == "py_path_traversal" for x in f)

    def test_safe_path_no_finding(self):
        py = 'data = open(safe_join(BASE_DIR, filename)).read()'
        f = _run_py(py, "check_python_path_traversal")
        assert not any(x.category == "py_path_traversal" for x in f)


class TestPythonCommandInjection:
    def test_shell_true_with_input(self):
        py = 'subprocess.run(f"ls {request.GET[\'dir\']}", shell=True)'
        f = _run_py(py, "check_python_command_injection")
        assert any(x.category == "py_command_injection" for x in f)

    def test_shell_false_no_finding(self):
        py = 'subprocess.run(["ls", directory], shell=False)'
        f = _run_py(py, "check_python_command_injection")
        assert not any(x.category == "py_command_injection" for x in f)


class TestPythonSSRF:
    def test_user_url_in_requests(self):
        py = 'requests.get(request.GET["url"])'
        f = _run_py(py, "check_python_ssrf")
        assert any(x.category == "py_ssrf" for x in f)

    def test_static_url_no_finding(self):
        py = 'requests.get("https://api.example.com/data")'
        f = _run_py(py, "check_python_ssrf")
        assert not any(x.category == "py_ssrf" for x in f)


class TestWebXSS:
    def test_innerhtml_with_input(self):
        js = 'element.innerHTML = request.query["html"]'
        f = _run_py(js, "check_xss", "app.js")
        assert any(x.category == "web_xss_innerhtml" for x in f)

    def test_dangerously_set_inner_html(self):
        jsx = 'return <div dangerouslySetInnerHTML={{__html: props.content}} />'
        f = _run_py(jsx, "check_xss", "App.tsx")
        assert any(x.category == "web_xss_react" for x in f)


class TestWebOpenRedirect:
    def test_redirect_with_user_input(self):
        py = 'return redirect(request.GET["next"])'
        f = _run_py(py, "check_open_redirect")
        assert any(x.category == "web_open_redirect" for x in f)

    def test_static_redirect_no_finding(self):
        py = 'return redirect("/dashboard")'
        f = _run_py(py, "check_open_redirect")
        assert not any(x.category == "web_open_redirect" for x in f)


class TestWebIDOR:
    def test_idor_detected(self):
        py = 'obj = MyModel.objects.get(id=request.GET["id"])'
        f = _run_py(py, "check_idor")
        assert any(x.category == "web_idor" for x in f)

    def test_with_ownership_no_finding(self):
        py = 'obj = MyModel.objects.get(id=request.GET["id"], owner=request.user)'
        f = _run_py(py, "check_idor")
        assert not any(x.category == "web_idor" for x in f)
