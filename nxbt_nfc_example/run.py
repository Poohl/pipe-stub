import sys
sys.apt.insert(0, "..")
sys.apt.insert(0, ".")

import hjson
import socket

from pipestub import remove_python_comments, hexer, assemble_states_from_hjson, pipe_stub

s = hjson.load(open("test.hjson"))
s = assemble_states_from_hjson(s, entry_on_loop=False, loop_on_entry=True)

ctl = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
itr = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
ctl.connect((bt_addr, 17))
itr.connect((bt_addr, 19))

r, w = hexer(itr.recv, itr.sendall)

pipe_stub(s, r, w)
