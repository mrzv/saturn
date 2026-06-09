# KaTeX Assets

Saturn vendors selected browser assets from KaTeX 0.16.3 for offline standalone HTML math rendering.

- Project: KaTeX
- Version: 0.16.3
- Source: https://github.com/KaTeX/KaTeX/tree/v0.16.3
- License: MIT
- Copyright: Copyright (c) 2013-2020 Khan Academy and other contributors

Vendored files:

- `katex.min.css`
- `katex.min.js`
- `auto-render.min.js`
- `copy-tex.min.js`
- `fonts/*.woff2`

Saturn embeds these assets only for `--standalone --katex` HTML output when markdown cells contain math delimiters.
