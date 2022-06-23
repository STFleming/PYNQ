from typing import Dict

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort
from pynqmetadata.errors import FeatureNotYetImplemented

from .append_drivers_pass import DriverExtension

def _default_repr(obj):
    return repr(obj)

class IpDictView:
    """
    Provides a view over the IP register map space, similar to the
    classic pynq metadata ip_dict view
    """

    def __init__(self, module: Module) -> None:
        self._md = module

    @property
    def ip_dict(self) -> Dict:
        repr_dict = {}
        for core in self._md.cores.values():
            for port in core.ports.values():
                if isinstance(port, SubordinatePort):
                    if len(port.registers) > 0:
                        repr_dict[core.hierarchy_name] = {}
                        repr_dict[core.hierarchy_name]["type"] = core.vlnv.str
                        repr_dict[core.hierarchy_name]["mem_id"] = port.name
                        repr_dict[core.hierarchy_name]["gpio"] = {}
                        repr_dict[core.hierarchy_name]["interrupts"] = {}
                        repr_dict[core.hierarchy_name]["parameters"] = {}
                        for param in core.parameters.values():
                            repr_dict[core.hierarchy_name]["parameters"][param.name] = param.value
                        repr_dict[core.hierarchy_name]["registers"] = {}

                        repr_dict[core.hierarchy_name]["driver"] = None
                        repr_dict[core.hierarchy_name]["device"] = None
                        if "driver" in port.ext and isinstance(port.ext["driver"], DriverExtension):
                            repr_dict[core.hierarchy_name]["driver"] =  port.ext["driver"].driver
                            repr_dict[core.hierarchy_name]["device"] = port.ext["driver"].device

                        if not isinstance(port.parent(), ProcSysCore):
                            for reg in port.registers.values():
                                repr_dict[core.hierarchy_name]["registers"][reg.name] = {}
                                repr_dict[core.hierarchy_name]["registers"][reg.name][
                                    "address_offset"
                                ] = reg.offset
                                repr_dict[core.hierarchy_name]["registers"][reg.name][
                                    "width"
                                ] = reg.width
                                repr_dict[core.hierarchy_name]["registers"][reg.name][
                                    "description"
                                ] = reg.description
                                repr_dict[core.hierarchy_name]["registers"][reg.name][
                                    "fields"
                                ] = {}
                                for f in reg.bitfields.values():
                                    repr_dict[core.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name] = {}
                                    repr_dict[core.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["bit_offset"] = f.LSB
                                    repr_dict[core.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["bit_width"] = (f.MSB - f.LSB)
                                    repr_dict[core.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["description"] = f.description
                            repr_dict[core.hierarchy_name]["state"] = None
                            repr_dict[core.hierarchy_name]["bdtype"] = None
                            repr_dict[core.hierarchy_name]["phys_addr"] = port.baseaddr
                            repr_dict[core.hierarchy_name]["addr_range"] = port.range
                            repr_dict[core.hierarchy_name]["fullpath"] = core.hierarchy_name

            if isinstance(core, ProcSysCore):
                repr_dict[core.hierarchy_name] = {}
                repr_dict[core.hierarchy_name]["type"] = core.vlnv.str
                repr_dict[core.hierarchy_name]["gpio"] = {}
                repr_dict[core.hierarchy_name]["interrupts"] = {}
                repr_dict[core.hierarchy_name]["parameters"] = {}
                repr_dict[core.hierarchy_name]["driver"] = None
                repr_dict[core.hierarchy_name]["device"] = None
                if "driver" in core.ext and isinstance(core.ext["driver"], DriverExtension):
                    repr_dict[core.hierarchy_name]["driver"] = core.ext["driver"].driver 
                    repr_dict[core.hierarchy_name]["device"] = core.ext["driver"].device

                for param in core.parameters.values():
                    repr_dict[core.hierarchy_name]["parameters"][param.name] = param.value

        return repr_dict

    def items(self):
        return self.ip_dict.items()

    def __len__(self) -> int:
        return len(self.ip_dict)

    def __iter__(self):
        for ip in self.ip_dict:
            yield ip

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.ip_dict, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.ip_dict[key]

    def __setitem__(self, key: str, value: object) -> None:
        """TODO: needs to send value into the model bypassing ip_dict
        this will require view tranlation in the other direction"""
        raise FeatureNotYetImplemented("IPDictView is currently only read only")
