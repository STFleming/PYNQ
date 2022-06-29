from typing import Dict, List
from pydantic import Field

import json
from pynqmetadata import Module, ProcSysCore, SubordinatePort, Hierarchy
from pynqmetadata.errors import FeatureNotYetImplemented

from .ip_dict_view import IpDictView
from .mem_dict_view import MemDictView
from pynqmetadata import MetadataExtension

def _default_repr(obj):
    return repr(obj)

class HierarchyDriverExetension(MetadataExtension):
    """Extends the metadata for hierarchies with PYNQ runtime driver information"""
    driver:object = Field(..., exclude=True, description="the runtime driver for this hierarchy")
    device:object = Field(..., exclude=True, description="the device this core has been loaded onto")
    overlay:object = Field(..., exclude=True, description="the overlay that this driver is associated with")

class HierarchyDictView:
    """
    Provides a hierarchical view over the IP cores in the design using the hierarchical_name
    """

    def __init__(self, 
                module: Module, 
                ip_view:IpDictView, 
                mem_view:MemDictView, 
                overlay: object,
                hierarchy_drivers:object,
                default_hierarchy:object,
                device:object) -> None:

        self._md = module
        self._ip_dict = ip_view
        self._mem_dict = mem_view
        self._hierarchy_drivers = hierarchy_drivers
        self._default_hierarchy = default_hierarchy
        self._device = device
        self._overlay = overlay

    def _hierarchy_walker(self, r:Dict, h:Hierarchy)->None:
        """ recursive walk down the hierarchy h, adding IP
        that is a match in ip_dict or mem_dict to the hierarchies
        """
        if h.name not in r:
            r[h.name] = {}
            r[h.name]["ip"] = {}
            r[h.name]["memories"] = {}
            r[h.name]["hierarchies"] = {}
            r[h.name]["interrupts"] = {}
            r[h.name]["gpio"] = {}
            r[h.name]["fullpath"] = h.path
            r[h.name]["md_ref"] = h

        for ip in h.core_obj.values():
            if ip.hierarchy_name in self._mem_dict:
                name = ip.hierarchy_name.split("/")[-1]
                r[h.name]["memories"][name] = self._mem_dict[ip.hierarchy_name]
            else:
                if ip.hierarchy_name in self._ip_dict: 
                    name = ip.hierarchy_name.split("/")[-1]
                    r[h.name]["ip"][name] = self._ip_dict[ip.hierarchy_name] 

        for hier in h.hierarchies_obj.values():
            self._hierarchy_walker(r[h.name]["hierarchies"], hier)

    def _prune_unused_walker(self, r:Dict)->bool:
        """ Walks down through the hierarchy dict, removing anything
        that is empty """
        del_list = []
        for i,h in r["hierarchies"].items():
            if self._prune_unused_walker(h):
                del_list.append(i)

        for i in del_list:
            del r["hierarchies"][i]

        return len(r["ip"])==0 and len(r["memories"])==0 and len(r["hierarchies"])==0

    def _replicate_subhierarchies(self, add_to_root:Dict, l:Dict)->None:
        """ The original hierarchy dict includes the sub-hierarchies
        of other hierarchies at the root of the hierarchy_dict.
        This walks through and appends the sub-hierarchies to the root. 
        """
        for hname,h in l["hierarchies"].items():
            add_to_root[h["fullpath"]] = h
            self._replicate_subhierarchies(add_to_root=add_to_root, l=h)

    def _assign_drivers(self, hier_dict:Dict)->None:
        """Assigns drivers to the hierarchy if the pattern matches
        in the driver class.
        
        Uses metadata extensions to append the driver information. First
        checks to see that there is not already a driver assigned."""
        for hier in hier_dict["hierarchies"].values():
            self._assign_drivers(hier_dict=hier)

        if "driver" not in hier_dict["md_ref"].ext:
            driver = self._default_hierarchy
            for hip in self._hierarchy_drivers:
                if hip.checkhierarchy(hier_dict):
                    driver = hip
                    break #taken 
            hier_dict["md_ref"].ext["driver"] = HierarchyDriverExetension(device=self._device, driver=driver, overlay=self._overlay)
            hier_dict["device"] = self._device
            hier_dict["driver"] = driver 
            hier_dict["overlay"] = self._overlay 
        else:
            hier_dict["device"] = hier_dict["md_ref"].ext["driver"].device 
            hier_dict["driver"] = hier_dict["md_ref"].ext["driver"].driver 
            hier_dict["overlay"] = hier_dict["md_ref"].ext["driver"].overlay 

    def _cleanup_metadata_hierarchy_references(self, hier_dict:Dict)->None:
        """"Removes any reference to the metadata hierarchy objects from
        the dictionary"""
        if "md_ref" in hier_dict:
            del hier_dict["md_ref"]
        for hier in hier_dict["hierarchies"].values():
            self._cleanup_metadata_hierarchy_references(hier)

    @property
    def hierarchy_dict(self) -> Dict:
        """
        Walks down the hierarchy dict and whenever it encounters an IP
        that is in the ip_dict or mem_dict keep it.
        """
        repr_dict = {}
        top_level = self._md.hierarchies

        # Build up the hierarchies
        for hierarchy in top_level.hierarchies_obj.values():
            self._hierarchy_walker(repr_dict, hierarchy)      

        # Prune hierarchies that are not used
        for item in repr_dict.values():
            self._prune_unused_walker(item)

        # Remove anything at the root that has nothing beneath it
        del_list = []
        for i_name, i in repr_dict.items():
            if len(i["ip"])==0 and len(i["memories"])==0 and len(i["hierarchies"])==0:
                del_list.append(i_name)

        # Remove everything flagged for removal
        for d in del_list:
            del repr_dict[d]

        # the extra sub-hierarchies add them to the root
        add_to_root = {}
        for item in repr_dict.values():
            self._replicate_subhierarchies(add_to_root, item)

        for iname, i in add_to_root.items():
            repr_dict[iname] = i

        # Assign drivers to all the hierarchies (Writes into the central metadata with a metadata extension)
        # If a driver is already associated with the hierarchy then grab that
        for item in repr_dict.values(): 
            self._assign_drivers(item)

        # remove any references to the metadata hierarchies in the dict
        for item in repr_dict.values():
            self._cleanup_metadata_hierarchy_references(item)

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
