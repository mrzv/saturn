from typing import Any, Callable, List

from . import cells as c


def from_jupyter(jnb: Any, info: Callable[..., None]) -> List[c.Cell]:
    header = c.CodeCell()
    header.lines_ = ['# vim: ft=python foldmethod=marker foldlevel=0\n']
    cells: List[c.Cell] = [header]

    for jcell in jnb.cells:
        if jcell['cell_type'] == 'markdown':
            cell = c.MarkdownCell()
            cell.lines_ = [' ' + line + '\n' if len(line) else '\n' for line in jcell['source'].split('\n')]
            if not isinstance(cells[-1], c.Blanks):
                cells.append(c.Blanks.create(1))
            cells.append(cell)
            cells.append(c.Blanks.create(1))
        elif jcell['cell_type'] == 'code':
            if isinstance(cells[-1], c.CodeCell):
                cells.append(c.Blanks.create(1))
                cells.append(c.BreakCell.create())
                cells.append(c.Blanks.create(1))
            code_cell = c.CodeCell()
            code_cell.lines_ = [line + '\n' for line in jcell['source'].split('\n')]
            cells.append(code_cell)

            for out in jcell['outputs']:
                if out['output_type'] == 'stream':
                    output_cell = c.OutputCell.from_string(out['text'])
                    cells.append(output_cell)
                elif out['output_type'] in ['display_data', 'execute_result']:
                    if 'image/png' in out['data']:
                        output_cell = c.OutputCell()
                        png_content = out['data']['image/png']
                        output_cell.composite_.append_png(c.base64.b64decode(png_content))
                        cells.append(output_cell)
                    elif 'text/plain' in out['data']:
                        output_cell = c.OutputCell.from_string(out['data']['text/plain'])
                        cells.append(output_cell)
                    else:
                        info('Unrecognized data type', style="magenta")
                elif out['output_type'] == 'error':
                    traceback = out.get('traceback')
                    if traceback:
                        text = '\n'.join(traceback) + '\n'
                    else:
                        text = f"{out.get('ename', 'Error')}: {out.get('evalue', '')}\n"
                    output_cell = c.OutputCell.from_string(text)
                    cells.append(output_cell)
                else:
                    info('Unrecognized output type', style="magenta")
        else:
            info('Unrecognized cell type', style="magenta")

    return cells
