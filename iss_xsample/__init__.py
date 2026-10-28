try:
    from ._version import __version__
except ImportError:  # editable install before the first build, or a plain checkout
    __version__ = "0.0.0"
