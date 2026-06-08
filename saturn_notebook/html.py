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


standalone_katex_preamble = r"""
<style>
.math-note {
    border-left: 0.25rem solid #d0d7de;
    margin: 1rem 0;
    padding: 0.5rem 0 0.5rem 1rem;
}
</style>
<script>
    document.addEventListener("DOMContentLoaded", function() {
        var note = document.createElement("p");
        note.className = "math-note";
        note.textContent = "Standalone output keeps TeX math delimiters in the document without loading external KaTeX assets.";
        document.body.insertBefore(note, document.body.firstChild);
    });
</script>
"""


def render(cells, html, katex=False, standalone=False):
    close_html = False
    if isinstance(html, str):
        f_html = open(html, 'w')
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
        if katex and standalone:
            f_html.write(standalone_katex_preamble)
        elif katex:
            f_html.write(katex_preamble)
        f_html.write('<style>\n')
        f_html.write(c.HtmlFormatter().get_style_defs('.highlight'))
        f_html.write('</style>\n')
        f_html.write('</head>\n')
        f_html.write('<body>\n')

        for cell in cells:
            if cell.display():
                cell.show_html(f_html)

        f_html.write('</body>\n')
        f_html.write('</html>\n')
    finally:
        if close_html:
            f_html.close()
