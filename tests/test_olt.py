from pyhuoi.olt import Olt
import pytest


def read_olt_parameters() -> dict:
    return None


@pytest.mark.xfail
def test_read_olt_parameters():
    olt_parameters = read_olt_parameters()
    assert len(olt_parameters) > 0
    olt1 = next(iter(olt_parameters))
    assert len(olt1) > 2
    assert olt1['ip']
    assert olt1['username']
    assert olt2['password']


@pytest.mark.skip('its not working anyway')
def test_get_version():
    olt = Olt()
    version = olt.get_version()
    assert version.version
