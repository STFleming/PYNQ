from pynqmetadata import Module
from .ip_dict_view import IpDictView
from .gpio_dict_view import GpioDictView
from .clock_dict_view import ClockDictView
from .append_drivers_pass import bind_drivers_to_metadata
from typing import Dict

class RuntimeMetadata:
    """A class to manage the runtime pynqmetadata"""

    def __init__(self, 
                md:Module, 
                ip_drivers:Dict[str, object],
                default_ip=object,
                device=object
    )->None:
        """ The runtime metadata object
            This contains views onto the metadata that are dynamically updated when
            the underlying metadata object is changed. 
            It contains the following views:
            
            ip_dict
            -----------------
            A view on each of the ip cores in the design

            gpio_dict
            -----------------
            A view on the PS accessible GPIO pins and what they are accessing
         """
        self.md = bind_drivers_to_metadata(md, device=device, ip_drivers=ip_drivers, default_ip=default_ip)
        self.md.refresh()
        self.ip_dict = IpDictView(self.md)
        self.gpio_dict = GpioDictView(self.md)
        self.clock_dict = ClockDictView(self.md)

    def __getattr__(self, key):
        """ Overload of __getattr__ to return a driver for an IP
        or hierarchy.""" 
        if key in self.ip_dict:
            return self.ip_dict[key]["driver"](self.ip_dict[key])
        else:
            raise RuntimeError(f"No IP called {key} in the overlay that has a driver")