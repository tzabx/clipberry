"""System tray integration."""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Signal, QObject


class SystemTray(QObject):
    """System tray icon and menu."""

    show_window_requested = Signal()
    toggle_sync_requested = Signal(bool)
    copy_last_requested = Signal()
    add_device_requested = Signal()
    quit_requested = Signal()

    def __init__(self, service):
        super().__init__()
        self.service = service

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setToolTip("Clibpard - Clipboard Sync")

        # TODO: Add proper icon
        # For now, use default
        # icon = QIcon(":/icons/clibpard.png")
        # self.tray_icon.setIcon(icon)

        # Create menu
        self._create_menu()

        # Connect signals
        self.tray_icon.activated.connect(self._on_activated)

    def _create_menu(self):
        """Create tray menu."""
        menu = QMenu()

        # Show/Hide action
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(show_action)

        menu.addSeparator()

        # Sync toggle
        self.sync_action = QAction("Sync Enabled", self)
        self.sync_action.setCheckable(True)
        self.sync_action.setChecked(self.service.is_sync_enabled())
        self.sync_action.triggered.connect(
            lambda checked: self.toggle_sync_requested.emit(checked)
        )
        menu.addAction(self.sync_action)

        menu.addSeparator()

        # Copy last item
        copy_last_action = QAction("Copy Last Item", self)
        copy_last_action.triggered.connect(self.copy_last_requested.emit)
        menu.addAction(copy_last_action)

        # Add device
        add_device_action = QAction("Add Device", self)
        add_device_action.triggered.connect(self.add_device_requested.emit)
        menu.addAction(add_device_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def show(self):
        """Show tray icon."""
        self.tray_icon.show()

    def hide(self):
        """Hide tray icon."""
        self.tray_icon.hide()

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window_requested.emit()

    def update_sync_state(self, enabled: bool):
        """Update sync state in menu."""
        self.sync_action.setChecked(enabled)

    def show_message(self, title: str, message: str):
        """Show tray notification."""
        from PySide6.QtWidgets import QSystemTrayIcon as TrayIcon

        self.tray_icon.showMessage(
            title, message, TrayIcon.MessageIcon.Information, 3000
        )
