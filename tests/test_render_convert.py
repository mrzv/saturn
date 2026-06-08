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
