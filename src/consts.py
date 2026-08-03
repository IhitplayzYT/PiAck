SRC_DIR = "path where we gonna store the file mails"

DBG_STR = """
PiAck - A file broker mailbox working with PiRelay

USAGE:
    python src/main.py [OPTIONS]

OPTIONS:
    -d, --debug, -D, --Debug    Enable debug mode
    -f, --flush, -F, --Flush    Flush the source directory on startup
    -s, --src=PATH              Set source dir path ("Update in code or always provide in cli args")
    -p, --port=PORT             Set server port (default: 8080)
    -h, --help                  Shows help menu

EXAMPLES:
    # Start server with default settings
    python src/main.py

    # Start server with debug mode and custom port
    python src/main.py -d -p=9000

    # Start server with custom source directory and flush all directories
    python src/main.py -s=/tmp/piack -f

SERVER ENDPOINTS:
    POST /config
        Description: Update server configuration dynamically remotely
        Headers: Content-Type: application/json
        Body: JSON config object (see CONFIG STRUCTURE below)

    POST /send/{recipient}/{file_id}
        Description: Send small file (<= 5MB) via multipart form data
        Headers: Content-Type: multipart/form-data
        Form fields:
            - file: File data
            - file_id: Unique file identifier
            - sender: Sender username
            - relative_path: Relative path for file

    POST /send/{recipient}/{file_id}/{chunk_idx}
        Description: Send large file chunk (> 5MB)
        Headers:
            - Content-Type: application/octet-stream
            - X-File-Id: File identifier
            - X-Chunk-Index: Current chunk index (0-based)
            - X-Total-Chunks: Total number of chunks
            - X-Sender: Sender username
            - X-Relative-Path: Relative path for file
        Body: Raw chunk data

    GET /recieve/
        Description: Receive files from mailbox (all senders)
        Headers:
            - X-Receiver: Receiver username
        Response:
            - Empty: JSON array []
            - Single file: Raw file data with X-File-Name header
            - Multiple files: Multipart/form-data response

    GET /recieve/{sender}
        Description: Receive files from specific sender
        Headers:
            - X-Receiver: Receiver username
        Response:
            - Empty: JSON array []
            - Single file: Raw file data with X-File-Name header
            - Multiple files: Multipart/form-data response

CONFIG STRUCTURE:
    {
        "flush": ["/path1", "/path2"],      // List of directories to flush
        "declutter": "true",                // Remove all files from ROOT (keep dirs)
        "port": 9000,                       // Change server port (triggers restart)
        "block": ["user1", "user2"],        // Add users to blocklist
        "command": "shell command",         // Execute shell command
        "down": true                        // Set server down state
    }

CONSTANTS:
    CHUNK_SIZE: 1MB (1024 * 1024 bytes)
    SMALL_FILE_SIZE: 5MB (5 * 1024 * 1024 bytes)

FILE STORAGE:
    Files are stored in memory as chunks until fully received, then added to recipient's mailbox.
    Use mailbox for receiving files from all senders, or specify sender for targeted retrieval.
"""
