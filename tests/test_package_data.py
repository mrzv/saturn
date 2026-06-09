import pkgutil


def test_katex_license_and_notice_are_packaged():
    license_text = pkgutil.get_data("saturn_notebook.assets.katex", "LICENSE")
    notice_text = pkgutil.get_data("saturn_notebook.assets.katex", "NOTICE.md")

    assert license_text is not None
    assert notice_text is not None
    assert b"The MIT License" in license_text
    assert b"KaTeX 0.16.3" in notice_text
