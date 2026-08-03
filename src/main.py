import requests
import helper
import piack
from pathlib import Path
import shutil
from fastapi import FastAPI, Request, UploadFile, Form, File
from fastapi.responses import Response
import consts
import globals

globals.ROOT = Path(consts.SRC_DIR)


def init():
    clargs = helper.CLI()
    clargs.parse()

    if clargs.dbg:
        print(clargs)    
    globals.ROOT = Path(clargs.src_dir)

    if clargs.flush:
        for e in globals.ROOT.iterdir():
            if e.is_dir():
                shutil.rmtree(e)


if __name__ == "__main__":
    init()
    app = FastAPI()
    
    # Load cache from disk
    piack.load_cache()


# Should always be Live so remoe config is possible
@app.post("/config")
async def recv_config(req: Request):
    config = await req.json()
    piack.parse_config(config)
    return {"status":"Ok"}


@app.post("/send/{dst_mail}/{file_id}")
async def send_small_file(dst_mail: str,file_id: str,file: UploadFile = File(...),file_id_form: str = Form(...),sender: str = Form(...),relative_path: str = Form(...)):
    file_content = await file.read()
    # Stroe full file as single chunk data
    if store_file_chunk(sender=sender,file_id=file_id,chunk_idx=0,chunk_data=file_content,total_chunks=1,relative_path=relative_path,file_name=file.filename,recipient=dst_mail):
        piack.add_to_mailbox(dst_mail, file_id)
    return {"status": "Ok"}


@app.post("/send/{dst_mail}/{file_id}/{chunk_idx}")
async def send_large_file_chunk(dst_mail: str,file_id: str,chunk_idx: int,req: Request):
    data = await req.body()

    # Extract headers
    tot_chnks = int(req.headers.get("X-Total-Chunks", "1"))
    sender = req.headers.get("X-Sender", "unknown")
    rel_fpath = req.headers.get("X-Relative-Path", "")
    
    if piack.store_file_chunk(sender=sender,file_id=file_id,chunk_idx=chunk_idx,chunk_data=data,total_chun=tot_chnks,relative_path=rel_fpath,recipient=dst_mail):
        piack.add_to_mailbox(dst_mail, file_id)
    return {"status": "Ok"}

@app.get("/status")
async def status(req:Request):
    return {"status":"ok"}

@app.get("/health")
async def health(req:Request):
    return {"status":"ok"}

@app.get("/recieve/")
async def receive_mailbox(req: Request):
    receiver = req.headers.get("X-Receiver", "ANONYM")
    files = piack.get_mailbox_files(receiver)
    if not files:
        return Response(content=b"No Files in Remote", media_type="application/json")
    if len(files) > 1:
        body, content_type = piack.create_multipart_response(files, receiver)
        return Response(content=body, media_type=content_type)
    f_info = files[0]
    f_data = piack.load_file_from_disk(receiver, f_info["relative_path"])
    if f_data is None:
        return Response(status_code=404, content=b"File not found")
    ret = Response(content=file_data, media_type="application/octet-stream")
    ret.headers["X-File-Name"] = f_info["name"]
    return ret 


@app.get("/recieve/{src_mail}")
async def receive_from_sender(src_mail: str, req: Request):
    receiver = req.headers.get("X-Receiver", "ANONYM")
    files = piack.get_sender_files(src_mail)
    if not files:
        return Response(content=b"No Files in Remote", media_type="application/json")

    if len(files) > 1:
        body, content_type = piack.create_multipart_ret(files, receiver)
        return Response(content=body, media_type=content_type)
    f_info = files[0]
    f_data = piack.load_file_from_disk(src_mail, f_info["relative_path"])
    if f_data is None:
        return Response(status_code=404, content=b"File not found")
    ret = Response(content=f_data, media_type="application/octet-stream")
    ret.headers["X-File-Name"] = f_info["name"]
    return ret






    
    

    
    
    
            


