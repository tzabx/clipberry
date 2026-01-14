"""Qt UI components."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QDialog,
    QLineEdit,
    QTextEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QSystemTrayIcon,
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QAction, QFont

from clibpard.storage import ClipboardItem, Device
from clibpard.utils import format_timestamp, format_size


class ClipboardItemWidget(QWidget):
    """Widget for displaying a clipboard item."""

    copy_requested = Signal(ClipboardItem)

    def __init__(self, item: ClipboardItem, device_name: str):
        super().__init__()
        self.item = item

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        # Type icon
        icon_label = QLabel()
        if item.type == "text":
            icon_label.setText("📝")
        elif item.type == "image":
            icon_label.setText("🖼️")
        else:
            icon_label.setText("📎")
        icon_label.setFont(QFont("", 20))
        layout.addWidget(icon_label)

        # Content info
        info_layout = QVBoxLayout()

        # Preview
        preview = QLabel()
        if item.type == "text" and item.text_content:
            preview_text = item.text_content[:100]
            if len(item.text_content) > 100:
                preview_text += "..."
            preview.setText(preview_text)
        elif item.type == "image":
            preview.setText(
                f"Image ({item.metadata.get('width')}x{item.metadata.get('height')})"
            )
        preview.setWordWrap(True)
        info_layout.addWidget(preview)

        # Metadata
        meta_text = f"{device_name} • {format_timestamp(item.timestamp)} • {format_size(item.size)}"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet("color: gray; font-size: 11px;")
        info_layout.addWidget(meta_label)

        layout.addLayout(info_layout, stretch=1)

        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(self.item))
        layout.addWidget(copy_btn)

        self.setLayout(layout)


class ClipboardTab(QWidget):
    """Clipboard items tab."""

    copy_requested = Signal(ClipboardItem)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("Recent Clipboard Items")
        header.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(header)

        # Items list
        self.items_list = QListWidget()
        self.items_list.setSpacing(2)
        layout.addWidget(self.items_list)

        self.setLayout(layout)

    def update_items(self, items: list[ClipboardItem], devices: dict[str, str]):
        """Update displayed items."""
        self.items_list.clear()

        for item in items:
            device_name = devices.get(item.origin_device_id, "Unknown")

            # Create custom widget
            widget = ClipboardItemWidget(item, device_name)
            widget.copy_requested.connect(self.copy_requested.emit)

            # Add to list
            list_item = QListWidgetItem(self.items_list)
            list_item.setSizeHint(widget.sizeHint())
            self.items_list.addItem(list_item)
            self.items_list.setItemWidget(list_item, widget)


class DevicesTab(QWidget):
    """Devices management tab."""

    add_device_requested = Signal()
    revoke_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Paired Devices")
        header.setFont(QFont("", 14, QFont.Bold))
        header_layout.addWidget(header)

        header_layout.addStretch()

        add_btn = QPushButton("+ Add Device")
        add_btn.clicked.connect(self.add_device_requested.emit)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Devices table
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(4)
        self.devices_table.setHorizontalHeaderLabels(
            ["Name", "Status", "Last Seen", "Actions"]
        )
        self.devices_table.horizontalHeader().setStretchLastSection(False)
        self.devices_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.devices_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.devices_table)

        self.setLayout(layout)

    def update_devices(self, devices: list[Device]):
        """Update displayed devices."""
        self.devices_table.setRowCount(len(devices))

        from clibpard.utils import utc_timestamp

        current_time = utc_timestamp()

        for row, device in enumerate(devices):
            # Name
            name_item = QTableWidgetItem(device.name)
            self.devices_table.setItem(row, 0, name_item)

            # Status
            is_online = (
                device.last_seen_timestamp
                and (current_time - device.last_seen_timestamp) < 300  # 5 minutes
            )
            status = "🟢 Online" if is_online else "⚫ Offline"
            status_item = QTableWidgetItem(status)
            self.devices_table.setItem(row, 1, status_item)

            # Last seen
            if device.last_seen_timestamp:
                last_seen = format_timestamp(device.last_seen_timestamp)
            else:
                last_seen = "Never"
            last_seen_item = QTableWidgetItem(last_seen)
            self.devices_table.setItem(row, 2, last_seen_item)

            # Actions
            revoke_btn = QPushButton("Revoke")
            revoke_btn.clicked.connect(
                lambda checked, did=device.id: self.revoke_requested.emit(did)
            )
            self.devices_table.setCellWidget(row, 3, revoke_btn)


class ActivityTab(QWidget):
    """Activity log tab."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Header
        header = QLabel("Activity Log")
        header.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(header)

        # Log view
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.log_view.clear)
        layout.addWidget(clear_btn)

        self.setLayout(layout)

    def add_log_entry(self, message: str):
        """Add entry to activity log."""
        from clibpard.utils import utc_now

        timestamp = utc_now().strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] {message}")


class AddDeviceDialog(QDialog):
    """Dialog for adding a new device."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Device")
        self.setModal(True)
        self.resize(500, 400)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "To pair with another device:\n"
            "1. Generate a pairing token on the host device\n"
            "2. Enter the host IP address and token below\n"
            "3. Click Connect"
        )
        layout.addWidget(instructions)

        # Host IP
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("Host IP:"))
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        ip_layout.addWidget(self.ip_input)
        layout.addLayout(ip_layout)

        # Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit()
        self.port_input.setText("9876")
        port_layout.addWidget(self.port_input)
        layout.addLayout(port_layout)

        # Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Token:"))
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("ABCD1234")
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)

        # Discovered devices section
        layout.addWidget(QLabel("\nOr select a discovered device:"))
        self.discovered_list = QListWidget()
        layout.addWidget(self.discovered_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.accept)
        button_layout.addWidget(connect_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_connection_info(self) -> tuple[str, int, str]:
        """Get entered connection information."""
        return (
            self.ip_input.text().strip(),
            int(self.port_input.text() or "9876"),
            self.token_input.text().strip().upper(),
        )

    def update_discovered_devices(self, devices: list[dict]):
        """Update list of discovered devices."""
        self.discovered_list.clear()
        for device in devices:
            item_text = f"{device['device_name']} ({device['ip']})"
            self.discovered_list.addItem(item_text)


class GenerateTokenDialog(QDialog):
    """Dialog for generating a pairing token."""

    def __init__(self, token: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pairing Token")
        self.setModal(True)
        self.resize(400, 200)

        self._init_ui(token)

    def _init_ui(self, token: str):
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "Share this token with the device you want to pair.\n"
            "Token expires in 5 minutes."
        )
        layout.addWidget(instructions)

        # Token display
        token_label = QLabel(token)
        token_label.setFont(QFont("Courier", 24, QFont.Bold))
        token_label.setAlignment(Qt.AlignCenter)
        token_label.setStyleSheet(
            "padding: 20px; background: #f0f0f0; border-radius: 5px;"
        )
        layout.addWidget(token_label)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.setWindowTitle("Clibpard - Clipboard Sync")
        self.resize(800, 600)

        self._init_ui()
        self._init_menu()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_data)
        self.update_timer.start(2000)  # Update every 2 seconds

    def _init_ui(self):
        # Central widget with tabs
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Tabs
        self.tabs = QTabWidget()

        self.clipboard_tab = ClipboardTab()
        self.clipboard_tab.copy_requested.connect(self._on_copy_item)
        self.tabs.addTab(self.clipboard_tab, "Clipboard")

        self.devices_tab = DevicesTab()
        self.devices_tab.add_device_requested.connect(self._on_add_device)
        self.devices_tab.revoke_requested.connect(self._on_revoke_device)
        self.tabs.addTab(self.devices_tab, "Devices")

        self.activity_tab = ActivityTab()
        self.tabs.addTab(self.activity_tab, "Activity")

        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _init_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Devices menu
        devices_menu = menubar.addMenu("Devices")

        add_action = QAction("Add Device", self)
        add_action.triggered.connect(self._on_add_device)
        devices_menu.addAction(add_action)

        generate_token_action = QAction("Generate Pairing Token", self)
        generate_token_action.triggered.connect(self._on_generate_token)
        devices_menu.addAction(generate_token_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _update_data(self):
        """Update UI data from service."""
        import asyncio

        asyncio.create_task(self._async_update_data())

    async def _async_update_data(self):
        """Async update of UI data."""
        try:
            # Get items and devices
            items = await self.service.get_recent_items(100)
            devices = await self.service.get_devices()

            # Build device name map
            device_map = {d.id: d.name for d in devices}
            device_map[self.service.config.device_id] = "This Device"

            # Update tabs
            self.clipboard_tab.update_items(items, device_map)
            self.devices_tab.update_devices(devices)

        except Exception as e:
            print(f"UI update error: {e}")

    def _on_copy_item(self, item: ClipboardItem):
        """Handle copy item request."""
        from pathlib import Path

        if item.type == "text" and item.text_content:
            self.service.clipboard_monitor.set_clipboard_text(item.text_content)
            self.activity_tab.add_log_entry(f"Copied text item to clipboard")
        elif item.type == "image" and item.blob_path:
            self.service.clipboard_monitor.set_clipboard_image(Path(item.blob_path))
            self.activity_tab.add_log_entry(f"Copied image item to clipboard")

    def _on_add_device(self):
        """Handle add device request."""
        dialog = AddDeviceDialog(self)

        if dialog.exec() == QDialog.Accepted:
            host, port, token = dialog.get_connection_info()

            if not host or not token:
                QMessageBox.warning(self, "Error", "Please enter host IP and token")
                return

            # Connect in background
            import asyncio

            asyncio.create_task(self._connect_to_device(host, port, token))

    async def _connect_to_device(self, host: str, port: int, token: str):
        """Connect to a device."""
        try:
            self.activity_tab.add_log_entry(f"Connecting to {host}:{port}...")

            device_id = await self.service.connect_to_device(host, port)

            if device_id:
                self.activity_tab.add_log_entry(f"Connected to device: {device_id}")
                QMessageBox.information(self, "Success", "Device paired successfully!")
            else:
                self.activity_tab.add_log_entry(f"Failed to connect to {host}:{port}")
                QMessageBox.warning(self, "Error", "Failed to connect to device")

        except Exception as e:
            self.activity_tab.add_log_entry(f"Connection error: {e}")
            QMessageBox.critical(self, "Error", f"Connection error: {e}")

    def _on_generate_token(self):
        """Generate pairing token."""
        token = self.service.generate_pairing_token()
        self.activity_tab.add_log_entry(f"Generated pairing token: {token}")

        dialog = GenerateTokenDialog(token, self)
        dialog.exec()

    def _on_revoke_device(self, device_id: str):
        """Handle device revocation."""
        reply = QMessageBox.question(
            self,
            "Revoke Device",
            "Are you sure you want to revoke trust for this device?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            import asyncio

            asyncio.create_task(self._revoke_device(device_id))

    async def _revoke_device(self, device_id: str):
        """Revoke device trust."""
        await self.service.revoke_device(device_id)
        self.activity_tab.add_log_entry(f"Revoked device: {device_id}")
        await self._async_update_data()

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Clibpard",
            "Clibpard v0.1.0\n\n"
            "Cross-platform clipboard synchronization\n"
            "Secure peer-to-peer sync with TLS encryption\n\n"
            "https://github.com/clibpard/clibpard",
        )
