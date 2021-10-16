
from argparse import ArgumentParser
import hjson
import sys
import logging
from datetime import datetime
import re
import os

def val_or_else(dict, key, default=None):
	return dict[key] if key in dict else default

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

	def next(self, input, default=None):
		"""
		given a input looks for a transition to fire now. If none is found return default.
		"""
		for t in self.transitions:
			if t.applies(input):
				return t
		return default

	@staticmethod
	def from_dict(dict, entry_on_loop=False, loop_on_entry=False):
		transitions = []
		for (pattern, state) in dict.items():
			if pattern not in ("name", "entry", "loop", "exit"):
				transitions.append(Transition(re.compile(pattern), state, state))
		return State(
			val_or_else(dict, "name"),
			val_or_else(dict, "entry", val_or_else(dict, "loop") if loop_on_entry else None),
			val_or_else(dict, "loop", val_or_else(dict, "entry") if entry_on_loop else None),
			val_or_else(dict, "exit"),
			transitions
		)

	def translate_trans(self, dict):
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

	def applies(self, input):
		return self.matcher.fullmatch(input)

	def translate_target(self, dict):
		self.target = dict[self.target]


def pipe_stub(states, read=lambda: input(), write=lambda b: print(b), initial=0, logdump=sys.stderr, default_transition="ignore", interactive=False):

	cstate = states[initial]

	while cstate:
		if cstate.entry:
			logdump.write(f"entry {datetime.now()} {cstate.entry}\n")
			write(cstate.entry)

		while True:
			cin = read()
			logdump.write(f"in {datetime.now()} {cin}\n")
			ctrans = cstate.next(cin, default=None)

			if not ctrans:
				logdump.write(f"unhandled input {cin} in state {cstate.name}, assuming {default_transition}\n")
				ctrans = Transition(None, default_transition, cstate)

			if ctrans.get() == cstate:
				if ctrans.name == "loop":
					if cstate.loop:
						logdump.write(f"loop {datetime.now()} {cstate.loop}\n")
						write(cstate.loop)
				elif ctrans.name == "reject":
					logdump.write(f"rejected {cin} in state {cstate.name}, terminating\n")
				if interactive:
					input()
			else:
				break

		if interactive:
			input()
			
		if cstate.exit:
			logdump.write(f"exit {datetime.now()} {cstate.exit}\n")
			write(cstate.exit)

		cstate = ctrans.get()

def assemble_states_from_hjson(raw_states, entry_on_loop=False, loop_on_entry=False):
		
	states = map(
		lambda r: State.from_dict(r, loop_on_entry=loop_on_entry, entry_on_loop=entry_on_loop),
		raw_states
	)
	
	def set_state_name_if_None(z):
		s, n = z
		if not s.name:
			s.name = n
		return s

	states = map(set_state_name_if_None, zip(states, range(len(raw_states))))

	states = list(states)

	name_dict = {
		"reject": None
	}
	for s in states:
		if s.name:
			name_dict[s.name] = s

	for i, s in enumerate(states):
		name_dict["accept"] = states[i + 1] if (i+1) < len(states) else None
		name_dict["loop"] = states[i]
		name_dict["ignore"] = states[i]
		s.translate_trans(name_dict)

	return states

def hexer(read, write):
	"""
	Given a binary read/write pair returns an equivalent hexadecimaly encoded read/write pair
	"""
	return lambda: bytes(read()).hex(), lambda b: write(bytes.fromhex(b))

def dehexer(read, write):
	"""
	given a hexadecimal read/write pair, returns an equivalent binary read/write pair
	"""
	return lambda: bytes.fromhex(read()), lambda h: write(bytes(h).hex())

def remove_python_comments(s):
	return re.sub(r'#[^"\n]\n', "\n", s)

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument("state_file", help="File to load the states from")
	#parser.add_argument("-l", "--log", help="File to log to")
	parser.add_argument("-r", "--raw", help="output raw like in file instead of converting filecontents from hex to bin")
	parser.add_argument("-d", "--default", help="what to do when no transition matches")
	parser.add_argument("--loop-on-entry", help="when no entry action is given, trigger loop action")
	parser.add_argument("--entry-on-loop", help="when no loop action is given but one it triggered, use entry")
	parser.add_argument("-m", "--mimify", help="if comments should be stripped from the statefile.")
	parser.add_argument("-I", "--interactive", help="Run interactively, requiereing confirmation for every action")
	args = parser.parse_args()

	with open(args.state_file) as f:
		if args.mimify:
			s = f.read()
			s = remove_python_comments(s)
			raw_states = hjson.loads(s)
		else:
			raw_states = hjson.load(f)
		print(raw_states)

	states = assemble_states_from_hjson(raw_states, entry_on_loop=args.entry_on_loop, loop_on_entry=args.loop_on_entry)

	r, w = sys.stdin.buffer.read, sys.stdout.buffer.write
	if not args.raw:
		r, w = dehexer(r, w)

	pipe_stub(states, r, w, default_transition=args.default)
