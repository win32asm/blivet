#
# Copyright (C) 2016  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): David Lehman <dlehman@redhat.com>
#
import sys

import dbus

from blivet import Blivet
from .constants import BLIVET_INTERFACE, BLIVET_OBJECT_PATH
from .device import DBusDevice
from .object import DBusObject


class DBusBlivet(DBusObject):
    """ This class provides the main entry point to the Blivet1 service.

        It provides methods for controlling the blivet service and querying its
        state.
    """
    def __init__(self, manager):
        super().__init__()
        self._dbus_devices = list()
        self._manager = manager  # provides ObjectManager interface
        self._blivet = Blivet()

    @property
    def object_path(self):
        return BLIVET_OBJECT_PATH

    @property
    def interface(self):
        return BLIVET_INTERFACE

    @property
    def properties(self):
        props = {"Devices": self.ListDevices()}
        return props

    def _device_removed(self, device):
        """ Update ObjectManager interface after a device is removed. """
        removed_object_path = DBusDevice.get_object_path_by_id(device.id)
        removed = next((d for d in self._dbus_devices if d.object_path == removed_object_path))
        self._manager.remove_object(removed)
        self._dbus_devices.remove(removed)

    def _device_added(self, device):
        """ Update ObjectManager interface after a device is added. """
        added = DBusDevice(device)
        self._dbus_devices.append(added)
        self._manager.add_object(added)

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE)
    def Reset(self):
        """ Reset the Blivet instance and populate the device tree. """
        old_devices = self._blivet.devices[:]
        self._blivet.reset()
        for removed in old_devices:
            self._device_removed(removed)

        for added in self._blivet.devices:
            self._device_added(added)

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE)
    def Exit(self):
        """ Stop the blivet service. """
        sys.exit(0)

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, out_signature='ao')
    def ListDevices(self):
        """ Return a list of strings describing the devices in this system. """
        return dbus.Array([d.object_path for d in self._dbus_devices], signature='o')

    @dbus.service.method(dbus_interface=BLIVET_INTERFACE, in_signature='s', out_signature='o')
    def ResolveDevice(self, spec):
        """ Return a string describing the device the given specifier resolves to. """
        device = self._blivet.devicetree.resolve_device(spec)
        object_path = ""
        if device is not None:
            dbus_device = next(d for d in self._dbus_devices if d._device == device)
            object_path = dbus_device.object_path
        return object_path