from typing import Dict

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort
from pynqmetadata.errors import FeatureNotYetImplemented

from ..utils import ReprDict
from .append_drivers_pass import DriverExtension

def _default_repr(obj):
    return repr(obj)

class GpioDictView:
    """
    Provides a view onto the metadata that mirrors the structure of gpio_dict.
    """

    def __init__(self, module: Module) -> None:
        self._md = module
        self._state = {}

    @property
    def gpio_dict(self) -> Dict:
        repr_dict = {}

        for core in self._md.cores.values():
            if isinstance(core, ProcSysCore):
                gpio = core.gpio
                for n,i in gpio.items():
                    repr_dict[n] = {}
                    if n in self._state:
                        repr_dict[n]["state"] = self._state[n] 
                    else:
                        repr_dict[n]["state"] = None 
                    pins='{'
                    for p in i["pins"]:
                        ref:str = p.ref
                        pins += f'"{ref}"'
                        if p != i["pins"][-1]:
                            pins+=","
                    pins+='}'
                    repr_dict[n]["pins"] = pins
                    repr_dict[n]["index"] = int(i["index"])

        return repr_dict

    def items(self):
        return self.gpio_dict.items()

    def __len__(self) -> int:
        return len(self.gpio_dict)

    def __iter__(self):
        for ip in self.gpio_dict:
            yield ip

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.gpio_dict, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.gpio_dict[key]

    def __setitem__(self, key: str, value: object) -> None:
        """Set the state of an item in the gpio_dict"""
        self._state[key] = value
