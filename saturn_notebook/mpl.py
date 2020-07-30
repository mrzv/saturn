from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (_Backend, FigureCanvasBase, FigureManagerBase)
from matplotlib.backends.backend_agg import FigureCanvasAgg

import io

figures = None

class SaturnFigureManager(FigureManagerBase):
    def show(self):
        with io.BytesIO() as buf:
            self.canvas.figure.savefig(buf, format='png')
            figures.append_png(buf.getvalue())

@_Backend.export
class SaturnBackend(_Backend):
    FigureCanvas  = FigureCanvasAgg
    FigureManager = SaturnFigureManager

    def show(*args, **kwargs):
        _Backend.show(*args, **kwargs)
        Gcf.destroy_all()
