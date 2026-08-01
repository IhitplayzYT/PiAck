import requests
import helper
from pathlib import Path
import shutil
from fastapi import FastAPI,Request
import consts
import globals

globals.ROOT = Path(consts.SRC_DIR)


def init():
    nonlocal ROOT
    clargs = helper.CLI()
    clargs.parse()

    if clargs.dbg:
        print(clargs)    
    ROOT = Path(clargs.src_dir)

    if clargs.flush:
        for e in ROOT.iterdir():
            if e.is_dir():
                shutil.rmtree(e)





if __name__ == "__main__":
    init()
    app = FastAPI()



@app.post("/config")
async def recv_config(req: Request):
    config = await req.json()
    parse_config(config)
    return {"status":"Ok"}


    
    

    
    
    
            


