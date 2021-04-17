
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
		return self.matcher.matches(input)

	def translate_target(self, dict):
		self.target = dict[self.target]


def pipe_stub(states, initial=0, in_stream=os.fdopen(sys.stdin.fileno(), 'rb'), out_stream=os.fdopen(sys.stdout.fileno(), 'wb'), logdump=sys.stderr, raw=False, default_transition="ignore"):

	if not raw:
		for s in states:
			if s.entry:
				s.entry = bytes.fromhex(s.entry)
			if s.loop:
				s.entry = bytes.fromhex(s.loop)
			if s.exit:
				s.entry = bytes.fromhex(s.exit)

	cstate = states[initial]

	while cstate:
		if cstate.entry:
			logdump.write(f"entry {datetime.now()} {cstate.entry}")
			out_stream.write(cstate.entry)

		while True:
			cin = in_stream.read()
			if not raw:
				cin = bytes(cin).hex()
			logdump.write(f"in {datetime.now()} {cin}")
			ctrans = cstate.next(cin, default=cstate)

			if not ctrans:
				logging.warning(f"unhandled input {cin} in state {cstate.name}, assuming {default_transition}")
				ctrans = Transition(None, default_transition, cstate)

			if ctrans.get() == cstate:
				if ctrans.name == "loop":
					if cstate.loop:
						logdump.write(f"loop {datetime.now()} {cstate.loop}")
						out_stream.write(cstate.loop)
				elif ctrans.name == "reject":
					logging.error(f"rejected {cin} in state {cstate.name}, terminating")

			else:
				break

		if cstate.exit:
			logdump.write(f"exit {datetime.now()} {cstate.exit}")
			out_stream.write(cstate.exit)

		cstate = ctrans.get()

def assemble_states_from_hjson(raw_states, entry_on_loop=False, loop_on_entry=False):
	states = list(map(
		lambda r: State.from_dict(r, loop_on_entry=loop_on_entry, entry_on_loop=entry_on_loop),
		raw_states
	))

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


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument("state_file", help="File to load the states from")
	#parser.add_argument("-l", "--log", help="File to log to")
	parser.add_argument("-r", "--raw", help="output raw like in file instead of converting from hex to bin")
	parser.add_argument("-d", "--default", help="what to do when no transition matches")
	parser.add_argument("--loop-on-entry", help="when no entry action is given, trigger loop action")
	parser.add_argument("--entry-on-loop", help="when no loop action is given but one it triggered, use entry")
	args = parser.parse_args()

	with open(args.state_file) as f:
		raw_states = hjson.load(f)
		print(raw_states)
	states = assemble_states_from_hjson(raw_states, entry_on_loop=args.entry_on_loop, loop_on_entry=args.loop_on_entry)

	pipe_stub(states, raw=args.raw, default_transition=args.default)
