import warnings
from typing import Dict

from pynqmetadata import Core, MetadataExtension, Module, ProcSysCore, SubordinatePort
from pynqmetadata.errors import UnexpectedMetadataObjectType

DRIVERS_GROUP = "pynq.lib"


def bind_driver(
    port: SubordinatePort,
    device: object,
    ip_drivers: Dict[str, object],
    default_ip: object,
    ignore_version: bool = False,
) -> None:
    """Assigns a driver to this port"""
    core = port.parent()
    if isinstance(core, Core):
        if core.vlnv.str in ip_drivers:
            port._ext["driver"] = ip_drivers[core.vlnv.str]
            port._ext["device"] = device
        else:
            no_version_ip = core.vlnv.str.rpartition(":")[0]
            if no_version_ip in ip_drivers:
                if ignore_version:
                    port._ext["driver"] = ip_drivers[no_version_ip]
                    port._ext["device"] = device
                else:
                    other_versions = [
                        v
                        for v in ip_drivers.keys()
                        if v.startswith(f"{no_version_ip}:")
                    ]
                    message = f"IP {core.ref} is of type {core.vlnv.str} a driver has been found for {other_versions}. Use ignore_version=True to use this driver."
                    warnings.warn(message, UserWarning)
                    port._ext["driver"] = default_ip
                    port._ext["device"] = device
            else:
                port._ext["driver"] = default_ip
                port._ext["device"] = device
    else:
        raise UnexpectedMetadataObjectType(
            f"Trying to bind driver to {port.ref} but it has no parent"
        )

def bind_ps_driver(
    core:ProcSysCore,
    device: object,
    ip_drivers: Dict[str,object],
    default_ip: object,
    ignore_version: bool = False
) -> None:
    """Assigns a driver to the PS"""
    if core.vlnv.str in ip_drivers:
        core._ext["driver"] = ip_drivers[core.vlnv.str]
        core._ext["device"] = device
    else:
        no_version_ip = core.vlnv.str.rpartition(":")[0]
        if no_version_ip in ip_drivers:
            if ignore_version:
                core._ext["driver"] = ip_drivers[no_version_ip]
                core._ext["device"] = device
            else:
                other_versions = [
                    v
                    for v in ip_drivers.keys()
                    if v.startswith(f"{no_version_ip}:")
                ]
                message = f"IP {core.ref} is of type {core.vlnv.str} a driver has been found for {other_versions}. Use ignore_version=True to use this driver."
                warnings.warn(message, UserWarning)
                core._ext["driver"] = default_ip
                core._ext["device"] = device
        else:
            core._ext["driver"] = default_ip
            core._ext["device"] = device


def bind_drivers_to_metadata(
    md: Module, device: object, ip_drivers: Dict[str, object], default_ip: object
) -> Module:
    """Passes over the metadata and for each subordinate port
    extends the metadata to include drivers bound to it"""
    for core in md.cores.values():
        for port in core.ports.values():
            if isinstance(port, SubordinatePort):
                if len(port.registers) > 0:
                    bind_driver(
                        port=port,
                        device=device,
                        ip_drivers=ip_drivers,
                        default_ip=default_ip,
                    )
        if isinstance(core, ProcSysCore):
            bind_ps_driver(
                core=core,
                device=device,
                ip_drivers=ip_drivers,
                default_ip=default_ip,
            )
            

    return md
