"""Test bootstrap helpers for PySide6 import stability."""

# Preload the scientific stack before any test imports PySide6.
# On this environment, collecting Qt-heavy tests first can leave shiboken's
# import hook active while lmfit/dill later resolve ``_thread`` via six.moves.
# Importing the fit stack up front keeps the mixed GUI/core pytest runs stable.
import six.moves._thread  # noqa: F401
import numpy  # noqa: F401
import pandas  # noqa: F401
import matplotlib.pyplot  # noqa: F401
import dill  # noqa: F401
import lmfit  # noqa: F401
