import base64
from functools import lru_cache
from importlib import resources
import re
from typing import Any, Iterable, TextIO, Union

from . import cells as c


standalone_css = """
body {
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
    color: #1f2933;
    background: #fff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.55;
}
pre {
    overflow-x: auto;
    padding: 1rem;
    background: #f6f8fa;
    border-radius: 0.35rem;
}
code, pre {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
img {
    max-width: 100%;
}
.muted {
    color: gray;
}
.math-note {
    color: #57606a;
    font-size: 0.9rem;
}
"""


katex_preamble = r"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/katex.min.css" integrity="sha384-Juol1FqnotbkyZUT5Z7gUPjQ9gzlwCENvUZTpQBAPxtusdwFLRy382PSDx5UUJ4/" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/katex.min.js" integrity="sha384-97gW6UIJxnlKemYavrqDHSX3SiygeOwIZhwyOKRfSaf0JWKRVj9hLASHgFTzT+0O" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/contrib/auto-render.min.js" integrity="sha384-+VBxd3r6XgURycqtZ117nYw44OOcIax56Z4dCRWbxyPt0Koah1uHoK0o4+/RRE05" crossorigin="anonymous"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        renderMathInElement(document.body, {
          // customised options
          // auto-render specific keys, e.g.:
          delimiters: [
              {left: '$$', right: '$$', display: true},
              {left: '$', right: '$', display: false},
              {left: '\\(', right: '\\)', display: false},
              {left: '\\[', right: '\\]', display: true}
          ],
          // rendering keys, e.g.:
          throwOnError : false
        });
    });
</script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.3/dist/contrib/copy-tex.min.js" integrity="sha384-ww/583aHhxWkz5DEVn6OKtNiIaLi2iBRNZXfJRiY1Ai7tnJ9UXpEsyvOITVpTl4A" crossorigin="anonymous"></script>
"""


render_math_script = r"""
<script>
    document.addEventListener("DOMContentLoaded", function() {
        renderMathInElement(document.body, {
          delimiters: [
              {left: '$$', right: '$$', display: true},
              {left: '$', right: '$', display: false},
              {left: '\\(', right: '\\)', display: false},
              {left: '\\[', right: '\\]', display: true}
          ],
          throwOnError : false
        });
    });
</script>
"""


math_delimiters = re.compile(r"\$\$|(?<!\\)\$(?!\s)|\\\(|\\\[")


def has_math(cells: Iterable[Any]) -> bool:
    for cell in cells:
        if isinstance(cell, c.MarkdownCell) and math_delimiters.search(cell.lines()):
            return True
    return False


def resource_text(package: str, name: str) -> str:
    if hasattr(resources, 'files'):
        return (resources.files(package) / name).read_text()
    return resources.read_text(package, name)


def resource_binary(package: str, name: str) -> bytes:
    if hasattr(resources, 'files'):
        return (resources.files(package) / name).read_bytes()
    return resources.read_binary(package, name)


@lru_cache(maxsize=1)
def standalone_katex_css() -> str:
    css = resource_text('saturn_notebook.assets.katex', 'katex.min.css')

    def embed_woff2(match: re.Match) -> str:
        name = match.group(1)
        font = resource_binary('saturn_notebook.assets.katex.fonts', name)
        encoded = base64.b64encode(font).decode('ascii')
        return f'src:url(data:font/woff2;base64,{encoded}) format("woff2")'

    return re.sub(
        r'src:url\(fonts/([^)]*?\.woff2)\) format\("woff2"\),url\(fonts/[^)]*?\.woff\) format\("woff"\),url\(fonts/[^)]*?\.ttf\) format\("truetype"\)',
        embed_woff2,
        css,
    )


@lru_cache(maxsize=1)
def standalone_katex_preamble() -> str:
    katex_js = resource_text('saturn_notebook.assets.katex', 'katex.min.js')
    auto_render_js = resource_text('saturn_notebook.assets.katex', 'auto-render.min.js')
    copy_tex_js = resource_text('saturn_notebook.assets.katex', 'copy-tex.min.js')
    return (
        '<style>\n'
        + standalone_katex_css()
        + '\n</style>\n'
        + '<script>\n'
        + katex_js
        + '\n</script>\n'
        + '<script>\n'
        + auto_render_js
        + '\n</script>\n'
        + '<script>\n'
        + copy_tex_js
        + '\n</script>\n'
        + render_math_script
    )


def render(cells: Iterable[Any], html: Union[str, TextIO], katex: bool = False, standalone: bool = False) -> None:
    cell_list = list(cells)
    include_katex = katex and has_math(cell_list)

    close_html = False
    if isinstance(html, str):
        f_html: TextIO = open(html, 'w')
        close_html = True
    else:
        f_html = html

    try:
        f_html.write('<!DOCTYPE html>\n')
        f_html.write('<html>\n')
        f_html.write('<head>\n')
        if standalone:
            f_html.write('<style>\n')
            f_html.write(standalone_css)
            f_html.write('</style>\n')
        else:
            f_html.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/light.css">\n')
            f_html.write('<style> .muted { color: gray; } </style>')
        if include_katex and standalone:
            f_html.write(standalone_katex_preamble())
        elif include_katex:
            f_html.write(katex_preamble)
        f_html.write('<style>\n')
        f_html.write(c.HtmlFormatter().get_style_defs('.highlight'))
        f_html.write('</style>\n')
        f_html.write('</head>\n')
        f_html.write('<body>\n')

        for cell in cell_list:
            if cell.display():
                cell.show_html(f_html)

        f_html.write('</body>\n')
        f_html.write('</html>\n')
    finally:
        if close_html:
            f_html.close()
