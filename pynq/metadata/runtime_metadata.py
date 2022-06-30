from pynqmetadata import Module
from .ip_dict_view import IpDictView
from .gpio_dict_view import GpioDictView
from .clock_dict_view import ClockDictView
from .mem_dict_view import MemDictView
from .hierarchy_dict_view import HierarchyDictView
from .interrupt_controllers_view import InterruptControllersView
from .append_drivers_pass import bind_drivers_to_metadata
from typing import Dict

class RuntimeMetadata:
    """A class to manage the runtime pynqmetadata"""

    def __init__(self, 
                md:Module, 
                ip_drivers:Dict[str, object],
                default_ip:object,
                device:object,
                hierarchy_drivers:object,
                default_hierarchy:object,
                overlay:object
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
        self.mem_dict = MemDictView(self.md)
        self.hierarchy_dict = HierarchyDictView(self.md, self.ip_dict, self.mem_dict, overlay, hierarchy_drivers, default_hierarchy, device)
        self.interrupt_controllers = InterruptControllersView(self.md)

    def __getattr__(self, key):
        """ Overload of __getattr__ to return a driver for an IP
        or hierarchy.""" 
        if key in self.ip_dict:
            return self.ip_dict[key]["driver"](self.ip_dict[key])
        else:
            raise RuntimeError(f"No IP called {key} in the overlay that has a driver")
