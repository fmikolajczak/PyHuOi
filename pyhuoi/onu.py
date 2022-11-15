from dataclasses import dataclass


@dataclass
class BtvUser:
    service_port: int = None
    vlan: int = None
    attrib: str = None


@dataclass
class ServicePort:
    id: int = None
    vlan: int = None
    user_vlan: int = None
    inner_vlan: int = None
    gemport: int = None
    inbound_traffic_table_name: str = None
    inbound_traffic_table_id: int = None
    outbound_traffic_table_name: str = None
    outbound_traffic_table_id: int = None


@dataclass
class Onu:
    sn: str = None
    board: int = None
    frame: int = None
    port: int = None
    onuid: int = None

    lineprofile_id: int = None
    lineprofile_name: str = None
    srvprofile_id: int = None
    srvprofile_name: str = None

    desc: str = None

    service_ports = []
    btv_sp = []