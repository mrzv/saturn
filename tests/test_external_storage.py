import io
import json
import zipfile
from pathlib import Path

import pytest

from saturn_notebook import __main__ as cli
from saturn_notebook import cells, notebook


def payload_names(zf):
    return [name for name in zf.namelist() if name != notebook.ARCHIVE_MANIFEST]


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
    assert saved.startswith("#saturn> external=image.zip\n")
    assert "#o> png name=" in saved
    with zipfile.ZipFile(external) as zf:
        manifest = json.loads(zf.read(notebook.ARCHIVE_MANIFEST))
        names = payload_names(zf)
        assert manifest["kind"] == notebook.ARCHIVE_MANIFEST_KIND
        assert manifest["notebook"] == "image.py"
        assert manifest["notebook_path"] == str(outfn)
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


def test_notebook_save_drops_stale_external_metadata_without_external_content(tmp_path):
    outfn = tmp_path / "plain.py"
    saturn = cells.SaturnCell.create("plain.zip")
    code = cells.CodeCell()
    code.append("x = 1\n")
    nb = notebook.Notebook(name="plain.py")
    nb.add([saturn, code])
    nb.move_all_incoming()

    nb.save(str(outfn), "")

    assert outfn.read_text() == "x = 1\n"


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


def test_explicit_relative_external_path_resolves_next_to_output_notebook(tmp_path):
    outfn = tmp_path / "nested" / "image.py"

    external = cli.save_external_name(str(outfn), external="image.zip", inline=False)

    assert external == str(tmp_path / "nested" / "image.zip")


def test_parse_resolves_relative_external_archive_next_to_notebook(tmp_path):
    outfn = tmp_path / "image.py"
    external = cli.save_external_name(str(outfn), external="", inline=False)
    nb = make_notebook_with_png()
    nb.save(str(outfn), external)

    with outfn.open() as f:
        parsed = cells.parse(f, "", external_base=str(outfn.parent))

    outputs = [cell for cell in parsed if isinstance(cell, cells.OutputCell)]
    assert len(outputs) == 1
    assert any(item == b"png-bytes" for item in outputs[0].composite_)


def test_parse_malformed_external_archive_reports_warning(tmp_path):
    external = tmp_path / "not-a-zip.zip"
    external.write_text("not a zip")
    source = io.StringIO("#o> png name=missing.png\n")
    messages = []

    parsed = cells.parse(source, str(external), show_only=True, info=lambda *args, **kwargs: messages.append(args[0]))

    output = next(cell for cell in parsed if isinstance(cell, cells.OutputCell))
    assert any("not a valid zip" in message for message in messages)
    assert not any(item == b"png-bytes" for item in output.composite_)


def test_unsafe_archive_member_names_are_not_loaded(tmp_path):
    external = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr("../escape.png", b"png-bytes")
    source = io.StringIO("#o> png name=../escape.png\n")

    parsed = cells.parse(source, str(external))

    output = next(cell for cell in parsed if isinstance(cell, cells.OutputCell))
    assert not any(item == b"png-bytes" for item in output.composite_)


def test_explicit_absolute_external_path_is_preserved_in_metadata(tmp_path):
    outfn = tmp_path / "nested" / "image.py"
    outfn.parent.mkdir()
    external = tmp_path / "archives" / "image.zip"
    external.parent.mkdir()
    nb = make_notebook_with_png()

    nb.save(str(outfn), str(external))

    assert outfn.read_text().startswith(f"#saturn> external={external}\n")
    assert Path(external).exists()


def test_external_archive_write_failure_preserves_existing_files(tmp_path, monkeypatch):
    outfn = tmp_path / "image.py"
    external = tmp_path / "image.zip"
    outfn.write_text("old notebook\n")
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr(notebook.ARCHIVE_MANIFEST, json.dumps(notebook.archive_manifest(str(outfn))))
        zf.writestr("old.png", b"old-png")

    nb = make_notebook_with_png()
    original_save = cells.OutputCell.save

    def fail_after_zip_write(self, external_zip):
        original_save(self, external_zip)
        raise RuntimeError("simulated zip write failure")

    monkeypatch.setattr(cells.OutputCell, "save", fail_after_zip_write)

    with pytest.raises(RuntimeError, match="simulated zip write failure"):
        nb.save(str(outfn), str(external))

    assert outfn.read_text() == "old notebook\n"
    with zipfile.ZipFile(external) as zf:
        assert payload_names(zf) == ["old.png"]
        assert zf.read("old.png") == b"old-png"


def test_notebook_save_refuses_to_overwrite_unknown_external_archive(tmp_path):
    outfn = tmp_path / "image.py"
    external = tmp_path / "image.zip"
    outfn.write_text("old notebook\n")
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr("unrelated.txt", b"do not replace")

    nb = make_notebook_with_png()

    with pytest.raises(ValueError, match="without Saturn manifest"):
        nb.save(str(outfn), str(external))

    assert outfn.read_text() == "old notebook\n"
    with zipfile.ZipFile(external) as zf:
        assert zf.namelist() == ["unrelated.txt"]
        assert zf.read("unrelated.txt") == b"do not replace"


def test_notebook_save_allows_matching_saturn_archive_manifest(tmp_path):
    outfn = tmp_path / "image.py"
    external = tmp_path / "image.zip"
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr(notebook.ARCHIVE_MANIFEST, json.dumps(notebook.archive_manifest(str(outfn))))
        zf.writestr("old.png", b"old")

    nb = make_notebook_with_png()

    nb.save(str(outfn), str(external))

    with zipfile.ZipFile(external) as zf:
        assert notebook.ARCHIVE_MANIFEST in zf.namelist()
        assert "old.png" not in zf.namelist()
        assert len(payload_names(zf)) == 1


def test_notebook_save_refuses_to_overwrite_archive_for_different_notebook(tmp_path):
    outfn = tmp_path / "image.py"
    external = tmp_path / "image.zip"
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr(notebook.ARCHIVE_MANIFEST, json.dumps(notebook.archive_manifest(str(tmp_path / "other.py"))))

    nb = make_notebook_with_png()

    with pytest.raises(ValueError, match="other.py"):
        nb.save(str(outfn), str(external))


def test_notebook_save_refuses_to_overwrite_archive_for_same_basename_different_path(tmp_path):
    first = tmp_path / "first" / "image.py"
    second = tmp_path / "second" / "image.py"
    external = tmp_path / "shared.zip"
    first.parent.mkdir()
    second.parent.mkdir()
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr(notebook.ARCHIVE_MANIFEST, json.dumps(notebook.archive_manifest(str(first))))

    nb = make_notebook_with_png()

    with pytest.raises(ValueError, match=str(first)):
        nb.save(str(second), str(external))


def test_notebook_save_force_external_replaces_unknown_archive(tmp_path):
    outfn = tmp_path / "image.py"
    external = tmp_path / "image.zip"
    with zipfile.ZipFile(external, "w") as zf:
        zf.writestr("unrelated.txt", b"replace me")

    nb = make_notebook_with_png()

    nb.save(str(outfn), str(external), force_external=True)

    with zipfile.ZipFile(external) as zf:
        assert "unrelated.txt" not in zf.namelist()
        assert notebook.ARCHIVE_MANIFEST in zf.namelist()
        assert len(payload_names(zf)) == 1
