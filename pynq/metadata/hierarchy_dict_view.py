from typing import Dict, List

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort
from pynqmetadata.errors import FeatureNotYetImplemented

from .append_drivers_pass import DriverExtension

def _default_repr(obj):
    return repr(obj)

class HierarchyDictView:
    """
    Provides a hierarchical view over the IP cores in the design using the hierarchical_name
    """

    def __init__(self, module: Module) -> None:
        self._md = module

    def _build_hierarchy(self, hier:Dict, new_items:List[str])->None:
        """ Recursively walks down hier adding items in new_items """
        if new_items[0] not in hier:
            hier[new_items[0]] = {}

        if len(new_items) > 1:
            next_items = new_items[1:]
            self._build_hierarchy(hier[new_items[0]], next_items)

    @property
    def hierarchy_dict(self) -> Dict:
        repr_dict = {}
        for core in self._md.cores.values():
            add_core = False
            for port in core.ports.values():
                if isinstance(port, SubordinatePort):
                    if len(port.registers)>1:
                        add_core = True
            if add_core:
                hier = core.hierarchy_name.split("/")
                self._build_hierarchy(repr_dict, hier)

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
