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
    olt_parameters = read_olt_parameters()
    assert len(olt_parameters) > 0
    for name, param in olt_parameters.items():
        assert len(param) > 2
        assert param['ip']
        assert param['username']
        assert param['password']


@pytest.mark.skip('its not working anyway')
def test_get_version():
    olt = Olt()
    version = olt.get_version()
    assert version.version
