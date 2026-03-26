import dbus
import gi
from dbus.connection import SignalMatch
from dbus.mainloop.glib import DBusGMainLoop
from loguru import logger

gi.require_version("GLib", "2.0")

from gi.repository import GLib  # type: ignore


class DBusContextManager:
    _bus: dbus.SystemBus | None = None
    _context: GLib.MainContext | None = None

    @classmethod
    def init(cls) -> None:
        DBusGMainLoop(set_as_default=True)
        cls._bus = dbus.SystemBus()
        cls._context = GLib.MainContext.default()

        logger.debug("dbus context initialized")

    @classmethod
    def add_signal_receiver(
        cls,
        handler_function,
        signal_name=None,
        dbus_interface=None,
        bus_name=None,
        path=None,
        **keywords,
    ) -> SignalMatch:
        if cls._bus is None:
            logger.critical("DBusContextManager has not been initialized yet")
            raise NotImplementedError("DBusContextManager has not been initialized yet")

        return cls._bus.add_signal_receiver(
            handler_function,
            signal_name=signal_name,
            dbus_interface=dbus_interface,
            bus_name=bus_name,
            path=path,
            **keywords,
        )

    @classmethod
    def get_context(cls) -> GLib.MainContext:
        if cls._context is None:
            logger.critical("DBusContextManager has not been initialized yet")
            raise NotImplementedError("DBusContextManager has not been initialized yet")

        return cls._context

    @classmethod
    @logger.catch
    def get_bus(cls) -> dbus.SystemBus:
        if cls._bus is None:
            logger.critical("DBusContextManager has not been initialized yet")
            raise NotImplementedError("DBusContextManager has not been initialized yet")

        return cls._bus
