import shutil
import globals 
from pathlib import Path
import asyncio
import os
import signal
import sys


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

        
async def restart():
    await asyncio.sleep(1) 
    args = sys.argv.copy()
    port_idx = None
    for i,v in enumerate(args):
        if v.startswith("--port=") or v.startswith("-p="):
            port_idx = i            
    args[port_idx] = args[port_idx][:args[port_idx].find("=")+1] + str(globals.PORT)
    os.execv(sys.executable, [sys.executable] + args)

    
