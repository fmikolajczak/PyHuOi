import json
import string
from os import path
from pyhuoi.onu import Onu, ServicePort, BtvUser
from pyhuoi.olt import Olt, OltConfigMode
import pytest

PWD = path.dirname(path.realpath(__file__))


def read_olt_parameters(write=False) -> dict:
    """Get list of OLTs to test on.

    :param: write: If True gets only OLTs which can write configuration on.
    """
    with open(PWD + '/olt_parameters.json', 'r') as f:
        json_text = f.read()
        olt_dict = json.loads(json_text)
        if write:
            do_not_write_list = []
            for key, params in olt_dict.items():
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


def test_read_olt_parameters_write():
    """Checking if there are devices to test on."""

    olt_parameters = read_olt_parameters(write=True)
    assert len(olt_parameters) > 0
    for name, param in olt_parameters.items():
        assert len(param) > 2
        assert param['ip']
        assert param['username']
        assert param['password']
        assert param['write'] == '1'


def assert_version(version: dict):
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
    olt.disconnect()


def assert_onu_list(onu_list):
    allowed_sn_chars = set('ABCDEF' + string.digits)
    assert onu_list is not None
    assert len(onu_list) > 0
    for sn, onu in onu_list.items():
        assert type(onu) == dict
        # len of sn have to be 16 and contain only chars A-F and digits
        assert len(sn) == 16
        assert set(sn) <= allowed_sn_chars
        assert type(onu.get('frame')) == int
        assert type(onu.get('board')) == int
        assert type(onu.get('port')) == int
        assert type(onu.get('onuid')) == int


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_onu_list(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_get_onu_list.log')
    onu_list = olt.get_onu_list()
    assert_onu_list(onu_list)
    olt.disconnect()


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_version_from_interface_mode(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_get_version_from_interface_mode.log')
    olt.set_interface_mode(*olt_params['gpon_interface'])
    version = olt.get_version()
    assert_version(version)
    olt.disconnect()


@pytest.mark.xfail
def test_get_port_onu_config():
    assert False


@pytest.mark.xfail
def test_get_onu_config_by_sn():
    assert False


@pytest.mark.xfail
def test_get_onu_config_by_fbp():
    assert False


def test_get_onu_list_bad_parameters():
    olt_name, olt_params = list(read_olt_parameters().items())[0]
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'])

    with pytest.raises(ValueError):
        olt.get_onu_list(port=0)
    with pytest.raises(ValueError):
        olt.get_onu_list(board=0)
    with pytest.raises(ValueError):
        olt.get_onu_list(port=0, board=0)


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_onu_list_port(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log=f'test_get_onu_list_port_{olt_name}.log')
    onu_list = olt.get_onu_list(frame=olt_params['onu_list_port'][0],
                                board=olt_params['onu_list_port'][1],
                                port=olt_params['onu_list_port'][2])
    olt.disconnect()
    assert_onu_list(onu_list)


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_get_onu_list_board(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'])
    onu_list = olt.get_onu_list(frame=olt_params['onu_list_port'][0],
                                board=olt_params['onu_list_port'][1])
    olt.disconnect()
    assert_onu_list(onu_list)


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
    olt.disconnect()


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_interface_mode(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_interface_mode.log')
    olt.get_connection()

    interface_mode_result = olt.set_interface_mode(*olt_params['gpon_interface'])
    assert 'config-if' in interface_mode_result
    current_mode = olt.get_config_mode()
    current_mode_interface = olt.get_interface_mode_interface()
    assert current_mode == OltConfigMode.INTERFACE
    assert current_mode_interface == tuple(olt_params['gpon_interface'])
    olt.disconnect()


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters(True).items())
def test_onu_add(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_onu_add.log')
    olt.get_connection()
    onu = Onu(sn='4800000000073357',
              frame=olt_params['write_gpon_port'][0],
              board=olt_params['write_gpon_port'][1],
              port=olt_params['write_gpon_port'][2],
              lineprofile_name=olt_params['write_lineprofile_name'],
              srvprofile_name=olt_params['write_srvprofile_name'],
              desc='test_PyHuOi')

    result = olt.onu_add(onu)
    print(f'result:\n{result}\n')
    assert result is None
    assert onu.onuid is not None


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters(True).items())
def test_onu_add_nonexistent_gpon_port(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_onu_add.log')
    olt.get_connection()
    onu = Onu(sn='4800000000073357',
              frame=olt_params['write_gpon_port'][0],
              board=olt_params['write_gpon_port'][1],
              port=int(olt_params['write_gpon_port'][2])+16,
              lineprofile_name=olt_params['write_lineprofile_name'],
              srvprofile_name=olt_params['write_srvprofile_name'],
              desc='test_PyHuOi')

    result = olt.onu_add(onu)
    print(f'result:\n{result}\n')
    assert result is not None
    assert onu.onuid is None


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters(True).items())
def test_onu_add_nonexistent_gpon_board(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_onu_add.log')
    olt.get_connection()
    onu = Onu(sn='4800000000073357',
              frame=olt_params['write_gpon_port'][0],
              board=int(olt_params['write_gpon_port'][1]) + 16,
              port=int(olt_params['write_gpon_port'][2]),
              lineprofile_name=olt_params['write_lineprofile_name'],
              srvprofile_name=olt_params['write_srvprofile_name'],
              desc='test_PyHuOi')

    result = olt.onu_add(onu)
    print(f'result:\n{result}\n')
    assert result is not None
    assert onu.onuid is None


def test_onu_add_no_port():
    olt = Olt()
    onu = Onu(sn='4800000000073357', frame='0', board='0',
              srvprofile_id=0, lineprofile_id=0)
    with pytest.raises(TypeError):
        olt.onu_add(onu)


def test_onu_add_no_frame():
    olt = Olt()
    onu = Onu(sn='4800000000073357', port='0', board='0',
              srvprofile_id=0, lineprofile_id=0)
    with pytest.raises(TypeError):
        olt.onu_add(onu)


def test_onu_add_no_board():
    olt = Olt()
    onu = Onu(sn='4800000000073357', port='0', frame='0',
              srvprofile_id=0, lineprofile_id=0)
    with pytest.raises(TypeError):
        olt.onu_add(onu)


def test_onu_add_no_srvprofile():
    olt = Olt()
    onu = Onu(sn='4800000000073357', port='0', frame='0', board=0,
              lineprofile_id=0)
    with pytest.raises(TypeError):
        olt.onu_add(onu)


def test_onu_add_no_lineprofile():
    olt = Olt()
    onu = Onu(sn='4800000000073357', port='0', frame='0', board=0,
              srvprofile_name='test')
    with pytest.raises(TypeError):
        olt.onu_add(onu)


def test_add_service_port_no_params():
    olt = Olt()
    onu = Onu()
    service_port = ServicePort()

    with pytest.raises(TypeError):
        olt.service_port_add(onu, service_port)


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters(True).items())
def test_service_port_add(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_service_port_add.log')
    olt.get_connection()
    onu = Onu(sn='4800000000073357',
              frame=olt_params['write_gpon_port'][0],
              board=int(olt_params['write_gpon_port'][1]),
              port=int(olt_params['write_gpon_port'][2]),
              onuid=int(olt_params['write_gpon_port'][3]),
              lineprofile_name=olt_params['write_lineprofile_name'],
              srvprofile_name=olt_params['write_srvprofile_name'],
              desc='test_PyHuOi')

    for sp_conf in olt_params['service_ports']:
        service_port = ServicePort(vlan=sp_conf[0], gemport=sp_conf[1],
                                   outbound_traffic_table_name=sp_conf[2],
                                   inbound_traffic_table_name=sp_conf[3])
        result = olt.service_port_add(onu, service_port)
        assert result is None


@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters(True).items())
def test_service_btv_user_add(olt_name, olt_params):
    olt = Olt(ip=olt_params['ip'],
              username=olt_params['username'],
              password=olt_params['password'],
              session_log='test_service_port_add.log')
    olt.get_connection()
    onu = Onu(sn='4800000000073357',
              frame=olt_params['write_gpon_port'][0],
              board=int(olt_params['write_gpon_port'][1]),
              port=int(olt_params['write_gpon_port'][2]),
              onuid=int(olt_params['write_gpon_port'][3]),
              lineprofile_name=olt_params['write_lineprofile_name'],
              srvprofile_name=olt_params['write_srvprofile_name'],
              desc='test_PyHuOi')

    for sp_conf in olt_params['service_ports']:
        if int(sp_conf[0]) == int(olt_params['btv_user_vlan']):
            olt.btv_user_add

@pytest.mark.xfail
@pytest.mark.parametrize('olt_name, olt_params', read_olt_parameters().items())
def test_login_after_login(olt_name, olt_params):
    return None
