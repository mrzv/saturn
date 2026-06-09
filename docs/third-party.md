# Third-Party Notices

Saturn includes the following third-party assets in source and wheel distributions.

## KaTeX

Saturn vendors selected browser assets from KaTeX 0.16.3 for offline standalone HTML math rendering.

- Source: https://github.com/KaTeX/KaTeX/tree/v0.16.3
- License: MIT
- Packaged notice: `saturn_notebook/assets/katex/NOTICE.md`
- Packaged license: `saturn_notebook/assets/katex/LICENSE`

These assets are embedded into generated HTML only when `--standalone --katex` is used and markdown cells contain math delimiters.
