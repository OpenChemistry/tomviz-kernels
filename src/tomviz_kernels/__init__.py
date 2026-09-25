###############################################################################
# This source file is part of the tomviz-kernels project.
# It is released under the 3-Clause BSD License, see "LICENSE".
###############################################################################
"""tomviz-kernels: the operators / node kernels shared by the tomviz
desktop and web applications.

Every kernel is a pair of files in this directory: ``Name.py``, the
script, and ``Name.json``, its description (parameters, ports, and the
catalog fields ``path`` and ``tags``). The scripts are not meant to be
imported from this package: a host application reads them and runs them
through its pipeline (tomviz-pipeline, or the desktop's own runtime),
which provides the ``tomviz.*`` modules they import.

This module is stdlib only, and is the only module here that is not a
kernel: hosts scanning ``directory()`` skip names starting with ``_``."""

from pathlib import Path

__version__ = '3.2.0'


def directory() -> Path:
    """The directory holding the kernel ``.py`` / ``.json`` files."""
    return Path(__file__).resolve().parent


def names() -> list[str]:
    """The kernel names (the file stems), sorted."""
    return sorted(path.stem for path in directory().glob('*.json'))
