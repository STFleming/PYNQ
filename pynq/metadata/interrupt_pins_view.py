from pynqmetadata import Module, Signal, Core
from typing import Dict, List
import json

def _default_repr(obj):
    return repr(obj)

class InterruptPinsView:
    """A view onto the interrupt controllers in the system"""

    def __init__(self, module: Module, controllers) -> None:
        self._md = module
        self._controllers = controllers

    def _walk_for_irq_pins(self, sig:Signal)->List[Signal]:
        """From and interrupt controller walk over connected concat blocks to 
        get all the pins that are connected"""
        ret: List[Signal] = []
        for dst in sig._connections.values():
            if dst.parent().parent().vlnv.name == "xlconcat":
                concat = dst.parent().parent()
                for port in concat.ports.values():
                    if port.name != "dout":
                        sig = port.sig()
                        ret = ret + self._walk_for_irq_pins(sig)
            else:
                ret.append(dst)
        return ret    

    @property
    def interrupt_pins(self) -> Dict:
        repr_dict = {}

        for ctrler_name in self._controllers:
            pins = []
            irq_controller = self._md.cores[ctrler_name]
            if "intr" in irq_controller.ports:
                pins = pins + self._walk_for_irq_pins(irq_controller.ports["intr"].sig())

            for irq_pin in pins:
                full_path = f"{irq_pin.parent().parent().hierarchy_name}/{irq_pin.name}"
                repr_dict[full_path] = {}
                repr_dict[full_path]["controller"] = irq_controller.hierarchy_name
                repr_dict[full_path]["index"] = 99
                repr_dict[full_path]["fullpath"] = full_path

        return repr_dict

    def items(self):
        return self.interrupt_pins.items()

    def __len__(self) -> int:
        return len(self.interrupt_pins)

    def __iter__(self):
        for ip in self.interrupt_pins:
            yield ip

    def _repr_json_(self) -> Dict:
        return json.loads(json.dumps(self.interrupt_pins, default=_default_repr))

    def __getitem__(self, key: str) -> None:
        return self.interrupt_pins[key]

    def __setitem__(self, key: str, value: object) -> None:
        """Set the state of an item in the interrupt_pins"""
        self._state[key] = value