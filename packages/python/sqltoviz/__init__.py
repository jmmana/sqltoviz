"""SqlToViz alpha: deterministic recommendations, no SQL execution."""
from .core import recommend
from .adapters import to_echarts, to_vegalite, to_plotly
from .statistics import mad_outliers, temporal_shifts, pareto, pearson
__version__ = "0.1.0a1"
__all__ = ["recommend","to_echarts","to_vegalite","to_plotly","mad_outliers","temporal_shifts","pareto","pearson"]
