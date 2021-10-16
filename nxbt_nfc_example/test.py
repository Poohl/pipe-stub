import sys
sys.path.insert(0, "..")
sys.path.insert(0, ".")

import hjson, json
import socket

from pipestub import remove_python_comments, hexer, assemble_states_from_hjson, pipe_stub

s = hjson.load(open("nxbt_nfc_example/test.hjson"))
s = assemble_states_from_hjson(s, entry_on_loop=False, loop_on_entry=True)

d = iter(json.load(open("nxbt_nfc_example/nxbt_raw.hex.json")))

pipe_stub(s, d.__next__, print, interactive=False)

