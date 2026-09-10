# PiAck

A file broker mailbox system designed to work with PiRelay, enabling secure file transfer and storage between users through a FastAPI-based REST API.

## Why PiAck?

PiAck provides a centralized mailbox system for file transfers, allowing users to:
- Send and receive files through a simple HTTP API
- Handle both small files (≤5MB) and large files (chunked uploads)
- Manage multiple recipient mailboxes
- Dynamically configure the server remotely
- Cache file transfers for reliability
- Support multipart file transfers

## Features

- **Chunked File Upload**: Supports large file transfers by splitting into configurable chunks (default 1MB)
- **Mailbox System**: Each user has their own mailbox directory for received files
- **Dynamic Configuration**: Update server settings remotely via `/config` endpoint
- **Caching**: Persistent cache for file storage and mailbox state
- **Multipart Responses**: Efficient handling of multiple file transfers
- **RESTful API**: Clean FastAPI-based interface

## Dependencies

- Python 3.8+
- fastapi >= 0.104.0
- uvicorn[standard] >= 0.24.0
- requests >= 2.31.0

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd PiAck
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## How to Use

### Starting the Server

Start the PiAck server with various options:

```bash
# Start with default settings (port 8080)
python src/main.py

# Start with debug mode and custom port
python src/main.py -d -p=9000

# Start with custom source directory and flush all directories
python src/main.py -s=/path/to/storage -f

# Show help menu
python src/main.py -h
```

### Command Line Options

- `-d, --debug, -D, --Debug` - Enable debug mode
- `-f, --flush, -F, --Flush` - Flush the source directory on startup
- `-s, --src=PATH` - Set source directory path
- `-p, --port=PORT` - Set server port (default: 8080)
- `-h, --help` - Show help menu

### Configuration

Update server configuration dynamically by sending a POST request to `/config`:

```bash
curl -X POST http://localhost:8080/config \
  -H "Content-Type: application/json" \
  -d '{
    "flush": ["/path1", "/path2"],
    "declutter": "true",
    "port": 9000,
    "block": ["user1", "user2"],
    "command": "shell command",
    "down": true,
    "delete": ["mailbox1"],
    "add": ["mailbox2"],
    "chname": ["old_name", "new_name"]
  }'
```

## API Endpoints

### POST /config
Update server configuration dynamically.

**Headers**: `Content-Type: application/json`

**Body**: JSON config object
```json
{
  "flush": ["/path1", "/path2"],      // List of directories to flush
  "declutter": "true",                // Remove all files from ROOT (keep dirs)
  "port": 9000,                       // Change server port (triggers restart)
  "block": ["user1", "user2"],        // Add users to blocklist
  "command": "shell command",         // Execute shell command
  "down": true,                       // Set server down state
  "delete": ["mailbox1"],             // Delete mailboxes
  "add": ["mailbox2"],                // Add new mailboxes
  "chname": ["old_name", "new_name"]  // Rename mailboxes (pairs)
}
```

### POST /send/{recipient}/{file_id}
Send small file (≤ 5MB) via multipart form data.

**Headers**: `Content-Type: multipart/form-data`

**Form fields**:
- `file`: File data
- `file_id`: Unique file identifier
- `sender`: Sender username
- `relative_path`: Relative path for file

**Example**:
```bash
curl -X POST http://localhost:8080/send/user123/file_001 \
  -F "file=@/path/to/file.txt" \
  -F "file_id=file_001" \
  -F "sender=alice" \
  -F "relative_path=documents/file.txt"
```

### POST /send/{recipient}/{file_id}/{chunk_idx}
Send large file chunk (> 5MB).

**Headers**:
- `Content-Type: application/octet-stream`
- `X-Total-Chunks`: Total number of chunks
- `X-Sender`: Sender username
- `X-Relative-Path`: Relative path for file

**Body**: Raw chunk data

**Example**:
```bash
curl -X POST http://localhost:8080/send/user123/file_002/0 \
  -H "Content-Type: application/octet-stream" \
  -H "X-Total-Chunks: 5" \
  -H "X-Sender: alice" \
  -H "X-Relative-Path:videos/large_video.mp4" \
  --data-binary @chunk0.bin
```

### GET /recieve/
Receive files from mailbox (all senders).

**Headers**:
- `X-Receiver`: Receiver username

**Response**:
- Empty: JSON array `[]`
- Single file: Raw file data with `X-File-Name` header
- Multiple files: Multipart/form-data response

**Example**:
```bash
curl -X GET http://localhost:8080/recieve/ \
  -H "X-Receiver: bob" \
  -O -J
```

### GET /recieve/{sender}
Receive files from specific sender.

**Headers**:
- `X-Receiver`: Receiver username

**Response**:
- Empty: JSON array `[]`
- Single file: Raw file data with `X-File-Name` header
- Multiple files: Multipart/form-data response

**Example**:
```bash
curl -X GET http://localhost:8080/recieve/alice \
  -H "X-Receiver: bob" \
  -O -J
```

### GET /status
Check server status.

**Response**: `{"status": "ok"}`

### GET /health
Health check endpoint.

**Response**: `{"status": "ok"}`

## Constants

- **CHUNK_SIZE**: 1MB (1024 * 1024 bytes)
- **SMALL_FILE_SIZE**: 5MB (5 * 1024 * 1024 bytes)

## File Storage

Files are stored in memory as chunks until fully received, then saved to the recipient's mailbox directory. The system uses:
- **In-memory chunk storage**: Temporary storage during upload
- **Disk persistence**: Files saved to recipient directories after complete upload
- **Cache file**: `cache.json` stores metadata and mailbox state

## Project Structure

```
PiAck/
├── src/
│   ├── main.py       # FastAPI application and endpoints
│   ├── piack.py      # Core file handling logic
│   ├── consts.py     # Constants and documentation
│   ├── globals.py    # Global state and configuration
│   └── helper.py     # CLI argument parsing
├── requirements.txt  # Python dependencies
├── config.toml       # Project metadata
└── README.md         # This file
```

## Examples

### Complete Workflow

1. **Start the server**:
   ```bash
   python src/main.py -s=/tmp/piack_storage -p=8080
   ```

2. **Send a small file**:
   ```bash
   curl -X POST http://localhost:8080/send/bob/doc_001 \
     -F "file=@report.pdf" \
     -F "file_id=doc_001" \
     -F "sender=alice" \
     -F "relative_path=reports/report.pdf"
   ```

3. **Receive the file**:
   ```bash
   curl -X GET http://localhost:8080/recieve/ \
     -H "X-Receiver: bob" \
     -o received_file.pdf
   ```

4. **Configure server remotely**:
   ```bash
   curl -X POST http://localhost:8080/config \
     -H "Content-Type: application/json" \
     -d '{"port": 9000}'
   ```

## License

GPL-3.0-only - See LICENSE file for details.
