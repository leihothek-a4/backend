import time

import dbus
from loguru import logger

from ...prelude.events import EventListener
from ...prelude.system import System
from ..dbus_context import DBusContextManager
from ..events.network_event import NetworkEvent

BUS_NAME = "com.bluetooth.Server"
OBJECT_PATH = "/com/bluetooth/Server"
INTERFACE = "com.bluetooth.Server"

RETRY_INTERVAL = 5.0


class BluetoothClient(System, EventListener):
    def __init__(self) -> None:
        System.__init__(self, name="BluetoothClient")
        EventListener.__init__(self)
        self._bus = DBusContextManager.get_bus()
        self._server: dbus.Interface | None = None
        self._next_attempt_at: float = 0.0
        self._pending_events: list[NetworkEvent] = []

    def on_attach(self) -> None:
        pass

    def on_start(self) -> None:
        self._subscribe_signals()
        self._next_attempt_at = time.monotonic()
        logger.info("BluetoothClient started.")

    def on_detach(self) -> None:
        pass

    def on_update(self) -> None:
        if time.monotonic() < self._next_attempt_at:
            return

        if self._server is None:
            if not self._acquire_server():
                self._next_attempt_at = time.monotonic() + RETRY_INTERVAL
                return
            self._flush_pending_events()

        self._attempt_connect()
        self._next_attempt_at = time.monotonic() + RETRY_INTERVAL

    def on_event(self, event: NetworkEvent) -> None:
        if self._server is None:
            logger.warning("Network disconnect — server unreachable, queuing event for later.")
            self._pending_events.append(event)
            return
        self._send_event(event)

    def _send_event(self, event: NetworkEvent) -> None:
        try:
            self._server.ReportNetworkDisconnect(
                event.prev_state, event.new_state, event.reason
            )
            logger.info(f"Network disconnect forwarded to server: {event.prev_state} → {event.new_state}")
        except dbus.DBusException as e:
            logger.error(f"Failed to report network disconnect: {e} — queuing event, dropping proxy.")
            self._pending_events.append(event)
            self._server = None

    def _flush_pending_events(self) -> None:
        if not self._pending_events:
            return
        logger.info(f"Server reconnected — flushing {len(self._pending_events)} pending event(s).")
        unsent: list[NetworkEvent] = []
        for event in self._pending_events:
            try:
                self._server.ReportNetworkDisconnect(
                    event.prev_state, event.new_state, event.reason
                )
                logger.info(f"Flushed pending disconnect: {event.prev_state} → {event.new_state}")
            except dbus.DBusException as e:
                logger.error(f"Flush failed: {e} — dropping proxy.")
                unsent.append(event)
                self._server = None
                break
        self._pending_events = unsent

    def _acquire_server(self) -> bool:
        try:
            proxy = self._bus.get_object(BUS_NAME, OBJECT_PATH)
            self._server = dbus.Interface(proxy, INTERFACE)
            logger.debug("Server proxy acquired.")
            return True
        except dbus.DBusException as e:
            logger.warning(f"Server not reachable yet: {e}")
            self._server = None
            return False

    def _attempt_connect(self) -> None:
        try:
            if not bool(self._server.HasDevice()):
                logger.debug("Server is still scanning — waiting.")
                return

            if bool(self._server.IsConnected()):
                logger.debug("Already connected — standing by.")
                return

            address = str(self._server.GetDeviceAddress())
            logger.info(f"Device [{address}] not connected — requesting connection ...")
            success = bool(self._server.Connect())
            if not success:
                logger.warning(f"Connection attempt failed, retrying in {RETRY_INTERVAL}s.")

        except dbus.DBusException as e:
            logger.error(f"DBus error: {e} — dropping server proxy, will re-acquire.")
            self._server = None

    def _subscribe_signals(self) -> None:
        DBusContextManager.add_signal_receiver(
            self._on_device_discovered,
            signal_name="DeviceDiscovered",
            dbus_interface=INTERFACE,
            bus_name=BUS_NAME,
            path=OBJECT_PATH,
        )
        DBusContextManager.add_signal_receiver(
            self._on_device_connected,
            signal_name="DeviceConnected",
            dbus_interface=INTERFACE,
            bus_name=BUS_NAME,
            path=OBJECT_PATH,
        )
        DBusContextManager.add_signal_receiver(
            self._on_device_disconnected,
            signal_name="DeviceDisconnected",
            dbus_interface=INTERFACE,
            bus_name=BUS_NAME,
            path=OBJECT_PATH,
        )
        logger.debug("Subscribed to server signals.")

    def _on_device_discovered(self, address: str, name: str) -> None:
        logger.info(f"[signal] Device discovered → {name}  [{address}]")
        self._next_attempt_at = time.monotonic()

    def _on_device_connected(self, address: str) -> None:
        logger.success(f"[signal] Device connected → {address}")

    def _on_device_disconnected(self, address: str) -> None:
        logger.warning(f"[signal] Device disconnected → {address}")
        self._next_attempt_at = time.monotonic()
