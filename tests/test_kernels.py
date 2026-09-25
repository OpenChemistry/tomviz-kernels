"""The contract every kernel in the package follows: a ``Name.py`` script
next to a ``Name.json`` description carrying the catalog fields the host
applications rely on. Needs nothing beyond the standard library."""

import json
import warnings

import pytest

import tomviz_kernels

DIRECTORY = tomviz_kernels.directory()
NAMES = tomviz_kernels.names()


def description(name):
    return json.loads((DIRECTORY / f'{name}.json').read_text('utf-8'))


def test_every_script_has_a_description():
    scripts = {path.stem for path in DIRECTORY.glob('*.py')
               if not path.name.startswith('_')}
    assert scripts == set(NAMES)


def test_only_kernel_files_in_the_package():
    others = [path.name for path in DIRECTORY.iterdir()
              if path.suffix not in ('.py', '.json')
              and path.name != '__pycache__']
    assert others == []


@pytest.mark.parametrize('name', NAMES)
def test_script_compiles(name):
    source = (DIRECTORY / f'{name}.py').read_text('utf-8')
    # SyntaxWarnings (invalid escape sequences, ...) become errors in
    # later Pythons; hosts compile the scripts at run time.
    with warnings.catch_warnings():
        warnings.simplefilter('error', SyntaxWarning)
        compile(source, f'{name}.py', 'exec')


@pytest.mark.parametrize('name', NAMES)
def test_description_has_catalog_fields(name):
    desc = description(name)
    assert isinstance(desc, dict)

    path = desc.get('path')
    assert isinstance(path, list) and path, 'path must be a non-empty list'
    assert all(isinstance(p, str) and p.strip() for p in path)

    tags = desc.get('tags')
    assert isinstance(tags, list) and tags, 'tags must be a non-empty list'
    assert all(isinstance(t, str) and t.strip() for t in tags)
    assert len(set(tags)) == len(tags), 'duplicate tags'


def test_names_are_present_and_unique():
    # Hosts key their catalog by name (tomviz-web): a missing or repeated
    # name hides a kernel.
    names = {kernel: description(kernel).get('name') for kernel in NAMES}
    assert {k for k, name in names.items() if not name} == set()

    seen = {}
    for kernel, name in names.items():
        seen.setdefault(name, []).append(kernel)
    assert {n: k for n, k in seen.items() if len(k) > 1} == {}
