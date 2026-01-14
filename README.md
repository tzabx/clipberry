# Clibpard - Cross-Platform Clipboard Sync

Securely synchronize clipboard content (text, images, files) between trusted devices on Linux and macOS.

## Features

- 📋 Real-time clipboard sync (text and images)
- 🔒 Secure peer-to-peer with TLS encryption
- 🔍 Automatic device discovery (mDNS/Bonjour)
- 🎯 Loop prevention and deduplication
- 🖥️ Modern Qt interface with system tray
- 💾 Local SQLite storage with metadata
- 🔐 Token-based device pairing

## Architecture

```
src/clibpard/
├── core/           # Core service daemon
├── networking/     # WebSocket + TLS + discovery
├── clipboard/      # Clipboard monitoring
├── storage/        # SQLite database
├── security/       # Crypto, pairing, signatures
├── ui/             # Qt/PySide6 interface
└── utils/          # Helpers and common code
```

## Installation

```bash
pip install -r requirements.txt
python setup.py develop
```

## Usage

```bash
# Start the application
clibpard

# Or run from source
python -m clibpard.main
```

## Security Model

- Self-signed certificates per device
- Short-lived pairing tokens (6-8 characters)
- Certificate pinning and trust revocation
- Signed clipboard items with device keys
- No cloud dependency - peer-to-peer only

## Roadmap

- ✅ MVP: Text + image sync, pairing, discovery
- 🚧 Phase 2: Drag-and-drop file transfer
- 📅 Phase 3: End-to-end payload encryption
- 📅 Phase 4: Rules engine and scripting

## License

MIT
