"""Main application entry point."""

import sys
import asyncio
import signal
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import qasync

from clibpard.utils.config import load_config, save_config
from clibpard.core import ClipboardSyncService
from clibpard.ui import MainWindow
from clibpard.ui.tray import SystemTray


class Application:
    """Main application controller."""

    def __init__(self):
        # Load config
        self.config = load_config()

        # Create Qt application
        self.qapp = QApplication.instance()
        if not self.qapp:
            self.qapp = QApplication(sys.argv)

        self.qapp.setApplicationName("Clibpard")
        self.qapp.setOrganizationName("Clibpard")

        # Create service
        self.service = ClipboardSyncService(self.config)

        # Create UI
        self.main_window = MainWindow(self.service)
        self.system_tray = SystemTray(self.service)

        # Connect signals
        self._connect_signals()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _connect_signals(self):
        """Connect UI signals."""
        # Tray signals
        self.system_tray.show_window_requested.connect(self._show_window)
        self.system_tray.toggle_sync_requested.connect(self._toggle_sync)
        self.system_tray.copy_last_requested.connect(self._copy_last_item)
        self.system_tray.add_device_requested.connect(self._add_device)
        self.system_tray.quit_requested.connect(self._quit)

    async def start(self):
        """Start the application."""
        print("Starting Clibpard...")

        # Start service
        await self.service.start()

        # Show UI
        if self.config.start_minimized:
            self.main_window.hide()
        else:
            self.main_window.show()

        # Show system tray
        if self.config.show_system_tray:
            self.system_tray.show()
            self.system_tray.show_message(
                "Clibpard Started", "Clipboard sync is running"
            )

        print("Clibpard started successfully!")

    async def stop(self):
        """Stop the application."""
        print("Stopping Clibpard...")

        # Save config
        save_config(self.config)

        # Stop service
        await self.service.stop()

        # Hide tray
        self.system_tray.hide()

        print("Clibpard stopped")

    def _show_window(self):
        """Show main window."""
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _toggle_sync(self, enabled: bool):
        """Toggle sync on/off."""
        self.service.toggle_sync(enabled)
        self.system_tray.update_sync_state(enabled)

        message = "Sync enabled" if enabled else "Sync disabled"
        self.system_tray.show_message("Clibpard", message)

    def _copy_last_item(self):
        """Copy last clipboard item."""
        asyncio.create_task(self._async_copy_last_item())

    async def _async_copy_last_item(self):
        """Async copy last item."""
        items = await self.service.get_recent_items(1)
        if items:
            item = items[0]
            if item.type == "text" and item.text_content:
                self.service.clipboard_monitor.set_clipboard_text(item.text_content)
            elif item.type == "image" and item.blob_path:
                self.service.clipboard_monitor.set_clipboard_image(Path(item.blob_path))

    def _add_device(self):
        """Show add device dialog."""
        self._show_window()
        # The main window will handle showing the dialog
        self.main_window.tabs.setCurrentIndex(1)  # Switch to Devices tab

    def _quit(self):
        """Quit application."""
        asyncio.create_task(self._async_quit())

    async def _async_quit(self):
        """Async quit."""
        await self.stop()
        self.qapp.quit()

    def _signal_handler(self, signum, frame):
        """Handle system signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self._quit()


async def async_main():
    """Async main function."""
    app = Application()

    try:
        await app.start()

        # Keep running until quit
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        await app.stop()


def main():
    """Main entry point."""
    # Setup Qt event loop with asyncio
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        # Create application
        application = Application()

        # Start service
        loop.create_task(application.start())

        # Run event loop
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            loop.run_until_complete(application.stop())


if __name__ == "__main__":
    main()
