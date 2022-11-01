import json
from os import path

from pyhuoi.olt import Olt
import pytest

PWD = path.dirname(path.realpath(__file__))


def read_olt_parameters() -> dict:
    with open(PWD + '/olt_parameters.json', 'r') as f:
        json_text = f.read()
        return json.loads(json_text)


def test_read_olt_parameters():
    """Checking if there are devices to test on."""

    olt_parameters = read_olt_parameters()
    assert len(olt_parameters) > 0
    for name, param in olt_parameters.items():
        assert len(param) > 2
        assert param['ip']
        assert param['username']
        assert param['password']


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_version(olt_name, olt_params):
    expected_keys = ('version', 'patch', 'product', 'uptime')
    #print(f'olt: {olt_name}, params: {olt_params}')
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'])
    version = olt.get_version()

    # returned dict should be at minimum 7 element count
    # TODO: verificate
    assert len(version) > 7
    for key in expected_keys:
        assert key in version
    assert 'day' in version['uptime']
    assert 'hour' in version['uptime']
    assert 'second' in version['uptime']

