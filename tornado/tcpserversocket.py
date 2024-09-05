from dataclasses import dataclass
from typing import Optional
import socket

from tornado.netutil import _DEFAULT_BACKLOG

@dataclass
class TCPServerSocket:
    port: int
    address: Optional[str] = None
    family: socket.AddressFamily = socket.AF_UNSPEC
    backlog: int = _DEFAULT_BACKLOG
    flags: Optional[int] = None
    reuse_port: bool = False
