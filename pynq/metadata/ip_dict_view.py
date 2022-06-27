from typing import Dict

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort, ManagerPort, Core
from pynqmetadata.errors import FeatureNotYetImplemented, CoreNotFound

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

    def get_ps(self)->ProcSysCore:
        """ Gets a reference to the PS core for this design """
        for core in self._md.cores.values():
            if isinstance(core, ProcSysCore):
                return core
        raise CoreNotFound(f"Could not find a processing system for the design when getting the ip_dict_view")

    @property
    def ip_dict(self) -> Dict:
        repr_dict = {}

        ps = self.get_ps() 
        for port in ps.ports.values():
            if isinstance(port, ManagerPort):
                for sp_ref in port.addrmap:
                    dst_port = port.addrmap_obj[sp_ref]
                    dcore = dst_port.parent()
                    if isinstance(dcore, Core):
                        repr_dict[dcore.hierarchy_name] = {}
                        repr_dict[dcore.hierarchy_name]["type"] = dcore.vlnv.str
                        repr_dict[dcore.hierarchy_name]["mem_id"] = dst_port.name
                        repr_dict[dcore.hierarchy_name]["memtype"] = "REGISTER" 
                        repr_dict[dcore.hierarchy_name]["gpio"] = {}
                        repr_dict[dcore.hierarchy_name]["interrupts"] = {}
                        repr_dict[dcore.hierarchy_name]["parameters"] = {}
                        for param in dcore.parameters.values():
                            repr_dict[dcore.hierarchy_name]["parameters"][param.name] = param.value
                        repr_dict[dcore.hierarchy_name]["registers"] = {}

                        repr_dict[dcore.hierarchy_name]["driver"] = None
                        repr_dict[dcore.hierarchy_name]["device"] = None
                        if "driver" in dst_port.ext and isinstance(dst_port.ext["driver"], DriverExtension):
                            repr_dict[dcore.hierarchy_name]["driver"] = dst_port.ext["driver"].driver
                            repr_dict[dcore.hierarchy_name]["device"] = dst_port.ext["driver"].device

                        if not isinstance(dst_port.parent(), ProcSysCore):
                            for reg in dst_port.registers.values():
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name] = {}
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                    "address_offset"
                                ] = reg.offset
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                    "size"
                                ] = reg.width
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                    "access"
                                ] = reg.access
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                    "description"
                                ] = reg.description
                                repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                    "fields"
                                ] = {}
                                for f in reg.bitfields.values():
                                    repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name] = {}
                                    repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["bit_offset"] = f.LSB
                                    repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["bit_width"] = (f.MSB - f.LSB) + 1
                                    repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["access"] = f.access
                                    repr_dict[dcore.hierarchy_name]["registers"][reg.name][
                                        "fields"
                                    ][f.name]["description"] = f.description
                            repr_dict[dcore.hierarchy_name]["state"] = None
                            repr_dict[dcore.hierarchy_name]["bdtype"] = None
                            repr_dict[dcore.hierarchy_name]["phys_addr"] = dst_port.baseaddr
                            repr_dict[dcore.hierarchy_name]["addr_range"] = dst_port.range
                            repr_dict[dcore.hierarchy_name]["fullpath"] = dcore.hierarchy_name

        repr_dict[ps.hierarchy_name] = {}
        repr_dict[ps.hierarchy_name]["type"] = ps.vlnv.str
        repr_dict[ps.hierarchy_name]["gpio"] = {}
        repr_dict[ps.hierarchy_name]["interrupts"] = {}
        repr_dict[ps.hierarchy_name]["parameters"] = {}
        repr_dict[ps.hierarchy_name]["driver"] = None
        repr_dict[ps.hierarchy_name]["device"] = None
        if "driver" in ps.ext and isinstance(ps.ext["driver"], DriverExtension):
            repr_dict[ps.hierarchy_name]["driver"] = ps.ext["driver"].driver 
            repr_dict[ps.hierarchy_name]["device"] = ps.ext["driver"].device

        for param in ps.parameters.values():
            repr_dict[ps.hierarchy_name]["parameters"][param.name] = param.value

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
