import json
from pynqmetadata import Module, ProcSysCore, ManagerPort, Core
from pynqmetadata.errors import FeatureNotYetImplemented
from pynqmetadata.errors import MetadataObjectNotFound

from typing import Dict

from ..utils import ReprDict

def _default_repr(obj):
    return repr(obj)

class MemDictView:
    """
    Provides a view onto the metadata that mirrors the structure of mem_dict.
    """

    def __init__(self, module: Module) -> None:
        self._md = module

    @property
    def mem_dict(self) -> Dict:
        repr_dict = {}

        # add the PS DDR
        for core in self._md.cores.values():
            for port in core.ports.values():
                if isinstance(port, ManagerPort):
                    for addr in port.addrmap.values():
                        if addr["memtype"] == "memory":
                            subord_port = port._addrmap_obj[addr["subord_port"]]
                            if isinstance(subord_port.parent(), ProcSysCore):
                                if "PSDDR" not in repr_dict:
                                    repr_dict["PSDDR"] = {}

        ps_core = None
        for core in self._md.cores.values():
            if isinstance(core, ProcSysCore):
                ps_core = core 
        
        if ps_core is None:
            raise MetadataObjectNotFound(f"Unable to find a PS in {self._md.ref}")

        for port in ps_core.ports.values():
            if isinstance(port, ManagerPort):
                for addr in port.addrmap.values():
                    if addr["memtype"] == "memory":
                        subord_port = port._addrmap_obj[addr["subord_port"]]
                        dst_core = subord_port.parent()
                        if isinstance(dst_core, Core):
                            repr_dict[dst_core.name] = {}
        

        return repr_dict

    def items(self):
        return self.mem_dict.items()

    def __len__(self) -> int:
        return len(self.mem_dict)

    def __iter__(self):
        for clock in self.mem_dict:
            yield clock 

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.mem_dict, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.mem_dict[key]

    def __setitem__(self, key: str, value: object) -> None:
        """TODO: needs to send value into the model bypassing ip_dict
        this will require view tranlation in the other direction"""
        raise FeatureNotYetImplemented("IPDictView is currently only read only")