import ArgumentParser from argparse
import hjson
import sys
import Enum from enum
import logging
import datetime

def val_or_none(dict, key):
	return dict[key] if key in dict else None

class State:
	"""
	Class representing a possible State to be in
	"""
	def __init__(self, name=None, entry=None, loop=None, exit=None, transitions=[]):
		self.name = name
		self.entry = entry
		self.loop = loop
		self.exit = exit
		self.transitions = transitions

	@classmethod
	def from_dict(dict):
		transitions = []
		for (pattern, state) in dict.items():
			if pattern not in ("name", "entry", "loop", "exit"):
				transitions.append(Transition(re.compile(pattern), state, state)
		return State(
				val_or_none(dict, "name"),
				val_or_none(dict, "entry"),
				val_or_none(dict, "loop"),
				val_or_none(dict, "exit"),
				transitions
			)
	
	def next(self, in, default=None):
		"""
		given a input looks for a transition to fire now. If none is found return default.
		"""
		for t in self.transitions:
			if t.applies(in):
				return t
		return default
	
	def transate_trans(self, dict):
		"""
		replace all transition targets according to a dict.
		"""
		for t in self.transitions:
			t.translate_target(dict)

	
class Transition:
	def __init__(self, matcher, name, target):
		self.matcher = matcher
		self.name = name
		self.target = target
	
    def get(self):
    	return self.target

	def applies(self, in):
		return self.matcher.matches(in)
	
	def translate_target(self, dict):
		self.target = dict[self.target]



def pipe_stub(states, initial=0, in_stream=sys.stdin, out_stream=sys.stdout, logdump=sys.stderr, hex=false):
	
	cstate = states[initial]

	if not hex:
		for s in states:
			if s.entry:
				s.entry = bytes.fromhex(s.entry)
			if s.loop:
				s.entry = bytes.fromhex(s.loop)
			if s.exit:
				s.entry = bytes.fromhex(s.exit)

	while cstate:
		if cstate.entry:
			logdump.write(f"entry {datetime.now()} {cstate.entry}")
			in_stream.write(cstate.entry)
		
		while True:
			cin = in_stream.read()
			if not hex:
				cin = cin.hex()
			logdump.write(f"in {datetime.now()} {cin}")
			ctrans = cstate.next(cin)

			if ctrans.get() == cstate:
				if ctrans.name == "loop":
					if cstate.loop:
						logdump.write(f"loop {datetime.now()} {cstate.loop}")
						out_stream.write(cstate.loop)
				elif ctrans.name == "reject":
					logger.error(f"rejected {cin} in state {cstate.name}, terminating")
				elif ctrans.name == "default":
					logging.warn(f"unhandled input {cin} in state {cstate.name}, assuming ignore")
			else:
				break

		if cstate.exit:
			logdump.write(f"exit {datetime.now()} {cstate.exit}")
			out_stream.write(cstate.exit)
		
		cstate = ctrans.get()
	

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("state_file", help="File to load the states from")
	#parser.add_argument("-l", "--log", help="File to log to")
	#parser.add_argument("-h", "--hex" help="output in hex instead of binary")
	
	args = parser.parse_args()
	
	with open(args.state_file) as f:
		rawstates = hjson.load(f)
		states = map(State.from_dict, rawstates)
	
	name_dict = {}
	for s in states:
		if s.name:
			name_dict[s.name] = s
	
	for i, s in enumerate(states):
		name_dict["accept"] = states[i+1] if i < len(states) else None
		name_dict["loop"] = states[i]
		name_dict["ignore"] = states[i]
		name:dict["reject"] = None
		s.transate_trans(name_dict)
	
	pipe_stub(states)
