from pynqmetadata import Module, Signal, Core
from pynqmetadata import MetadataExtension
from typing import Dict, List
import json
import re
from pydantic import Field

class InterruptControllerIndex(MetadataExtension):
    index:int = Field(..., description="The index for an interrupt controller in the PYNQ runtime")

def _default_repr(obj):
    return repr(obj)

class InterruptControllersView:
    """A view onto the interrupt controllers in the system"""

    def __init__(self, module: Module) -> None:
        self._md = module
        self._state = {}
        self._base_idx:int = 0

    def _walk_for_irq_controllers(self, sig:Signal)->List[Core]:
        """From a PS IRQ pin, walk out from it and the concat blocks collecting all 
        the interrupt controller blocks"""
        ret:List[Core] = []

        # Get the index number from the port name (stf: I don't like this)
        if sig.parent().parent().vlnv.name == "xlconcat":
            idx_re = re.search("In([0-9]+)", sig.name)
            if len(idx_re.groups()) == 1:
                #idx = int(idx_re.group(1)) + base_idx
                idx = self._base_idx
            else:
                raise ValueError(f"Trying to infer an interrupt index from the port name for {sig.ref} but it does not match the expected format signame={sig.name} groups={idx_re.groups()}") 
        else:
            idx = self._base_idx

        for dst in sig._connections.values():
            if dst.parent().parent().vlnv.name == "axi_intc":
                dst.parent().parent().ext["interrupt_controller_index"] = InterruptControllerIndex(index=idx)
                self._base_idx = self._base_idx + 1
                ret.append(dst.parent().parent())
            if dst.parent().parent().vlnv.name == "xlconcat":
                concat = dst.parent().parent()
                for port in concat.ports.values():
                    if port.name != "dout":
                        sig = port.sig()
                        ret = ret + self._walk_for_irq_controllers(sig)
        return ret    

    @property
    def interrupt_controllers(self) -> Dict:
        repr_dict = {}
        self._base_idx

        ps_list = self._md.get_processing_systems()
        if len(ps_list) > 1:
            raise RuntimeError(f"There is more than one processing system in the design, not sure how to proceed.")
        ps = ps_list[list(ps_list.keys())[0]]

        ps_irq_signals = ps.get_irqs

        # Find all the directly connected controllers to the ps
        controller_list = []
        for ps_irq in ps_irq_signals.values():
           controller_list = controller_list + self._walk_for_irq_controllers(ps_irq) 

        for controller in controller_list:
            repr_dict[controller.name] = {}
            repr_dict[controller.name]["parent"] = ""
            if "interrupt_controller_index" in controller.ext:
                repr_dict[controller.name]["index"] = controller.ext["interrupt_controller_index"].index 
            else:
                raise RuntimeError(f"Cannot determine the index for interrupt controller {controller.ref}")
            repr_dict[controller.name]["raw_irq"] = ps.irq_map[controller.ext["interrupt_controller_index"].index] 

        return repr_dict

    def items(self):
        return self.interrupt_controllers.items()

    def __len__(self) -> int:
        return len(self.interrupt_controllers)

    def __iter__(self):
        for ip in self.interrupt_controllers:
            yield ip

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.interrupt_controllers, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.interrupt_controllers[key]

    def __setitem__(self, key: str, value: object) -> None:
        """Set the state of an item in the interrupt_controllers"""
        self._state[key] = value
