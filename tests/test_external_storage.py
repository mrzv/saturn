import zipfile

import pytest

from saturn_notebook import __main__ as cli
from saturn_notebook import cells, notebook


def make_notebook_with_png():
    output = cells.OutputCell()
    output.composite_.append_png(b"png-bytes")

    nb = notebook.Notebook(name="image.py")
    nb.add([output])
    nb.move_all_incoming()
    return nb


def test_notebook_save_externalizes_binary_content_by_default(tmp_path):
    outfn = tmp_path / "image.py"
    external = cli.save_external_name(str(outfn), external="", inline=False)
    nb = make_notebook_with_png()

    nb.save(str(outfn), external)

    saved = outfn.read_text()
    assert saved.startswith(f"#saturn> external={external}\n")
    assert "#o> png name=" in saved
    with zipfile.ZipFile(external) as zf:
        names = zf.namelist()
        assert len(names) == 1
        assert names[0].endswith(".png")
        assert zf.read(names[0]) == b"png-bytes"


def test_notebook_save_does_not_create_external_archive_for_plain_text(tmp_path):
    outfn = tmp_path / "plain.py"
    external = cli.save_external_name(str(outfn), external="", inline=False)
    code = cells.CodeCell()
    code.append("x = 1\n")
    nb = notebook.Notebook(name="plain.py")
    nb.add([code])
    nb.move_all_incoming()

    nb.save(str(outfn), external)

    assert outfn.read_text() == "x = 1\n"
    assert not (tmp_path / "plain.zip").exists()


def test_notebook_save_inline_embeds_binary_content(tmp_path):
    outfn = tmp_path / "image.py"
    nb = make_notebook_with_png()

    nb.save(str(outfn), cli.save_external_name(str(outfn), external="", inline=True), inline=True)

    saved = outfn.read_text()
    assert "#saturn>" not in saved
    assert "#o> png{{{" in saved
    assert not (tmp_path / "image.zip").exists()


def test_external_and_inline_flags_conflict(tmp_path):
    with pytest.raises(ValueError, match="--external and --inline"):
        cli.save_external_name(str(tmp_path / "image.py"), external="image.zip", inline=True)
