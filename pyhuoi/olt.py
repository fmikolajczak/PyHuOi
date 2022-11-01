from netmiko import ConnectHandler
import re

class Olt:
    connection: ConnectHandler = None

    def __init__(self, ip: str = '', username: str = '', password: str = '') -> None:
        self.ip = ip
        self.username = username
        self.password = password

    def _init_connection(self):
        self.connection = ConnectHandler(device_type='huawei_olt',
                                         ip=self.ip,
                                         username=self.username,
                                         password=self.password)

    def get_connection(self):
        if not self.connection:
            self._init_connection()
        return self.connection

    def get_version(self) -> dict:
        cmd = 'display version'
        version_pattern = '\s+([A-Za-z ]+[A-Za-z]+?)\s+:\s+([A-Za-z0-9 -]+?)\s*$'
        uptime_pattern = 'Uptime is\s([^\n]+)'
        conn = self.get_connection()
        output = conn.send_command('display version')
        version_dict = {}
        for section in re.findall(version_pattern, output, re.MULTILINE):
            version_dict[section[0].lower().strip()] = section[1]
        uptime = re.findall(uptime_pattern, output).pop()
        version_dict['uptime'] = uptime
        return version_dict
