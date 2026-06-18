import base64
import contextlib
import dill
import io
import zipfile
from pathlib import Path

from saturn_notebook import __main__ as cli
from saturn_notebook import cells


def run_notebook(infn, outfn, *, inline=False, clean=False):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        cli.run(str(infn), str(outfn), clean=clean, no_mpi=True, inline=inline)
    return stdout.getvalue()


def write_marker(path):
    Path(path).write_text("pwned")


class WriteMarkerOnLoad:
    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return write_marker, (self.path,)


def test_variable_cell_round_trips_semantically_with_external_archive(tmp_path):
    source = tmp_path / "variables.py"
    first = tmp_path / "variables.first.py"
    second = tmp_path / "variables.second.py"
    marker = tmp_path / "variables.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "print('expensive')\n"
        "value = 41\n"
        "#var> value\n"
        "\n"
        "print(value + 1)\n"
    )

    first_stdout = run_notebook(source, first)

    assert "expensive" in first_stdout
    assert "42" in first_stdout
    assert marker.read_text() == "x"
    first_text = first.read_text()
    assert "#saturn> external=" in first_text
    assert "#var> value" in first_text
    assert "#var> name=" in first_text
    external_name = tmp_path / "variables.first.zip"
    with zipfile.ZipFile(external_name) as zf:
        assert any(name.endswith(".var") for name in zf.namelist())

    second_stdout = run_notebook(first, second)

    assert "42" in second_stdout
    assert "loading" in second_stdout
    assert marker.read_text() == "x"


def test_checkpoint_cell_round_trips_semantically_with_external_archive(tmp_path):
    source = tmp_path / "checkpoint.py"
    first = tmp_path / "checkpoint.first.py"
    second = tmp_path / "checkpoint.second.py"
    marker = tmp_path / "checkpoint.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "print('before checkpoint')\n"
        "value = 40\n"
        "#chk>\n"
        "\n"
        "print(value + 2)\n"
    )

    first_stdout = run_notebook(source, first)

    assert "before checkpoint" in first_stdout
    assert "42" in first_stdout
    assert marker.read_text() == "x"
    first_text = first.read_text()
    assert "#saturn> external=" in first_text
    assert "#chk> name=" in first_text
    external_name = tmp_path / "checkpoint.first.zip"
    with zipfile.ZipFile(external_name) as zf:
        assert any(name.endswith(".chk") for name in zf.namelist())

    second_stdout = run_notebook(first, second)

    assert "42" in second_stdout
    assert "Skipping to checkpoint" in second_stdout
    assert marker.read_text() == "x"


def test_inline_variable_cache_remains_compatible(tmp_path):
    source = tmp_path / "variables.py"
    first = tmp_path / "variables.inline.py"
    second = tmp_path / "variables.second.py"
    marker = tmp_path / "variables.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 41\n"
        "#var> value\n"
        "\n"
        "print(value + 1)\n"
    )

    run_notebook(source, first, inline=True)

    first_text = first.read_text()
    assert "#saturn>" not in first_text
    assert "#var> name=" not in first_text
    assert "#var>{{{" in first_text

    second_stdout = run_notebook(first, second)

    assert "42" in second_stdout
    assert "loading" in second_stdout
    assert marker.read_text() == "x"


def test_inline_checkpoint_cache_remains_compatible(tmp_path):
    source = tmp_path / "checkpoint.py"
    first = tmp_path / "checkpoint.inline.py"
    second = tmp_path / "checkpoint.second.py"
    marker = tmp_path / "checkpoint.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 40\n"
        "#chk>\n"
        "\n"
        "print(value + 2)\n"
    )

    run_notebook(source, first, inline=True)

    first_text = first.read_text()
    assert "#saturn>" not in first_text
    assert "#chk> name=" not in first_text
    assert "#chk>{{{" in first_text

    second_stdout = run_notebook(first, second)

    assert "42" in second_stdout
    assert "Skipping to checkpoint" in second_stdout
    assert marker.read_text() == "x"


def test_clean_run_ignores_variable_cache(tmp_path):
    source = tmp_path / "variables.py"
    first = tmp_path / "variables.first.py"
    second = tmp_path / "variables.second.py"
    marker = tmp_path / "variables.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 41\n"
        "#var> value\n"
        "\n"
        "print(value + 1)\n"
    )

    run_notebook(source, first)
    second_stdout = run_notebook(first, second, clean=True)

    assert "loading" not in second_stdout
    assert "42" in second_stdout
    assert marker.read_text() == "xx"


def test_variable_cache_includes_target_expression(tmp_path):
    source = tmp_path / "variables.py"
    first = tmp_path / "variables.first.py"
    second = tmp_path / "variables.second.py"
    marker = tmp_path / "variables.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 41\n"
        "other = 99\n"
        "#var> value\n"
        "\n"
        "print(value + 1)\n"
    )

    run_notebook(source, first)
    first.write_text(first.read_text().replace("#var> value\n", "#var> other\n").replace("print(value + 1)", "print(other)"))
    second_stdout = run_notebook(first, second)

    assert "loading" not in second_stdout
    assert "99" in second_stdout
    assert marker.read_text() == "xx"


def test_code_hash_includes_cell_boundaries(tmp_path):
    source = tmp_path / "checkpoint.py"
    first = tmp_path / "checkpoint.first.py"
    second = tmp_path / "checkpoint.second.py"
    source.write_text("x = 1\n#---#\n0\n#chk>\n\nprint(x)\n")

    run_notebook(source, first)
    cached_checkpoint = first.read_text()[first.read_text().index("#chk>"):]
    first.write_text("x = 10\n" + cached_checkpoint)
    second_stdout = run_notebook(first, second)

    assert "Skipping to checkpoint" not in second_stdout
    assert "10" in second_stdout


def test_checkpoint_scan_skips_empty_checkpoint_before_later_valid_checkpoint(tmp_path):
    source = tmp_path / "checkpoint.py"
    first = tmp_path / "checkpoint.first.py"
    second = tmp_path / "checkpoint.second.py"
    marker = tmp_path / "checkpoint.marker"
    source.write_text(
        f"from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text(Path({str(marker)!r}).read_text() + 'x' if Path({str(marker)!r}).exists() else 'x')\n"
        "value = 40\n"
        "#chk>\n"
        "value += 2\n"
        "#chk>\n"
        "print(value)\n"
    )

    run_notebook(source, first)
    lines = first.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("#chk> name="):
            lines[i] = "#chk>\n"
            break
    first.write_text("".join(lines))
    second_stdout = run_notebook(first, second)

    assert "Skipping to checkpoint" in second_stdout
    assert "42" in second_stdout
    assert marker.read_text() == "x"


def test_rehash_rewrites_checkpoint_hash_without_deserializing_payload(tmp_path):
    marker = tmp_path / "rehash.marker"
    source = tmp_path / "malicious.py"
    output = tmp_path / "rehashed.py"
    payload = io.BytesIO()
    dill.dump(WriteMarkerOnLoad(str(marker)), payload)
    dill.dump({"value": 42}, payload)
    encoded = base64.b64encode(payload.getvalue()).decode("ascii")
    source.write_text(
        "value = 42\n"
        + "".join(f"#chk>{line}\n" for line in cells.chunk(encoded, 80, markers=True))
        + "\nprint(value)\n"
    )

    cli.rehash(str(source), str(output), inline=True)

    assert output.exists()
    assert not marker.exists()
