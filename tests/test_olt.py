import json
import string
from os import path

from pyhuoi.olt import Olt, OltConfigMode
import pytest

PWD = path.dirname(path.realpath(__file__))


def read_olt_parameters(write=False) -> dict:
    """Get list of OLTs to test on.

    :param write: If True gets only OLTs which can write configuration on.
    """
    with open(PWD + '/olt_parameters.json', 'r') as f:
        json_text = f.read()
        olt_dict = json.loads(json_text)
        if write:
            do_not_write_list = []
            for key, params in d.items():
                if not params.get('write') or not int(params.get('write')):
                    do_not_write_list.append(key)
            for key in do_not_write_list:
                olt_dict.pop(key)
        return olt_dict


def test_read_olt_parameters():
    """Checking if there are devices to test on."""

    olt_parameters = read_olt_parameters()
    assert len(olt_parameters) > 0
    for name, param in olt_parameters.items():
        assert len(param) > 2
        assert param['ip']
        assert param['username']
        assert param['password']


def assert_version(version: str):
    expected_keys = ('version', 'patch', 'product', 'uptime')
    # returned dict should be at minimum 7 element count
    # TODO: check how many elements are found in OLTs in the wild
    assert len(version) > 7
    for key in expected_keys:
        assert key in version
    assert 'day' in version['uptime']
    assert 'hour' in version['uptime']
    assert 'second' in version['uptime']


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_version(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'])
    version = olt.get_version()
    assert_version(version)


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_onu_list(olt_name, olt_params):
    allowed_sn_chars = set('ABCDEF' + string.digits)
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_get_onu_list.log')
    onu_list = olt.get_onu_list()
    assert onu_list is not None
    for sn, onu in onu_list:
        assert type(onu) == dict
        # len of sn have to be 16 and contain only chars A-F and digits
        assert len(sn) == 16
        assert set(onu.get('sn')) <= allowed_sn_chars
        assert type(onu.get('frame')) == int
        assert type(onu.get('board')) == int
        assert type(onu.get('port')) == int
        assert type(onu.get('onuid')) == int


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_version_from_interface_mode(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_get_version_from_interface_mode.log')
    olt.set_interface_mode(olt_params['gpon_interface'])
    version = olt.get_version()
    assert_version(version)


@pytest.mark.xfail
def test_get_port_onu_config():
    assert False


@pytest.mark.xfail
def test_get_onu_config_by_sn():
    assert False


@pytest.mark.xfail
def test_get_onu_config_by_fbp():
    assert False


@pytest.mark.xfail
def test_get_port_onu_list():
    assert False


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_configuration_modes(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'])

    olt.get_connection()

    current_mode = olt.get_config_mode()
    assert current_mode == OltConfigMode.USER

    olt.set_config_mode(OltConfigMode.ENABLE)
    current_mode = olt.get_config_mode()
    assert current_mode == OltConfigMode.ENABLE

    olt.set_config_mode(OltConfigMode.CONFIG)
    current_mode = olt.get_config_mode()
    assert current_mode == OltConfigMode.CONFIG

    olt.set_config_mode(OltConfigMode.USER)
    current_mode = olt.get_config_mode()
    assert current_mode == OltConfigMode.USER


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_interface_mode(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_inteface_mode.log')
    olt.get_connection()

    interface_mode_result = olt.set_interface_mode(olt_params['gpon_interface'])
    assert 'config-if' in interface_mode_result
    current_mode = olt.get_config_mode()
    current_mode_interface = olt.get_interface_mode_interface()
    assert current_mode == OltConfigMode.INTERFACE
    assert current_mode_interface == olt_params['gpon_interface']
