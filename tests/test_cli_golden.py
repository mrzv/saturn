import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def normalize_terminal_output(text):
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()).strip()


def run_saturn(fixture, tmp_path, output=None):
    if output is None:
        output = tmp_path / f"{fixture.name}.out.py"
    return run_saturn_command(["run", str(fixture), str(output), "--no-mpi"]), output


def run_saturn_command(args):
    env = os.environ.copy()
    env["COLUMNS"] = "80"
    env.setdefault("TERM", "xterm-256color")

    return subprocess.run(
        [sys.executable, "saturn.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


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


def test_cli_checkpoint_cache_skips_work_on_second_run(tmp_path):
    marker = tmp_path / "checkpoint.marker"
    source = tmp_path / "checkpoint.py"
    first = tmp_path / "checkpoint.first.py"
    second = tmp_path / "checkpoint.second.py"
    source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 40\n"
        "#chk>\n"
        "\n"
        "print(value + 2)\n"
    )

    first_result, _ = run_saturn(source, tmp_path, first)
    second_result, _ = run_saturn(first, tmp_path, second)

    assert first_result.returncode == 0, first_result.stderr
    assert second_result.returncode == 0, second_result.stderr
    assert marker.read_text() == "x"
    assert "Skipping to checkpoint" in second_result.stdout
    assert first.read_text().startswith("#saturn> external=checkpoint.first.zip\n")
    with zipfile.ZipFile(tmp_path / "checkpoint.first.zip") as zf:
        assert any(name.endswith(".chk") for name in zf.namelist())


def test_cli_variable_cache_skips_work_on_second_run(tmp_path):
    marker = tmp_path / "variables.marker"
    source = tmp_path / "variables.py"
    first = tmp_path / "variables.first.py"
    second = tmp_path / "variables.second.py"
    source.write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 41\n"
        "#var> value\n"
        "\n"
        "print(value + 1)\n"
    )

    first_result, _ = run_saturn(source, tmp_path, first)
    second_result, _ = run_saturn(first, tmp_path, second)

    assert first_result.returncode == 0, first_result.stderr
    assert second_result.returncode == 0, second_result.stderr
    assert marker.read_text() == "x"
    assert "loading" in second_result.stdout
    assert first.read_text().startswith("#saturn> external=variables.first.zip\n")
    with zipfile.ZipFile(tmp_path / "variables.first.zip") as zf:
        assert any(name.endswith(".var") for name in zf.namelist())
