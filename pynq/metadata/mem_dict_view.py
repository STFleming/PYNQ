import json
from pynqmetadata import Module, ProcSysCore, ManagerPort, Core
from pynqmetadata.errors import FeatureNotYetImplemented
from pynqmetadata.errors import MetadataObjectNotFound

from ..pl_server.embedded_device import _create_xclbin, _unify_dictionaries
from ..pl_server.xclbin_parser import XclBin

from .xrt_metadata_extension import XrtExtension

from typing import Dict

def _default_repr(obj):
    return repr(obj)

class DummyHwhParser:
    def __init__(self, mem_dict):
        self.mem_dict = mem_dict

class MemDictView:
    """
    Provides a view onto the metadata that mirrors the structure of mem_dict.
    """

    def __init__(self, module: Module) -> None:
        self._md = module
        self._first_run = True
        self._created_xclbin = {}

    @property
    def mem_dict(self) -> Dict:
        repr_dict = {}

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
                        subord_port = port.addrmap_obj[addr["subord_port"]]
                        dst_core = subord_port.parent()
                        if isinstance(dst_core, Core):
                            repr_dict[dst_core.hierarchy_name] = {}
                            repr_dict[dst_core.hierarchy_name]["fullpath"] = dst_core.hierarchy_name
                            repr_dict[dst_core.hierarchy_name]["type"] = "DDR4"
                            repr_dict[dst_core.hierarchy_name]["bdtype"] = None
                            repr_dict[dst_core.hierarchy_name]["state"] = None
                            repr_dict[dst_core.hierarchy_name]["addr_range"] = subord_port.range 
                            repr_dict[dst_core.hierarchy_name]["phys_addr"] = subord_port.baseaddr 
                            repr_dict[dst_core.hierarchy_name]["mem_id"] = subord_port.name 
                            repr_dict[dst_core.hierarchy_name]["memtype"] = "MEMORY" 
                            repr_dict[dst_core.hierarchy_name]["gpio"] = {}
                            repr_dict[dst_core.hierarchy_name]["interrupts"] = {}
                            repr_dict[dst_core.hierarchy_name]["parameters"] = {}
                            for param in dst_core.parameters.values():
                                repr_dict[dst_core.hierarchy_name]["parameters"][param.name] = param.value
                            repr_dict[dst_core.hierarchy_name]["registers"] = {}
                            for reg in subord_port.registers.values():
                                repr_dict[dst_core.hierarchy_name]["registers"][reg.name] = reg.dict()

                            repr_dict[dst_core.hierarchy_name]["used"] = 1 

        if self._first_run:
            xclbin_data = _create_xclbin(repr_dict) # Create all the XRT stuff 
            xclbin_parser = XclBin(xclbin_data=xclbin_data)
            hwh_parser = DummyHwhParser(mem_dict=repr_dict)
            _unify_dictionaries(hwh_parser=hwh_parser, xclbin_parser=xclbin_parser)
            for name,mem in repr_dict.items():
                if name != "PSDDR":
                    self._created_xclbin[name] = {} # cache it for later
                    self._created_xclbin[name]["xrt_mem_idx"] = repr_dict[name]["xrt_mem_idx"] 
                    self._created_xclbin[name]["raw_type"] = repr_dict[name]["raw_type"] 
                    self._created_xclbin[name]["base_address"] = repr_dict[name]["base_address"] 
                    self._created_xclbin[name]["size"] = repr_dict[name]["size"] 
                    self._created_xclbin[name]["streaming"] = repr_dict[name]["streaming"] 
                    self._created_xclbin[name]["idx"] = repr_dict[name]["idx"] 
                    self._created_xclbin[name]["tag"] = repr_dict[name]["tag"] 
            self._first_run = False
        else:
            for name,mem in repr_dict.items(): # read it from the cache when regenerating
                if name != "PSDDR":
                    mem["xrt_mem_idx"] = self._created_xclbin[name]["xrt_mem_idx"]
                    mem["raw_type"] = self._created_xclbin[name]["raw_type"]
                    mem["base_address"] = self._created_xclbin[name]["base_address"]
                    mem["size"] = self._created_xclbin[name]["size"]
                    mem["streaming"] = self._created_xclbin[name]["streaming"]
                    mem["idx"] = self._created_xclbin[name]["idx"]
                    mem["tag"] = self._created_xclbin[name]["tag"]

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