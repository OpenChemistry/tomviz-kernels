# tomviz-kernels

The operators / node kernels shared by the [tomviz](https://tomviz.org)
desktop application and its web version, tomviz-web. Both applications
depend on this package, so a fix or a new kernel lands in one place.

## Layout

Every kernel is a pair of files in `src/tomviz_kernels/`:

- `Name.py`, the script;
- `Name.json`, its description: `name`, `label`, `description`,
  `parameters`, ports, and the catalog fields `path` and `tags`.

Two flavors coexist:

- **v1 operators** (most of them): a module-level `transform(dataset, ...)`
  function or a `tomviz.operators.Operator` subclass; the description has
  no `schemaVersion` and may set `inputType` / `outputType`.
- **Schema-v2 kernels**: `"schemaVersion": 2`, `inputs` / `outputs` port
  lists, and a single `tomviz.nodes.TransformNode` or `SourceNode`
  subclass (a source when there are no `inputs`).

Converting the v1 operators to schema v2 is planned, but not done yet.

The scripts are not imported from this package. A host application reads
them and runs them through its pipeline, which provides the `tomviz.*`
modules they import: the desktop's own `tomviz` package, or
[tomviz-pipeline](https://github.com/OpenChemistry/tomviz-pipeline)'s
aliases for `tomviz.operators`, `tomviz.nodes`, `tomviz.utils` and
`tomviz.dataset`. The ITK kernels also import `tomviz.itkutils`, which
only the desktop provides today.

### Catalog fields

Each description has `path` and `tags`:

```json
"path": ["Data Transforms", "Filters & Smoothing"],
"tags": ["gaussian", "blur", "smoothing", "filter", "denoise"],
```

`path` places the kernel in the web catalog's tree and `tags` feed its
search. The desktop builds its menus in C++ and ignores both.

### Dependencies

The package declares no runtime dependencies. The host provides NumPy,
SciPy and tomviz-pipeline. Some kernels need more, imported when they
run: `itk`, `tomopy`, `pyfftw`, `pystackreg`, `scikit-image`, `bm3d`, and
for the SAM kernels `torch`, `sam2` / `sam3` (external environments
only).

## Use

```python
import tomviz_kernels

tomviz_kernels.directory()  # Path of the directory holding the files
tomviz_kernels.names()      # ['AddConstant', 'AddPoissonNoise', ...]
```

- tomviz-web: list the `tomviz_kernels` module in the catalog. It scans
  the module's directory for `Name.json` / `Name.py` pairs and skips
  `__init__.py`.
- tomviz desktop: install the contents of `directory()` into
  `share/tomviz/scripts`, where `readInPythonScript` /
  `readInJSONDescription` read them today.

Neither application has switched over yet.

## Provenance

The kernels were imported from the tomviz desktop repository, branch
`3.1` at `d0c9879f` (2026-09-24). Where the two applications had
diverged, the desktop version was kept. `path` and `tags` were ported from
tomviz-web's `builtin_kernels` at `59a8145d`. They were drafted for the
kernels tomviz-web did not have, following where the desktop menus place
them.

Until the desktop reads its kernels from here, a fix made to its copy has
to be ported. To list those changes:
`git -C tomviz diff d0c9879f -- tomviz/python`.

These stayed in the desktop, because they only make sense there:

- the custom-transform templates `DefaultCustomTransform`,
  `NewCustomTransform` and `DefaultITKTransform`;
- `Recon_real_time_tomography`, which needs `tomviz._realtime`;
- `PtychoSource` and `PyXRFSource`, driven by the desktop's beamline
  workflows;
- the SAM conda environment files (`tomviz/python/environments`).

## Development

```sh
pip install -e ".[dev]"
pytest
flake8 --config setup.cfg src/tomviz_kernels/__init__.py tests
```

The tests check every kernel's contract (a script and a description with
`path` and `tags`, unique names), build a tomviz-pipeline node from every
description, and run a few cheap kernels end to end. Kernels whose
optional dependencies are missing are skipped.

The kernel scripts are kept identical to the desktop copies they came
from and are not linted yet.

To add a kernel, put `Name.py` and `Name.json` in `src/tomviz_kernels/`.
The description needs a unique `name`, plus `path` and `tags`.

To release, bump `__version__` in `src/tomviz_kernels/__init__.py`, tag
`v<version>`, and publish a GitHub release. `publish.yml` then uploads to
PyPI through trusted publishing.
