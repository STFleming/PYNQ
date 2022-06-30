from pynqmetadata import Module, Signal, Core
from typing import Dict, List
import json


def _default_repr(obj):
    return repr(obj)

class InterruptControllersView:
    """A view onto the interrupt controllers in the system"""

    def __init__(self, module: Module) -> None:
        self._md = module
        self._state = {}

    def _walk_for_irq_controllers(self, sig:Signal)->List[Core]:
        """From a PS IRQ pin, walk out from it and the concat blocks collecting all 
        the interrupt controller blocks"""
        ret:List[Core] = []
        for dst in sig._connections.values():
            if dst.parent().parent().vlnv.name == "axi_intc":
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

        ps_list = self._md.get_processing_systems()
        if len(ps_list) > 1:
            raise RuntimeError(f"There is more than one processing system in the design, not sure how to proceed.")
        ps = ps_list[list(ps_list.keys())[0]]

        ps_irq_signals = ps.get_irqs()

        # Find all the directly connected controllers to the ps
        controller_list = []
        for ps_irq in ps_irq_signals.values():
           controller_list = controller_list + self._walk_for_irq_controllers(ps_irq) 

        for controller in controller_list:
            repr_dict[controller.name] = {}
            repr_dict[controller.name]["parent"] = ""
            repr_dict[controller.name]["index"] = 99 
            repr_dict[controller.name]["raw_irq"] = 99 


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
