"""SqlToViz alpha: deterministic recommendations, no SQL execution."""
from .core import recommend
from .engine import Engine, ModelError
from .features import FeatureError, extract as extract_features
from .adapters import to_echarts, to_vegalite, to_plotly
from .statistics import mad_outliers, temporal_shifts, pareto, pearson
__version__ = "0.1.0a1"
__all__ = ["Engine","ModelError","FeatureError","extract_features","recommend","to_echarts","to_vegalite","to_plotly","mad_outliers","temporal_shifts","pareto","pearson"]
