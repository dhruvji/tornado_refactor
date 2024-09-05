from dataclasses import dataclass
from typing import Optional, Union, Dict, Any
import socket
import ssl
import datetime

@dataclass
class TCPClientConfig:
    host: str
    port: int
    af: socket.AddressFamily = socket.AF_UNSPEC
    ssl_options: Optional[Union[Dict[str, Any], ssl.SSLContext]] = None
    max_buffer_size: Optional[int] = None
    source_ip: Optional[str] = None
    source_port: Optional[int] = None
    timeout: Optional[Union[float, datetime.timedelta]] = None
