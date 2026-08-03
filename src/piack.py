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
import uuid

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
    if json["delete"]:
        for i in json["delete"]:
            remove_mail(i)
    if json["add"]:
        for i in json["delete"]:
            add_mail(i)
    if json["chname"]:
        l = len(json["chname"])
        if not l & 1:
            return
        else:
            for i in range(l//2):
                change_mail(json["chname"][2 * i],json["chname"][2 * i+1])

def change_mail(old: str,new:str):
    os.rename(Path(os.curdir) / old,Path(os.curdir) / new)

def remove_mail(mailbx:str):
    shutil.rmtree(Path(os.curdir) / mailbox)

def add_mail(mailbox:str):
    os.mkdir(Path(os.curdir) / mailbox)

async def restart():
    await asyncio.sleep(1)
    args = sys.argv.copy()
    port_idx = None
    for i,v in enumerate(args):
        if v.startswith("--port=") or v.startswith("-p="):
            port_idx = i
    args[port_idx] = args[port_idx][:args[port_idx].find("=")+1] + str(globals.PORT)
    os.execv(sys.executable, [sys.executable] + args)


def store_file_chunk(sender: str,file_id: str,chunk_idx: int,chunk_data: bytes,tot_chunks: int,rel_path: str,fname: Optional[str] = None,recipient: Optional[str] = None) -> bool:
    assert globals.ROOT is not None
    if sender not in globals.file_storage:
        globals.file_storage[sender] = {}
    
    if file_id not in globals.file_storage[sender]:
        globals.file_storage[sender][file_id] = {
            "chunks": {},
            "metadata": {
                "total_chunks": tot_chunks,
                "relative_path": rel_path,
                "file_name": fname,
                "sender": sender,
                "recipient": recipient
            }
        }
    globals.file_storage[sender][file_id]["chunks"][chunk_idx] = chunk_data
    
    stored_chunks = len(globals.file_storage[sender][file_id]["chunks"])
    if (len(globals.file_storage[sender][file_id]["chunks"]) == tot_chunks) and recipient:
        full_data = assemble_file(sender, file_id)
        if full_data:
            recip_dir = globals.ROOT / recipient
            recip_dir.mkdir(parents=True, exist_ok=True)
            
            save_path = recip_dir / rel_path 
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(full_data)
            globals.file_storage[sender][file_id]["chunks"] = {}
            save_cache()
            return True 
        else:
            return False
    return True


def assemble_file(sender: str, file_id: str) -> Optional[bytes]:
    if sender not in globals.file_storage or file_id not in globals.file_storage[sender]:
        return None
    file_data = globals.file_storage[sender][file_id]
    chunks = file_data["chunks"]
    tot_chunks = file_data["metadata"]["total_chunks"]
    if len(chunks) != tot_chunks:
        return None
    ret = b""
    for i in range(tot_chunks):
        # Missing Chunk
        if i not in chunks:
            return None
        ret += chunks[i]
    return ret


def load_file_from_disk(recipient: str, relative_path: str) -> Optional[bytes]:
    assert globals.ROOT is not None

    file_path = globals.ROOT / recipient / relative_path
    if not file_path.exists():
        return None
    with open(file_path, 'rb') as f:
        return f.read()


def add_to_mailbox(recipient: str, file_id: str):
    if recipient not in globals.mailbox:
        globals.mailbox[recipient] = []
    if file_id not in globals.mailbox[recipient][0]:
        globals.mailbox[recipient][1].append(file_id)
        globals.mailbox[recipient][0].add(file_id)


def get_mailbox_files(recipient: str) -> List[Dict]:
    assert globals.ROOT is not None
    src_dir = globals.ROOT / recipient 
    if not src_dir.exists():
        return []
    files = []
    for file_path in src_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(src_dir))
            files.append({
                "name": rel_path,
                "size": file_path.stat().st_size,
                "sender": "CACHED",
                "file_id": rel_path.replace("/", "_"),
                "relative_path": rel_path
                })
    return files


def get_sender_files(sender: str) -> List[Dict]:
    assert globals.ROOT is not None
    sender_dir = globals.ROOT / sender
    if not sender_dir.exists():
        return []
    files = []
    for file_path in sender_dir.rglob("*"):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(sender_dir))
            files.append({
                "name": rel_path,
                "size": file_path.stat().st_size,
                "sender": sender,
                "file_id": rel_path.replace("/", "_"),
                "relative_path": rel_path
            })
    return files


def cleanup_file(sender: str, file_id: str):
    if sender in globals.file_storage and file_id in globals.file_storage[sender]:
        del globals.file_storage[sender][file_id]


def create_multipart_response(files: List[Dict], receiver: str) -> tuple[bytes, str]:
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
    """Save file_storage and the mailbox to a cache.json located in the root of the Remote."""
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
            # chunks are saved to disk
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
    globals.mailbox = cache_data.get("mailbox", {})
    
    # (chunks will be loaded from disk)
    for sender, sender_files in cache_data.get("file_storage", {}).items():
        globals.file_storage[sender] = {}
        for file_id, file_data in sender_files.items():
            globals.file_storage[sender][file_id] = {
                "chunks": {}, 
                "metadata": file_data["metadata"]
            }

    
