from netmiko import ConnectHandler, ReadTimeout
import re
from enum import Enum
from pyhuoi.onu import Onu, ServicePort, BtvUser


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
        #ont_info_list_pattern = r'([0-9]+)\/ ([0-9]+)\/([0-9]+)\s+([0-9]+)  ([A-F0-9]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        ont_info_list_pattern = r'([0-9]+)\/\s*([0-9]+)\/([0-9]+)\s+([0-9]+)  ([A-F0-9]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        self.set_config_mode(OltConfigMode.ENABLE)
        conn = self.get_connection()
        try:
            output = conn.send_command(cmd, read_timeout=90, expect_string="#")
        except Exception as e:
            print(f'Exception: {e} on \nolt: {self}')
            return None

        olt_list_match = re.findall(ont_info_list_pattern, output)
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
        """Adds onu on given frame/board/port. Sets onuid of Onu object after successfully added.

        :returns: Error message or None if run successfully
        """
        if onu.frame is None or onu. board is None or onu.port is None:
            raise TypeError('frame, board, port attributes of Onu must be set')
        if onu.srvprofile_name is None and onu.srvprofile_id is None:
            raise TypeError('Either onu.srvprofile_name or _id must be set.')
        if onu.lineprofile_name is None and onu.lineprofile_id is None:
            raise TypeError('Either onu.lineprofile_name or _id must be set.')

        cmd = f'ont add {onu.port} sn-auth {onu.sn} omci desc "{onu.desc}" ont-lineprofile-name' \
              f' "{onu.lineprofile_name}" ont-srvprofile-name "{onu.srvprofile_name}"'
        conn = self.get_connection()
        try:
            self.set_interface_mode(onu.frame, onu.board)
        except ReadTimeout:
            return "ReadTimeout while edit gpon interface. Maybe this interface does not exist?"
        try:
            output = conn.send_command(cmd)
        except ReadTimeout as e:
            return str(e)
        if 'Number of ONTs that can be added: 1, success: 1' in output:
            if find := re.findall('ONTID :([0-9]+)', output):
                onu.onuid = find[0][0]
                return None
        return output


    def service_port_add(self, onu: Onu, service_port: ServicePort):
        """service-port 28 vlan 1554 gpon 0/0/0 ont 3 gemport 1 multi-service user-vlan
301 tag-transform translate-and-add inner-vlan 301 inner-priority 0"""

        """service-port 29 vlan 501 gpon 0/0/0 ont 3 gemport 2 multi-service user-vlan 500 tag-transform translate"""

        """service-port 51 vlan 1399 gpon 0/0/0 ont 1 gemport 1 multi-service user-vlan
1399 tag-transform translate inbound traffic-table index 20 outbound
traffic-table index 20"""
        # must have gpon interface, and onu_id, vlan, gemport +
        # optionally user-vlan or/and inner-vlan
        # optionally traffic-table + in/out + name/id
        if onu.frame is None or onu.board is None or onu.port is None or onu.onuid is None:
            raise TypeError('frame, board, port and onuid must be set')
        if service_port.vlan is None or service_port.gemport is None:
            raise TypeError('service-port vlan and gemport must be set')
        if service_port.user_vlan is None:
            service_port.user_vlan = service_port.vlan
        if service_port.inbound_traffic_table_id is not None and service_port.inbound_traffic_table_name is not None:
            raise TypeError('inbound traffic table id and name cant be set at the same time')
        if service_port.outbound_traffic_table_id is not None and service_port.outbound_traffic_table_name is not None:
            raise TypeError('outbound traffic table id and name cant be set at the same time')
        cmd = f'service-port vlan {service_port.vlan} gpon {onu.frame}/{onu.board}/{onu.port} ' \
              f'ont {onu.onuid} gemport {service_port.gemport} multi-service user-vlan {service_port.user_vlan}'
        if service_port.inner_vlan is None:
            cmd += f' tag-transform translate'
        else:
            cmd += f' tag-transform translate-and-add inner-vlan {service_port.inner_vlan}'
        if service_port.inbound_traffic_table_id is not None:
            cmd += f' inbound traffic-table id {service_port.inbound_traffic_table_id}'
        if service_port.inbound_traffic_table_name is not None:
            cmd += f' inbound traffic-table name {service_port.inbound_traffic_table_name}'
        if service_port.outbound_traffic_table_id is not None:
            cmd += f' outbound traffic-table id {service_port.outbound_traffic_table_id}'
        if service_port.outbound_traffic_table_name is not None:
            cmd += f' outbound traffic-table name {service_port.outbound_traffic_table_name}'

        self.set_config_mode(OltConfigMode.CONFIG)
        conn = self.get_connection()
        result = conn.send_command(cmd)
        if 'Failure' in result:
            return result


    def btv_user_add(self, btv_user: BtvUser):
        # go to btv config mode
        # (config)# btv
        # (config-btv)#
        # execute sth like this:
        # igmp user add 0 service-port 59 no-auth max-program 64
        # or
        # igmp user add 2 service-port 59 no-auth quickleave immediate max-program 10
        # next go to btv /multicast-vlan config mode
        # (config-btv)# multicast-vlan 2099
        # (config-mvlan2099) #
        # and run:
        # (config-mvlan2099)# igmp multicast-vlan member service-port 59
        return


    def get_service_ports(self, onu: Onu):
        cmd = f'display service-port {onu.frame}/{onu.board}/{onu.port} ont {onu.onuid}'
        self.set_config_mode(OltConfigMode.ENABLE)
        conn = self.get_connection()
        output = conn.send_command(cmd)
        # id, vlan, vattrib, frame, board, port, onuid, gemport, user-vlan, traffix-rx-id, traffic-tx-id
        display_service_port_pattern = r'\s+([0-9]+)\s+([0-9]+)\s+(\S+)\s+gpon\s+([0-9]+)\/([0-9]+)\s+\/([0-9]+)\s+' \
                                       r'([0-9]+)\s+([0-9]+)\s+vlan\s+([0-9]+)\s+([-0-9]+)\s+([-0-9]+)\s+\S+'
        sp_list = re.findall(display_service_port_pattern, output)
        service_port_list = []
        for sp in sp_list:
            service_port = ServicePort(id=sp[0],
                                       vlan=sp[1],
                                       gemport=sp[7],
                                       user_vlan=sp[8],
                                       inbound_traffic_table_id=sp[9],
                                       outbound_traffic_table_id=sp[10])
            service_port_list.append(service_port)
        return service_port_list


    def get_onu_by_sn(self, sn: str) -> Onu:
        """query olt for onu parameters by given sn"""
        conn = self.get_connection()
        self.set_config_mode(OltConfigMode.ENABLE)
        display_ont_info_pattern = r'F\/S\/P\s+:\s([0-9]+)\/([0-9]+)\/([0-9]+)\s+ONT-ID\s+:\s([0-9]+)'
        output = conn.send_command(f'display ont info by-sn {sn}')
        if find := re.findall(display_ont_info_pattern, output):
            onu = Onu(frame=find[0][0],
                      board=find[0][1],
                      port=find[0][2],
                      onuid=find[0][3])
            return onu
        return None

