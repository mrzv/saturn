import contextlib
import io
import zipfile

from saturn_notebook import __main__ as cli


def run_notebook(infn, outfn, *, inline=False):
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        cli.run(str(infn), str(outfn), no_mpi=True, inline=inline)
    return stdout.getvalue()


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
