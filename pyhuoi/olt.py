from netmiko import ConnectHandler
import re
from enum import Enum
from pyhuoi.onu import Onu


class OltConfigMode(Enum):
    USER = 0
    ENABLE = 1
    CONFIG = 2
    INTERFACE = 3
    BTV = 4


class Olt:
    connection: ConnectHandler = None
    config_mode: OltConfigMode = None
    ip: str = None
    username: str = None
    password: str = None
    interface_mode_interface: str = None

    def __init__(self, ip: str = '', username: str = '', password: str = '', session_log: str = None) -> None:
        self.ip = ip
        self.username = username
        self.password = password
        self.session_log = session_log

    def __repr__(self):
        return f'OLT ip {self.ip}'

    def _init_connection(self):
        self.connection = ConnectHandler(device_type='huawei_olt',
                                         ip=self.ip,
                                         username=self.username,
                                         password=self.password,
                                         session_log=self.session_log)
        self.config_mode = OltConfigMode.USER

    def get_connection(self):
        if not self.connection:
            self._init_connection()
        return self.connection

    def get_version(self) -> dict:
        cmd = 'display version'
        valid_modes = (OltConfigMode.USER,
                       OltConfigMode.ENABLE,
                       OltConfigMode.CONFIG)
        if self.get_config_mode() not in valid_modes:
            self.set_config_mode(OltConfigMode.CONFIG)
        version_pattern = r'\s+([A-Za-z ]+[A-Za-z]+?)\s+:\s+([A-Za-z0-9 -]+?)\s*$'
        uptime_pattern = r'Uptime is\s([^\n]+)'
        conn = self.get_connection()
        output = conn.send_command(cmd)
        version_dict = {}
        for section in re.findall(version_pattern, output, re.MULTILINE):
            version_dict[section[0].lower().strip()] = section[1]
        uptime = re.findall(uptime_pattern, output).pop()
        version_dict['uptime'] = uptime
        return version_dict

    def get_onu_list(self, frame: int = None, board: int = None, port: int = None):

        if port is not None and (frame is None or board is None) or \
                board is not None and frame is None:
            raise ValueError('Please pass frame with board or/and port')

        cmd = f'display ont info {frame or "0"} {board or ""} {port or ""} all'
        cmd = re.sub(' +', ' ', cmd)
        #ont_info_pattern = r'([0-9]+)\/ ([0-9]+)\/([0-9]+)\s+([0-9]+)  ([A-F0-9]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        ont_info_pattern = r'([0-9]+)\/\s*([0-9]+)\/([0-9]+)\s+([0-9]+)  ([A-F0-9]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        self.set_config_mode(OltConfigMode.ENABLE)
        conn = self.get_connection()
        try:
            output = conn.send_command(cmd, read_timeout=90, expect_string="#")
        except Exception as e:
            print(f'Exception: {e} on \nolt: {self}')
            return None

        olt_list_match = re.findall(ont_info_pattern, output)
        return {onusn: {'frame': int(frame), 'board': int(board), 'port': int(port), 'onuid': int(onuid), 'control': control,
                        'run': run, 'config': config, 'match': match, 'protect': protect}
                for frame, board, port, onuid, onusn, control, run, config, match, protect in olt_list_match}

    def get_config_mode(self) -> OltConfigMode:
        return self.config_mode

    def set_config_mode(self, mode: OltConfigMode) -> None:
        if mode == OltConfigMode.INTERFACE:
            raise ValueError('Cannot go to interface mode without knowing interface name!')

        # same mode, do nothing
        if self.config_mode == mode:
            return None

        conn = self.get_connection()
        if self.config_mode == OltConfigMode.USER:
            conn.send_command('enable', expect_string='#')
            self.config_mode = OltConfigMode.ENABLE
            return self.set_config_mode(mode)

        if self.config_mode == OltConfigMode.ENABLE:
            if mode == OltConfigMode.USER:
                conn.send_command('disable', expect_string='>')
                self.config_mode = OltConfigMode.USER
                return
            if mode == OltConfigMode.CONFIG:
                conn.send_command('config', expect_string=r'\(config\)#')
                self.config_mode = OltConfigMode.CONFIG
                return

        if self.config_mode == OltConfigMode.CONFIG:
            conn.send_command('quit', expect_string='#')
            self.config_mode = OltConfigMode.ENABLE
            return self.set_config_mode(mode)

        if self.config_mode == OltConfigMode.INTERFACE:
            conn.send_command('quit', expect_string=r'\(config\)#')
            self.config_mode = OltConfigMode.CONFIG
            return self.set_config_mode(mode)

    def set_interface_mode(self, frame: int, board: int):
        if self.get_config_mode() is not OltConfigMode.CONFIG:
            self.set_config_mode(OltConfigMode.CONFIG)

        conn = self.get_connection()
        expected_prompt = rf'\(config-if-gpon-{frame}/{board}\)#'
        conn.send_command(f'interface gpon {frame}/{board}', expect_string=expected_prompt)
        self.config_mode = OltConfigMode.INTERFACE
        self.interface_mode_interface = (frame, board)
        return conn.find_prompt()

    def get_interface_mode_interface(self):
        return self.interface_mode_interface

    def disconnect(self) -> None:
        if self.connection:
            self.connection.disconnect()

    def onu_add(self, onu: Onu):
        if onu.frame is None or onu. board is None or onu.port is None:
            raise TypeError('frame, board, port attributes of Onu must be set')

        cmd = f'ont add {onu.port} sn-auth {onu.sn} omci desc "{onu.desc}" ont-lineprofile-name "{onu.lineprofile_name}" ont-srvprofile-name "{onu.srvprofile_name}"'
        conn = self.get_connection()
        self.set_interface_mode(onu.frame, onu.board)
        output = conn.send_command(cmd)
        if 'Number of ONTs that can be added: 1, success: 1' in output:
            if find := re.findall('ONTID :([0-9]+)', output):
                onu.onuid = find[0][0]
        return output


#     def add_service_port(self, service_port: ServicePort):
#         """service-port 28 vlan 1554 gpon 0/0/0 ont 3 gemport 1 multi-service user-vlan
# 301 tag-transform translate-and-add inner-vlan 301 inner-priority 0"""
#
#         """service-port 29 vlan 501 gpon 0/0/0 ont 3 gemport 2 multi-service user-vlan 500 tag-transform translate"""
#
#         """service-port 51 vlan 1399 gpon 0/0/0 ont 1 gemport 1 multi-service user-vlan
# 1399 tag-transform translate inbound traffic-table index 20 outbound
# traffic-table index 20"""
#
#     def add_btv_user(self, btv_user: BtvUser):
#         """igmp user add 0 service-port 59 no-auth max-program 64"""
#         """igmp user add 2 service-port 59 no-auth quickleave immediate max-program 10
# igmp-version v2
# igmp multicast-vlan member service-port 59"""
