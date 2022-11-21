from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (FigureCanvasBase, FigureManagerBase)
from matplotlib.backends.backend_agg import FigureCanvasAgg

import io

figures = None

class SaturnFigureManager(FigureManagerBase):
    def show(self):
        with io.BytesIO() as buf:
            self.canvas.figure.savefig(buf, format='png')
            figures.append_png(buf.getvalue())

class SaturnCanvas(FigureCanvasAgg):
    manager_class = SaturnFigureManager

FigureCanvas  = SaturnCanvas
FigureManager = SaturnFigureManager

def show(*, block=None):
    for manager in Gcf.get_all_fig_managers():
        manager.show()
    Gcf.destroy_all()
