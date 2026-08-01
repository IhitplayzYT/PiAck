import consts
import sys
class CLI:
    def __init__(self):
        self.dbg = False
        self.flush = False
        self.src_dir = consts.SRC_DIR

    def parse(self):
        for i in sys.argv:
            if i in {"-d","--debug","-D","--Debug"}:
                self.dbg = True
            elif i in {"-f","--flush","-F","--Flush"}:
                self.flush = True
            else:
                if i.startswith("--src=") or i.startswit("--src-dir=") or i.startswith("-s="):
                    self.src_dir = i[i.find("=")+1:]
                else:
                    Help()



def Help():
    print(consts.DBG_STR)
    exit(0)



            
        
