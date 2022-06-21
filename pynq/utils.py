#   Copyright (c) 2020, Xilinx, Inc.
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
import shutil
import tempfile
from distutils.dir_util import copy_tree, remove_tree, mkpath
from distutils.file_util import copy_file
from distutils.command.build import build as dist_build
from setuptools.command.build_py import build_py as _build_py


__author__ = "Giuseppe Natale"
__copyright__ = "Copyright 2020, Xilinx"
__email__ = "pynq_support@xilinx.com"


_function_text = """
import json

def _default_repr(obj):
    return repr(obj)

def _resolve_global(name):
    g = globals()
    return g[name] if name in g else None

"""

def _detect_devices(active_only=False):
    """Return a list containing all the detected devices names."""
    from pynq.pl_server import Device
    devices = Device.devices
    if not devices:
        raise RuntimeError("No device found in the system")
    if active_only:
        return Device.active_device.name
    return [d.name for d in devices]


def _resolve_global_overlay_res(overlay_res_link, src_path, logger,
                                fail=False):
    """Resolve resource that is global to every device (using a ``device=None``
    when calling ``_find_remote_overlay_res``). File is downloaded in
    ``src_path``.
    """
    overlay_res_filename = os.path.splitext(overlay_res_link)[0]
    overlay_res_download_dict = \
        _find_remote_overlay_res(None,
                                 os.path.join(src_path, overlay_res_link))
    if overlay_res_download_dict:
        overlay_res_fullpath = os.path.join(
            src_path, overlay_res_filename)
        try:
            logger.info("Downloading file '{}'. "
                        "This may take a while"
                        "...".format(
                            overlay_res_filename))
            _download_file(
                overlay_res_download_dict["url"],
                overlay_res_fullpath,
                overlay_res_download_dict["md5sum"])
        except Exception as e:
            if fail:
                raise e
        finally:
            if not os.path.isfile(
                    overlay_res_fullpath):
                err_msg = "Could not resolve file '{}'".format(
                    overlay_res_filename)
                logger.info(err_msg)
            else:
                return True  # overlay_res_download_dict was not empty
    return False


def _resolve_devices_overlay_res_helper(device, src_path, overlay_res_filename,
                                        overlay_res_link, overlay_res_fullpath,
                                        logger, fail=False,
                                        overlay_res_download_path=None):
    """Helper function for `_resolve_devices_overlay_res`."""
    overlay_res_src_path = _find_local_overlay_res(device,
                                                   overlay_res_filename,
                                                   src_path)
    err_msg = "Could not resolve file '{}' for " \
              "device '{}'".format(overlay_res_filename, device)
    if not overlay_res_src_path:
        overlay_res_download_dict = _find_remote_overlay_res(
            device, os.path.join(src_path, overlay_res_link))
        if overlay_res_download_dict:
            if overlay_res_download_path:
                mkpath(overlay_res_download_path)
            try:
                logger.info("Downloading file '{}'. This may take a while"
                            "...".format(overlay_res_filename))
                _download_file(
                    overlay_res_download_dict["url"],
                    overlay_res_fullpath,
                    overlay_res_download_dict["md5sum"])
            except Exception as e:
                if fail:
                    raise e
            finally:
                if not os.path.isfile(
                        overlay_res_fullpath):
                    logger.info(err_msg)
                if overlay_res_download_path and \
                        len(os.listdir(overlay_res_download_path)) == 0:
                    os.rmdir(overlay_res_download_path)
        else:
            if fail:
                raise OverlayNotFoundError(err_msg)
            logger.info(err_msg)


def _resolve_devices_overlay_res(overlay_res_link, src_path, devices, logger,
                                 fail=False):
    """Resolve ``overlay_res.ext`` file for every device in ``devices``.
    Files are downloaded in a ``overlay_res.ext.d`` folder in ``src_path``.
    If the device is only one and is an edge device, file is resolved directly
    to ``overlay_res.ext``.
    """
    from pynq.pl_server.device import Device 
    from pynq.pl_server.embedded_device import EmbeddedDevice
    overlay_res_filename = os.path.splitext(overlay_res_link)[0]
    if len(devices) == 1 and type(Device.devices[0]) == EmbeddedDevice:
        overlay_res_fullpath = os.path.join(src_path, overlay_res_filename)
        _resolve_devices_overlay_res_helper(devices[0], src_path,
                                            overlay_res_filename,
                                            overlay_res_link,
                                            overlay_res_fullpath, logger, fail)
        return
    for device in devices:
        overlay_res_download_path = os.path.join(
            src_path, overlay_res_filename + ".d")
        overlay_res_filename_split = \
            os.path.splitext(overlay_res_filename)
        overlay_res_filename_ext = "{}.{}{}".format(
            overlay_res_filename_split[0], device,
            overlay_res_filename_split[1])
        overlay_res_fullpath = os.path.join(overlay_res_download_path,
                                            overlay_res_filename_ext)
        _resolve_devices_overlay_res_helper(device, src_path,
                                            overlay_res_filename,
                                            overlay_res_link,
                                            overlay_res_fullpath, logger, fail,
                                            overlay_res_download_path)


def _resolve_all_overlay_res_from_link(overlay_res_link, src_path, logger,
                                       fail=False):
    """Resolve every entry of ``.link`` files regardless of detected devices.
    """
    overlay_res_filename = os.path.splitext(overlay_res_link)[0]
    with open(os.path.join(src_path, overlay_res_link)) as f:
        links = json.load(f)
    if not _resolve_global_overlay_res(overlay_res_link, src_path, logger,
                                       fail):
        for device, download_link_dict in links.items():
            if not _find_local_overlay_res(
                    device, overlay_res_filename, src_path):
                err_msg = "Could not resolve file '{}' for " \
                    "device '{}'".format(overlay_res_filename, device)
                overlay_res_download_path = os.path.join(
                    src_path, overlay_res_filename + ".d")
                overlay_res_filename_split = \
                    os.path.splitext(overlay_res_filename)
                overlay_res_filename_ext = "{}.{}{}".format(
                    overlay_res_filename_split[0], device,
                    overlay_res_filename_split[1])
                mkpath(overlay_res_download_path)
                overlay_res_fullpath = os.path.join(
                    overlay_res_download_path,
                    overlay_res_filename_ext)
                try:
                    logger.info("Downloading file '{}'. "
                                "This may take a while"
                                "...".format(
                                    overlay_res_filename))
                    _download_file(
                        download_link_dict["url"],
                        overlay_res_fullpath,
                        download_link_dict["md5sum"])
                except Exception as e:
                    if fail:
                        raise e
                finally:
                    if not os.path.isfile(
                            overlay_res_fullpath):
                        logger.info(err_msg)
                    if len(os.listdir(
                            overlay_res_download_path)) == 0:
                        os.rmdir(overlay_res_download_path)


def download_overlays(path, download_all=False, fail_at_lookup=False,
                      fail_at_device_detection=False, cleanup=False):
    """Download overlays for detected devices in destination path.

    Resolve ``overlay_res.ext`` files from  ``overlay_res.ext.link``
    json files. Downloaded ``overlay_res.ext`` files are put in a
    ``overlay_res.ext.d`` directory, with the device name added to their
    filename, as ``overlay_res.device_name.ext``.
    If the detected device is only one and is an edge device, target file is
    resolved directly to ``overlay_res.ext``.
    If target ``overlay_res.ext`` already exists, resolution is skipped.

    Parameters
    ----------
        path: str
            The path to inspect for overlays installation
        download_all: bool
            Causes all overlays to be downloaded from .link files, regardless
            of the detected devices.
        fail_at_lookup: bool
            Determines whether the function should raise an exception in case
            overlay lookup fails.
        fail_at_device_detection: bool
            Determines whether the function should raise an exception in case
            no device is detected.
        cleanup: bool
            Dictates whether .link files need to be deleted after resolution.
            If `True`, all .link files are removed as last step.
    """
    logger = get_logger()
    try:
        devices = _detect_devices()
    except RuntimeError as e:
        if fail_at_device_detection:
            raise e
        devices = []
    cleanup_list = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(".link"):
                if not download_all:
                    if not _resolve_global_overlay_res(f, root, logger,
                                                       fail_at_lookup):
                        _resolve_devices_overlay_res(f, root, devices, logger,
                                                     fail_at_lookup)
                else:  # download all overlays regardless of detected devices
                    _resolve_all_overlay_res_from_link(f, root, logger,
                                                       fail_at_lookup)
                if cleanup:
                    cleanup_list.append(os.path.join(root, f))
    for f in cleanup_list:
        os.remove(f)


class _download_overlays(dist_build):
    """Custom distutils command to download overlays using .link files."""
    description = "Download overlays using .link files"
    user_options = [("download-all", "a",
                     "forcibly download every overlay from .link files, "
                     "overriding download based on detected devices"),
                    ("force-fail", "f",
                     "Do not complete setup if overlays lookup fails.")]
    boolean_options = ["download-all", "force-fail"]

    def initialize_options(self):
        self.download_all = False
        self.force_fail = False

    def finalize_options(self):
        pass

    def run(self):
        cmd = self.get_finalized_command("build_py")
        for package, _, build_dir, _ in cmd.data_files:
            if "." not in package:  # sub-packages are skipped
                download_overlays(build_dir,
                                  download_all=self.download_all,
                                  fail_at_lookup=self.force_fail)


class build_py(_build_py):
    """Overload the standard setuptools 'build_py' command to also call the
    command 'download_overlays'.
    """
    def run(self):
        super().run()
        self.run_command("download_overlays")


class NotebookResult:
    """Class representing the result of executing a notebook

    Contains members with the form ``_[0-9]*`` with the output object for
    each cell or ``None`` if the cell did not return an object.

    The raw outputs are available in the ``outputs`` attribute. See the
    Jupyter documentation for details on the format of the dictionary

    """
    def __init__(self, nb):
        self.outputs = [
            c['outputs'] for c in nb['cells'] if c['cell_type'] == 'code'
        ]
        objects = json.loads(self.outputs[-1][0]['text'])
        for i, o in enumerate(objects):
            setattr(self, "_" + str(i+1), o)


def _create_code(num):
    call_line = "print(json.dumps([{}], default=_default_repr))".format(
        ", ".join(("_resolve_global('_{}')".format(i+1) for i in range(num))))
    return _function_text + call_line


def run_notebook(notebook, root_path=".", timeout=30, prerun=None):
    """Run a notebook in Jupyter

    This function will copy all of the files in ``root_path`` to a
    temporary directory, run the notebook and then return a
    ``NotebookResult`` object containing the outputs for each cell.

    The notebook is run in a separate process and only objects that
    are serializable will be returned in their entirety, otherwise
    the string representation will be returned instead.

    Parameters
    ----------
    notebook : str
        The notebook to run relative to ``root_path``
    root_path : str
        The root notebook folder (default ".")
    timeout : int
        Length of time to run the notebook in seconds (default 30)
    prerun : function
        Function to run prior to starting the notebook, takes the
        temporary copy of root_path as a parameter

    """
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    with tempfile.TemporaryDirectory() as td:
        workdir = os.path.join(td, 'work')
        notebook_dir = os.path.join(workdir, os.path.dirname(notebook))
        shutil.copytree(root_path, workdir)
        if prerun is not None:
            prerun(workdir)
        fullpath = os.path.join(workdir, notebook)
        with open(fullpath, "r") as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(kernel_name='python3', timeout=timeout)
        code_cells = [c for c in nb['cells'] if c['cell_type'] == 'code']
        nb['cells'].append(
            nbformat.from_dict({'cell_type': 'code',
                                'metadata': {},
                                'source': _create_code(len(code_cells))}
                               ))
        ep.preprocess(nb, {'metadata': {'path': notebook_dir}})
        return NotebookResult(nb)
