from dataclasses import dataclass


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
