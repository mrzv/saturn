import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def normalize_terminal_output(text):
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()).strip()


def run_saturn(fixture, tmp_path):
    output = tmp_path / f"{fixture.name}.out.py"
    env = os.environ.copy()
    env["COLUMNS"] = "80"
    env.setdefault("TERM", "xterm-256color")

    return subprocess.run(
        [sys.executable, "saturn.py", "run", str(fixture), str(output), "--no-mpi"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ), output


def assert_fixture_matches(fixture_name, tmp_path, *, exact_notebook=True):
    fixture = ROOT / "tests" / fixture_name
    result, output = run_saturn(fixture, tmp_path)

    assert result.returncode == 0, result.stderr
    if exact_notebook:
        assert output.read_text() == fixture.with_suffix(fixture.suffix + ".expected").read_text()
    assert normalize_terminal_output(result.stdout) == normalize_terminal_output(
        fixture.with_suffix(fixture.suffix + ".expected-out").read_text()
    )
    return output.read_text()


def test_cli_runs_blank_lines_fixture(tmp_path):
    assert_fixture_matches("blank-lines.py", tmp_path)


def test_cli_preserves_system_exit_fixture(tmp_path):
    output = assert_fixture_matches("test-sys-exit.py", tmp_path, exact_notebook=False)

    assert 'print("Hello")' in output
    assert "#o> Hello" in output
    assert "sys.exit(0)" in output
    assert 'print("Past the end")' in output
