from    rich.theme   import Theme
from    rich.style   import Style

theme = Theme({
    "variables":    Style.parse("yellow"),
    "warn":         Style.parse("yellow"),
    "affirm":       Style.parse("green"),
    "error":        Style.parse("red"),
    "cell-name":    Style.parse("yellow"),
})
