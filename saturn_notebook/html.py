from . import cells as c


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


def render(cells, html, katex=False):
    close_html = False
    if type(html) is str:
        f_html = open(html, 'w')
        close_html = True
    else:
        f_html = html

    try:
        f_html.write('<!DOCTYPE html>\n')
        f_html.write('<html>\n')
        f_html.write('<head>\n')
        f_html.write('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/light.css">\n')
        f_html.write('<style> .muted { color: gray; } </style>')
        if katex:
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
