import shutil
import globals 
from pathlib import Path
import asyncio
import os
import signal
import sys
import subprocess
import json
from typing import Dict, List, Optional
from fastapi import UploadFile, Form


def parse_config(json):
    assert globals.ROOT is not None
    ROOT = globals.ROOT
    if json["flush"]:
        for i in json["flush"]:
            p = ROOT + i
            if ROOT.exists() and ROOT.is_dir():        
                shutil.rmtree(ROOT + i)
    if json["declutter"] in ("true","True"):
        for i in ROOT.iterdir():
            if i.is_dir():
                pass
            else:
                i.unlink()
    if json["port"]:
        globals.PORT = int(json["port"])
        asyncio.create_task(restart())
    if json["block"]:
        globals.BLOCKLIST.extend(json["block"])
    if json["command"]:
        subprocess.run(json["command"], shell=True)
    if json["down"]:
        globals.DOWN = bool(json["down"])
    
    

        
        

        
async def restart():
    await asyncio.sleep(1)
    args = sys.argv.copy()
    port_idx = None
    for i,v in enumerate(args):
        if v.startswith("--port=") or v.startswith("-p="):
            port_idx = i
    args[port_idx] = args[port_idx][:args[port_idx].find("=")+1] + str(globals.PORT)
    os.execv(sys.executable, [sys.executable] + args)


def store_file_chunk(
    sender: str,
    file_id: str,
    chunk_idx: int,
    chunk_data: bytes,
    total_chunks: int,
    relative_path: str,
    file_name: Optional[str] = None,
    recipient: Optional[str] = None
) -> bool:
    """Store a file chunk and return True if file is complete."""
    assert globals.ROOT is not None
    
    if sender not in globals.file_storage:
        globals.file_storage[sender] = {}
    
    if file_id not in globals.file_storage[sender]:
        globals.file_storage[sender][file_id] = {
            "chunks": {},
            "metadata": {
                "total_chunks": total_chunks,
                "relative_path": relative_path,
                "file_name": file_name,
                "sender": sender,
                "recipient": recipient
            }
        }
    
    globals.file_storage[sender][file_id]["chunks"][chunk_idx] = chunk_data
    
    # Check if file is complete
    stored_chunks = len(globals.file_storage[sender][file_id]["chunks"])
    is_complete = stored_chunks == total_chunks
    
    if is_complete and recipient:
        # Assemble and save to recipient's directory
        complete_data = assemble_file(sender, file_id)
        if complete_data:
            recipient_dir = globals.ROOT / recipient
            recipient_dir.mkdir(parents=True, exist_ok=True)
            
            # Use relative_path as filename, or file_name if available
            save_path = recipient_dir / relative_path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(complete_data)
            
            # Clear chunks from memory after saving to disk
            globals.file_storage[sender][file_id]["chunks"] = {}
            
            # Save cache
            save_cache()
    
    return is_complete


def assemble_file(sender: str, file_id: str) -> Optional[bytes]:
    """Assemble all chunks into complete file data."""
    if sender not in globals.file_storage or file_id not in globals.file_storage[sender]:
        return None
    
    file_data = globals.file_storage[sender][file_id]
    chunks = file_data["chunks"]
    total_chunks = file_data["metadata"]["total_chunks"]
    
    if len(chunks) != total_chunks:
        return None
    
    # Assemble chunks in order
    complete_data = b""
    for i in range(total_chunks):
        if i not in chunks:
            return None
        complete_data += chunks[i]
    
    return complete_data


def load_file_from_disk(recipient: str, relative_path: str) -> Optional[bytes]:
    """Load file from recipient's directory on disk."""
    assert globals.ROOT is not None
    file_path = globals.ROOT / recipient / relative_path
    
    if not file_path.exists():
        return None
    
    with open(file_path, 'rb') as f:
        return f.read()


def add_to_mailbox(recipient: str, file_id: str):
    if recipient not in globals.mailbox:
        globals.mailbox[recipient] = []
    if file_id not in globals.mailbox[recipient]:
        globals.mailbox[recipient].append(file_id)


def get_mailbox_files(recipient: str) -> List[Dict]:
    """Get list of files in recipient's mailbox from disk."""
    assert globals.ROOT is not None
    recipient_dir = globals.ROOT / recipient
    
    if not recipient_dir.exists():
        return []
    
    files = []
    for file_path in recipient_dir.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(recipient_dir))
            files.append({
                "name": relative_path,
                "size": file_path.stat().st_size,
                "sender": "cached",
                "file_id": relative_path.replace("/", "_"),
                "relative_path": relative_path
            })
    
    return files


def get_sender_files(sender: str) -> List[Dict]:
    """Get list of files from a specific sender's directory on disk."""
    assert globals.ROOT is not None
    sender_dir = globals.ROOT / sender
    
    if not sender_dir.exists():
        return []
    
    files = []
    for file_path in sender_dir.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(sender_dir))
            files.append({
                "name": relative_path,
                "size": file_path.stat().st_size,
                "sender": sender,
                "file_id": relative_path.replace("/", "_"),
                "relative_path": relative_path
            })
    
    return files


def cleanup_file(sender: str, file_id: str):
    """Remove file from storage after sending."""
    if sender in globals.file_storage and file_id in globals.file_storage[sender]:
        del globals.file_storage[sender][file_id]


def create_multipart_response(files: List[Dict], receiver: str) -> tuple[bytes, str]:
    """Create multipart response body and content-type header from disk."""
    import uuid
    boundary = str(uuid.uuid4())
    
    body = b""
    for file_info in files:
        sender = file_info["sender"]
        relative_path = file_info["relative_path"]
        
        # Load file from disk
        file_data = load_file_from_disk(sender, relative_path)
        
        if file_data is None:
            continue
        
        filename = file_info["name"]
        
        # Add part headers
        part_headers = f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        part_headers += "\r\n"
        
        body += f"--{boundary}\r\n".encode()
        body += part_headers.encode()
        body += file_data
        body += b"\r\n"
    
    body += f"--{boundary}--\r\n".encode()
    
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def save_cache():
    """Save file_storage and mailbox to cache.json."""
    assert globals.ROOT is not None
    cache_path = globals.ROOT / globals.CACHE_FILE
    
    # Convert bytes to base64 for JSON serialization
    cache_data = {
        "file_storage": {},
        "mailbox": globals.mailbox
    }
    
    for sender, sender_files in globals.file_storage.items():
        cache_data["file_storage"][sender] = {}
        for file_id, file_data in sender_files.items():
            # Store metadata only, chunks are saved to disk
            cache_data["file_storage"][sender][file_id] = {
                "metadata": file_data["metadata"]
            }
    
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)


def load_cache():
    """Load file_storage and mailbox from cache.json."""
    assert globals.ROOT is not None
    cache_path = globals.ROOT / globals.CACHE_FILE
    
    if not cache_path.exists():
        return
    
    with open(cache_path, 'r') as f:
        cache_data = json.load(f)
    
    # Restore mailbox
    globals.mailbox = cache_data.get("mailbox", {})
    
    # Restore file_storage metadata (chunks will be loaded from disk)
    for sender, sender_files in cache_data.get("file_storage", {}).items():
        globals.file_storage[sender] = {}
        for file_id, file_data in sender_files.items():
            globals.file_storage[sender][file_id] = {
                "chunks": {},  # Chunks loaded from disk on demand
                "metadata": file_data["metadata"]
            }

    
