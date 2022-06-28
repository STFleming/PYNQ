from typing import Dict, List

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort, Hierarchy
from pynqmetadata.errors import FeatureNotYetImplemented

from .append_drivers_pass import DriverExtension
from .ip_dict_view import IpDictView
from .mem_dict_view import MemDictView

def _default_repr(obj):
    return repr(obj)

class HierarchyDictView:
    """
    Provides a hierarchical view over the IP cores in the design using the hierarchical_name
    """

    def __init__(self, module: Module) -> None:
        self._md = module
        self._ip_dict = IpDictView(self._md)
        self._mem_dict = MemDictView(self._md)

    def _hierarchy_walker(self, r:Dict, h:Hierarchy)->None:
        """ recursive walk down the hierarchy h, adding IP
        that is a match in ip_dict or mem_dict to the hierarchies
        """
        if h.name not in r:
            r[h.name] = {}
            r[h.name]["ip"] = {}
            r[h.name]["memories"] = {}
            r[h.name]["hierarchies"] = {}

        for ip in h.core_obj.values():
            if ip.hierarchy_name in self._ip_dict: 
                r[h.name]["ip"][ip.name] = ip.ref
            if ip.hierarchy_name in self._mem_dict:
                r[h.name]["memories"][ip.name] = ip.ref

        for hier in h.hierarchies_obj.values():
            self._hierarchy_walker(r[h.name]["hierarchies"], hier)

    def _prune_walker(self, r:Dict)->bool:
        """ Walks down through the hierarchy dict, removing anything
        that is empty """
        for item in r.values():
            empty = False

            if "hierarchies" in item:
                del_list = []
                for i,h in item["hierarchies"].items():
                    if self._prune_walker(h):
                        empty = True
                        del_list.append(i)

                for i in del_list:
                    del item["hierarchies"][i]

                return len(item["ip"]) == 0 and len(item["memories"]) == 0
            return True

    @property
    def hierarchy_dict(self) -> Dict:
        """
        Walks down the hierarchy dict and whenever it encounters an IP
        that is in the ip_dict or mem_dict keep it.
        """
        repr_dict = {}
        top_level = self._md.hierarchies
        for hierarchy in top_level.hierarchies_obj.values():
            self._hierarchy_walker(repr_dict, hierarchy)      
            self._prune_walker(repr_dict)

        return repr_dict

    def items(self):
        return self.hierarchy_dict.items()

    def __len__(self) -> int:
        return len(self.hierarchy_dict)

    def __iter__(self):
        for ip in self.hierarchy_dict:
            yield ip

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.hierarchy_dict, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.hierarchy_dict[key]

    def __setitem__(self, key: str, value: object) -> None:
        """TODO: needs to send value into the model bypassing ip_dict
        this will require view tranlation in the other direction"""
        raise FeatureNotYetImplemented("HierarcyDictView is currently only read only")
