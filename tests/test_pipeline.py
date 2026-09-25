"""The kernels in tomviz-pipeline, the runtime that hosts them in
tomviz-web and in the desktop's external environments: every description
builds a node, every script defines what its host looks for, and a few
cheap kernels run end to end (one per host: schema-v2 source, schema-v2
transform, v1 function, v1 function with the NEP 50 dtype logic)."""

import importlib.util
import json

import numpy as np
import pytest
from tomviz_pipeline import Pipeline, PortData, PythonNode, SourceNode
from tomviz_pipeline._compat import (
    install_script_module_aliases,
    kernel_base_classes,
)
from tomviz_pipeline._internal import find_transform_function
from tomviz_pipeline.dataset import Dataset
from tomviz_pipeline.nodes.transforms.legacy_python import (
    LegacyPythonTransform,
)

import tomviz_kernels

DIRECTORY = tomviz_kernels.directory()
NAMES = tomviz_kernels.names()


def description(name):
    return json.loads((DIRECTORY / f'{name}.json').read_text('utf-8'))


def is_v2(desc):
    return desc.get('schemaVersion') == 2


def build(name):
    """The node a host builds for a kernel, as tomviz-web does."""
    desc = description(name)
    script = DIRECTORY / f'{name}.py'
    if is_v2(desc):
        return PythonNode(desc, kernel=script)
    node = LegacyPythonTransform()
    assert node.deserialize({
        'description': json.dumps(desc),
        'script': script.read_text('utf-8'),
    })
    return node


def load_module(name):
    """Execute a kernel script the way the hosts do; skip when it needs
    an optional third-party package that is not installed."""
    install_script_module_aliases()
    spec = importlib.util.spec_from_file_location(
        f'tomviz_kernel_{name}', DIRECTORY / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split('.')[0] != 'tomviz':
            pytest.skip(f'{name} needs {exc.name}')
        raise
    return module


@pytest.mark.parametrize('name', NAMES)
def test_description_builds_a_node(name):
    desc = description(name)
    node = build(name)

    if 'label' in desc:
        assert node.label == desc['label']
    if is_v2(desc):
        outputs = [port.name for port in node.output_ports()]
        assert outputs == [o['name'] for o in desc['outputs']]
        inputs = {port.name for port in node.input_ports()}
        assert {i['name'] for i in desc.get('inputs', [])} <= inputs
    else:
        assert node.input_port('volume') is not None
        if 'inputType' in desc:
            accepted = node.input_port('volume').accepted_types
            assert accepted == [desc['inputType']]


@pytest.mark.parametrize('name', NAMES)
def test_script_defines_what_the_host_runs(name):
    desc = description(name)
    module = load_module(name)

    if is_v2(desc):
        bases = kernel_base_classes(
            'transform' if desc.get('inputs') else 'source')
        kernels = [value for value in vars(module).values()
                   if isinstance(value, type) and value not in bases
                   and issubclass(value, bases)]
        assert len(kernels) == 1
    else:
        assert callable(find_transform_function(module))


class ArraySource(SourceNode):
    """Emits a fixed array as an 'ImageData' dataset."""

    type_name = 'test.array'

    def __init__(self, values):
        super().__init__()
        self.values = values
        self.add_output('volume', 'ImageData')

    def execute(self):
        dataset = Dataset({'scalars': self.values.copy()})
        self.output_port('volume').set_data(PortData(dataset, 'ImageData'))
        return True


def run(name, values=None, **parameters):
    """Run one kernel, fed `values` when it is a transform, and return
    the scalars on its first output."""
    graph = Pipeline()
    node = graph.add_node(build(name))
    if values is not None:
        source = graph.add_node(ArraySource(values))
        graph.create_link(source.output_port('volume'),
                          node.input_port('volume'))
    if parameters:
        node.set_parameters(**parameters)
    assert graph.execute().succeeded()
    return node.output_ports()[0].data().payload.active_scalars


def ramp(shape, dtype):
    size = int(np.prod(shape))
    return np.arange(size, dtype=dtype).reshape(shape, order='F')


def test_constant_dataset_source():
    result = run('ConstantDataset', shape=[4, 5, 6], value=3.0)

    assert result.shape == (4, 5, 6)
    assert np.all(result == 3.0)


def test_invert_data_flips_the_range():
    values = ramp((3, 4, 5), np.float32)

    result = run('InvertData', values)

    np.testing.assert_allclose(result, values.max() - values + values.min())


def test_gaussian_filter_spreads_a_spike():
    values = np.zeros((9, 9, 9), dtype=np.float32, order='F')
    values[4, 4, 4] = 1.0

    result = run('GaussianFilter', values, sigma=1.0)

    assert result[4, 4, 4] < 1.0
    assert result[4, 4, 5] > 0.0
    assert np.isclose(result.sum(), 1.0, atol=1e-3)


def test_add_constant_keeps_small_integers():
    values = ramp((2, 3, 4), np.uint8)

    result = run('AddConstant', values, constant=2.0)

    np.testing.assert_array_equal(result, values.astype(np.int64) + 2)
    assert result.dtype == np.uint8
