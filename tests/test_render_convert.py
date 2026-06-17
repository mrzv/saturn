import io

import nbformat

from saturn_notebook import cells, convert, html


def test_html_render_writes_document_with_displayed_cells():
    cell = cells.MarkdownCell()
    cell.lines_ = [" Hello\n"]
    output = io.StringIO()

    html.render([cell], output)

    rendered = output.getvalue()
    assert rendered.startswith("<!DOCTYPE html>")
    assert "<body>" in rendered
    assert "Hello" in rendered
    assert rendered.endswith("</html>\n")


def test_html_render_handles_empty_markdown_cell():
    parsed = cells.parse(io.StringIO("#m>"), "")
    output = io.StringIO()

    html.render(parsed, output)

    assert output.getvalue().endswith("</html>\n")


def test_html_render_handles_output_warning_renderables():
    parsed = cells.parse(io.StringIO("#o> png name=../escape.png\n"), "")
    output = io.StringIO()

    html.render(parsed, output)

    rendered = output.getvalue()
    assert "unsafe image archive name" in rendered
    assert rendered.endswith("</html>\n")


def test_html_render_can_inline_standalone_css():
    output = io.StringIO()

    html.render([], output, standalone=True)

    rendered = output.getvalue()
    assert "cdn.jsdelivr.net" not in rendered
    assert "font-family" in rendered


def test_html_render_keeps_standalone_katex_offline():
    cell = cells.MarkdownCell()
    cell.lines_ = [" Euler: $e^{i\\pi} + 1 = 0$\n"]
    output = io.StringIO()

    html.render([cell], output, katex=True, standalone=True)

    rendered = output.getvalue()
    assert "cdn.jsdelivr.net" not in rendered
    assert "renderMathInElement" in rendered
    assert "data:font/woff2;base64" in rendered


def test_html_render_skips_standalone_katex_when_no_math():
    cell = cells.MarkdownCell()
    cell.lines_ = [" No math here.\n"]
    output = io.StringIO()

    html.render([cell], output, katex=True, standalone=True)

    rendered = output.getvalue()
    assert "cdn.jsdelivr.net" not in rendered
    assert "renderMathInElement" not in rendered
    assert "data:font/woff2;base64" not in rendered


def test_html_render_uses_cdn_katex_for_non_standalone_math():
    cell = cells.MarkdownCell()
    cell.lines_ = [" Euler: $e^{i\\pi} + 1 = 0$\n"]
    output = io.StringIO()

    html.render([cell], output, katex=True)

    rendered = output.getvalue()
    assert "cdn.jsdelivr.net/npm/katex" in rendered
    assert "renderMathInElement" in rendered


def test_convert_from_jupyter_preserves_markdown_code_and_outputs():
    jnb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell("# Heading"),
            nbformat.v4.new_code_cell(
                "x = 1\nx",
                outputs=[nbformat.v4.new_output("execute_result", data={"text/plain": "1"}, execution_count=1)],
            ),
        ]
    )

    converted = convert.from_jupyter(jnb, info=lambda *args, **kwargs: None)

    assert isinstance(converted[0], cells.CodeCell)
    assert any(isinstance(cell, cells.MarkdownCell) for cell in converted)
    assert any(isinstance(cell, cells.OutputCell) for cell in converted)
