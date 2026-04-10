import threading
from abc import ABCMeta

import dbus
import dbus.service
import requests
from loguru import logger

from ...prelude.system import System
from ..dbus_context import DBusContextManager

BUS_NAME = "com.bluetooth.Server"
OBJECT_PATH = "/com/bluetooth/Server"
INTERFACE = "com.bluetooth.Server"

WEBHOOK_URL = "https://ntfy.sh/hanzeleihothek"

BLUEZ_SERVICE = "org.bluez"
BLUEZ_ADAPTER_IFACE = "org.bluez.Adapter1"
BLUEZ_DEVICE_IFACE = "org.bluez.Device1"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"


class _BluetoothServerMeta(type(dbus.service.Object), ABCMeta):
    pass


class BluetoothServer(dbus.service.Object, System, metaclass=_BluetoothServerMeta):
    def __init__(self) -> None:
        bus = DBusContextManager.get_bus()
        dbus.service.Object.__init__(self, bus, OBJECT_PATH)
        System.__init__(self, name="BluetoothServer")

        self._bus = bus
        self._adapter_iface: dbus.Interface | None = None
        self._device_path: str | None = None
        self._device_address: str = ""

    def on_attach(self) -> None:
        pass

    def on_start(self) -> None:
        dbus.service.BusName(BUS_NAME, self._bus)
        self._init_adapter()

        DBusContextManager.add_signal_receiver(
            self._on_interfaces_added,
            signal_name="InterfacesAdded",
            dbus_interface=OBJECT_MANAGER_IFACE,
            bus_name=BLUEZ_SERVICE,
        )

        self._select_from_known_devices()
        self._start_discovery()
        logger.info(f"BluetoothServer started — registered as {BUS_NAME}")

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        context = DBusContextManager.get_context()
        while context.iteration(may_block=False):
            pass

    def _init_adapter(self) -> None:
        manager = dbus.Interface(
            self._bus.get_object(BLUEZ_SERVICE, "/"),
            OBJECT_MANAGER_IFACE,
        )
        for path, ifaces in manager.GetManagedObjects().items():
            if BLUEZ_ADAPTER_IFACE in ifaces:
                self._adapter_iface = dbus.Interface(
                    self._bus.get_object(BLUEZ_SERVICE, path),
                    BLUEZ_ADAPTER_IFACE,
                )
                name = ifaces[BLUEZ_ADAPTER_IFACE].get("Name", "unknown")
                logger.info(f"Using BT adapter: {path}  ({name})")
                return
        logger.error("No Bluetooth adapter found — is BlueZ running?")

    def _start_discovery(self) -> None:
        if self._adapter_iface is None:
            logger.error("Cannot start discovery: no adapter.")
            return
        try:
            self._adapter_iface.StartDiscovery()
            logger.info("BT discovery started (running indefinitely).")
        except dbus.DBusException as e:
            if "org.bluez.Error.InProgress" in str(e):
                logger.debug("Discovery already in progress.")
            else:
                logger.error(f"StartDiscovery failed: {e}")

    def _select_device(self, path: str, props: dict) -> None:
        address = str(props.get("Address", "unknown"))
        name = str(props.get("Name", "unnamed"))
        paired = bool(props.get("Paired", False))

        if self._device_path is None or paired:
            self._device_path = path
            self._device_address = address
            logger.success(f"Device selected: {name}  [{address}]  (paired={paired})")
            self.DeviceDiscovered(address, name)

    def _select_from_known_devices(self) -> None:
        manager = dbus.Interface(
            self._bus.get_object(BLUEZ_SERVICE, "/"),
            OBJECT_MANAGER_IFACE,
        )
        for path, ifaces in manager.GetManagedObjects().items():
            if BLUEZ_DEVICE_IFACE in ifaces:
                self._select_device(str(path), ifaces[BLUEZ_DEVICE_IFACE])
                if self._device_path and bool(
                    ifaces[BLUEZ_DEVICE_IFACE].get("Paired", False)
                ):
                    break

    def _on_interfaces_added(self, path: str, interfaces: dict) -> None:
        if BLUEZ_DEVICE_IFACE in interfaces:
            logger.debug(f"InterfacesAdded: {path}")
            self._select_device(str(path), interfaces[BLUEZ_DEVICE_IFACE])

    def _get_device_props(self) -> dict | None:
        if self._device_path is None:
            return None
        try:
            return dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE, self._device_path),
                PROPERTIES_IFACE,
            ).GetAll(BLUEZ_DEVICE_IFACE)
        except dbus.DBusException as e:
            logger.warning(f"Could not read device properties: {e}")
            return None

    @dbus.service.method(INTERFACE, in_signature="", out_signature="b")
    def HasDevice(self) -> bool:
        return self._device_path is not None

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetDeviceAddress(self) -> str:
        return self._device_address

    @dbus.service.method(INTERFACE, in_signature="", out_signature="b")
    def IsConnected(self) -> bool:
        props = self._get_device_props()
        return bool(props.get("Connected", False)) if props else False

    @dbus.service.method(INTERFACE, in_signature="", out_signature="b")
    def Connect(self) -> bool:
        if self._device_path is None:
            logger.warning("Connect called but no device selected yet.")
            return False
        try:
            dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE, self._device_path),
                BLUEZ_DEVICE_IFACE,
            ).Connect()
            logger.success(f"Connected to {self._device_address}")
            self.DeviceConnected(self._device_address)
            return True
        except dbus.DBusException as e:
            logger.error(f"Connect failed: {e}")
            return False

    @dbus.service.method(INTERFACE, in_signature="", out_signature="b")
    def Disconnect(self) -> bool:
        if self._device_path is None:
            return False
        try:
            dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE, self._device_path),
                BLUEZ_DEVICE_IFACE,
            ).Disconnect()
            logger.info(f"Disconnected from {self._device_address}")
            self.DeviceDisconnected(self._device_address)
            return True
        except dbus.DBusException as e:
            logger.error(f"Disconnect failed: {e}")
            return False

    @dbus.service.method(INTERFACE, in_signature="", out_signature="s")
    def GetStatus(self) -> str:
        if self._device_path is None:
            return "scanning — no device yet"
        state = "connected" if self.IsConnected() else "disconnected"
        return f"{self._device_address} — {state}"

    @dbus.service.method(INTERFACE, in_signature="sss", out_signature="")
    def ReportNetworkDisconnect(
        self, prev_state: str, new_state: str, reason: str
    ) -> None:
        logger.warning(
            f"[client] Network disconnect: {prev_state} → {new_state}  ({reason})"
        )
        self.NetworkDisconnected(prev_state, new_state, reason)
        threading.Thread(
            target=self._post_disconnect_webhook,
            args=(prev_state, new_state, reason),
            daemon=True,
        ).start()

    def _post_disconnect_webhook(
        self, prev_state: str, new_state: str, reason: str
    ) -> None:
        try:
            response = requests.post(
                WEBHOOK_URL,
                json={
                    "prev_state": prev_state,
                    "new_state": new_state,
                    "reason": reason,
                },
                timeout=10,
            )
            logger.debug(f"Webhook response: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Webhook POST failed: {e}")

    @dbus.service.signal(INTERFACE, signature="ss")
    def DeviceDiscovered(self, address: str, name: str):
        pass

    @dbus.service.signal(INTERFACE, signature="s")
    def DeviceConnected(self, address: str):
        pass

    @dbus.service.signal(INTERFACE, signature="s")
    def DeviceDisconnected(self, address: str):
        pass

    @dbus.service.signal(INTERFACE, signature="sss")
    def NetworkDisconnected(self, prev_state: str, new_state: str, reason: str):
        pass
