from netmiko import ConnectHandler
import re
from enum import Enum


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

    def get_onu_list(self):
        cmd = 'display ont info 0 all'
        ont_info_pattern = r'([0-9]+)\/ ([0-9]+)\/([0-9]+)\s+([0-9]+)  {}\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        self.set_config_mode(OltConfigMode.ENABLE)
        conn = self.get_connection()
        try:
            output = conn.send_command(cmd)
        except Exception as e:
            print(f'Exception: {e} on \nolt: {self}')
            return None

        olt_list_match = re.findall(ont_info_pattern, output)
        return {k: v for k, *v in olt_list_match}

    def get_config_mode(self) -> OltConfigMode:
        return self.config_mode

    def set_config_mode(self, mode: OltConfigMode) -> None:
        # can set configmode: USER, ENABLE, CONFIG (not INTERFACE)
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
                conn.send_command('config', expect_string='\(config\)#')
                self.config_mode = OltConfigMode.CONFIG
                return

        if self.config_mode == OltConfigMode.CONFIG:
            conn.send_command('quit', expect_string='#')
            self.config_mode = OltConfigMode.ENABLE
            return self.set_config_mode(mode)

        if self.config_mode == OltConfigMode.INTERFACE:
            conn.send_command('quit', expect_string='(config)#')
            self.config_mode = OltConfigMode.CONFIG
            return self.set_config_mode(mode)

        prompt = conn.find_prompt()
        return prompt

    def set_config_interface(self, interface: str):
        raise NotImplementedError('Not implemented Yet!')
