#!/tools/net/bin/python

# Copyright (c) 1994, 1996, Tony J. Ibbs All rights reserved.
# Copyright (c) 2004, Derek Chen-Becker All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#       
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#       
#     * Neither the name of py-iso8211 nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""commandline - a simple command line interface

	This module provides a class CommandLine which may be subclassed
	to provide command line interpretation facilities.

	This code written by:

		Tony J Ibbs

		Department of Geography & Topographic Science,
		University of Glasgow,
		GLASGOW  G12 8QQ
		Scotland

		Tel: (+44)141-330-6649
		Fax: (+44)141-330-4894

		Email:	tony@lsl.co.uk
		   or:	T.Ibbs@geog.gla.ac.uk

	and dated 10 January 1996

	NOTE - this is not specific to ISO 8211, at all, but is needed by the
	iso8211 command, so is provided in the iso8211 package for convenience.
	"""

import sys
import os
import string

# Standard stuff

FALSE = 0
TRUE  = 1

# Exceptions

class UnknownCommand(Exception):
	"Unknown command"
	pass

# The basic help string

Basic_help_string = """Command line processor.

	Commands are:

	interactive	enter a simple interactive environment.
	int		synonym for "interactive"
	debug		switch debugging on (or off)
	exit		exit the interactive environment
	help		print this message
	"""


#---------------------------------------------------------------------------------
class CommandLine:
	"""Command line context.

	This class provides the basic functionality for command line processing,
	including the ability to manage a simple sort of interactive session.

	Basic usage involves:

		- create a sub-class of CommandLine
		- add appropriate methods for the commands required
		- add the command name / method correspondences to "self.commands"
		- do
			SubClass.obey_command_line(sys.argv[1:])

	Initialisation arguments:

		None

	A CommandLine object contains:

		self.prompt		The prompt to use for interactive use
					(defaults to "Command:")

		self.separator		The separator for multiple commands on one line
					(defaults to "+")

		self.commands		A dictionary of the form:
						command name :: command method
					(defaults to entries for "int", "interactive", "help",
					"debug" and "exit")

		self.help_string	A string giving help on the basic commands already
					defined

		self.exceptions_to_ignore	A tuple of exceptions to be ignored
						(defaults to an empty tuple)

		self.exceptions_to_handle	A tuple of exceptions to be pass to self.handler
						(defaults to an empty tuple)

		self.handler		A routine to call (with arguments exception and tuple)
					to handle any exceptions that are not to be ignored,
					but do need special handling. If it raises any exceptions
					of its own, they will not be trapped.
					(defaults to None)
	"""

	def __init__(self):

		# Set up a default prompt, used when doing an interactive session

		self.prompt   = "Command: "

		# Remember if we are currently doing an interactive session

		self.in_interactive = FALSE

		# Decide on the string we use to separate multiple commands
		# on the same line - a plus makes a reasonable default, since
		# it doesn't get clobbered by the Unix shell

		self.separator = '+'

		# Define our basic commands

		self.commands = { "interactive" : self.interactive,
				  "int"		: self.interactive,
				  "help"	: self.help,
				  "debug"	: self.debug,
				  "exit"	: self.exit }

		# Define the basic help string

		self.help_string = Basic_help_string

		# We have a tuple of exceptions which should be ignored
		# when obeying a command line - these just print out
		# the basic exception type and value, which allows an
		# interactive session to continue neatly over expected
		# exceptions. Note that EOFError and UnknownCommand are
		# handled separately

		self.exceptions_to_ignore = ()	# no such exceptions, by default

		# We don't have a special exception handler

		self.exceptions_to_handle = ()	# no such exceptions, by default
		self.handler = None

		# And we're not (by default) debugging

		self.debugging = FALSE


	def __repr__(self):
		return "Command line interface"


	def exit(self,cmd,args):
		"""Request to exit interactive mode - raise an EOF error."""

		raise EOFError


	def help(self,cmd,args):
		"""The basic help command - prints the basic help string.

		Called with ARGS = None if there were no arguments on the
		command line."""

		print self.help_string


	def debug(self,cmd,args):
		"""Command to switch debugging on or off."""

		if args == None or len(args) == 0:
			self.debugging = TRUE
		elif args[0] == "true" or args[0] == "t" or args[0] == 1:
			self.debugging = TRUE
		elif args[0] == "false" or args[0] == "f" or args[0] == 0:
			self.debugging = FALSE
		else:
			print "Command is `debug [t|f|true|false|1|0]'"

		if self.debugging:
			print "Debugging on"
		else:
			print "Debugging off"


	def obey_command_line(self,command_line):
		"""Obey a command line.

		The COMMAND_LINE is a list of `words', so that this method
		may be called with "sys.argv[1:]" as a sensible argument.

		Note that a command line may be composed of multiple commands,
		separated by the separator string (which defaults to "+").
		Separators must be delimited by spaces (i.e., must count as
		`words') - this is so that (for instance) a filename may safely
		contain the separator string.
		"""

		if len(command_line) == 0:
			self.help(None)
			return

		# Split the command line apart into individual commands

		list_of_commands = self.extract_commands(command_line,self.separator)

		if self.debugging:
			print "--- command line =",list_of_commands

		# And obey them

		for command in list_of_commands:

			try:
				self.obey_command(command)

			except UnknownCommand,(cmd,args):
				# Unknown command - this should already have
				# been grumbled about, so just abort this
				# command line

				break

			except KeyboardInterrupt:
			   	# Raised by typing "Control-C"
				# Just ignore this command line

				print	# The system doesn't print a newline for us
				break

			except EOFError:
			   	# Raised by typing "exit"
				# If we're interactive, just raise it again

				if self.in_interactive:
					raise EOFError
				else:
					break

			except self.exceptions_to_ignore:
				# Any exception that we should just ignore
				# - just ignore this command line after reporting

				print "%s: %s"%(sys.exc_type,sys.exc_value)
				break

			except self.exceptions_to_handle:
				# Any exception that we should handle specially
				# - just ignore this command line afterwards

				if self.handler == None:
					print "%s: %s"%(sys.exc_type,sys.exc_value)
				else:
					self.handler(sys.exc_type,sys.exc_value)
				break



	def extract_commands(self,command_line,separator):
		"""Extract individual commands from a command line.

		Given a COMMAND_LINE (list of `words'), return a list of
		individual commands, as delimited by the SEPARATOR string.

		Each individual command is a list of command words.

		For instance, given the COMMAND_LINE [ "help" "+" "fred" "2" ],
		and the SEPARATOR "+", this routine would return:

			[ [ "help" ], [ "fred", "2" ] ]
		"""

		if self.debugging:
			print "--- extract:",command_line

		# Individual command sequences are separated by the separator string...

		commands = []

		this_command = []

		for word in command_line:
			if word == separator:
				commands.append(this_command)
				this_command = []
			else:
				this_command.append(word)
		else:
			if len(this_command) > 0:
 				commands.append(this_command)

		if self.debugging:
			print "--- which produces:",commands

		return commands



	def obey_command(self,command):
		"""Obey a command.

		The COMMAND is a list of `words', where the first is the
		command name, and the rest are any arguments.
		"""

		if self.debugging:
			print "--- command =",command

		cmd  = command[0]	# the command word
		args = command[1:]	# any arguments

		# If we recognise this command, obey the relevent function,
		# otherwise, call the "unknown command" function to take
		# appropriate action

		if self.commands.has_key(cmd):
			self.commands[cmd](cmd,args)
		else:
			self.unknown_command(cmd,args)


	def unknown_command(self,cmd,args):
		"""Called to grumble about an unknown command.

		This is given as a separate method so that it can be
		overridden by child classes, if required.
		"""

		print "Unknown command: %s"%(cmd)
		print "Commands are:",

		names = self.commands.keys()
		names.sort()

		for name in names:
			print name,
		print

		# And raise an exception to show something went wrong

		raise UnknownCommand(cmd,args)


	def interactive(self,cmd,args):
		"""Start an interactive session."""

		if self.in_interactive:
			print "Already in an interactive session - ignored"
			return
		else:
			self.in_interactive = TRUE

		# Announce ourselves

		self.interactive_intro(args)

		# And loop, reading command lines and obeying them

		while 1:
			try:
				command_line = raw_input(self.prompt)

			except KeyboardInterrupt:	# i.e., "Control-C"
				print			# need a newline
				continue		# ignore it

			except EOFError:
				print "exit"
				break

			# Split it into individual words, separated by spaces

			word_list = string.split(command_line)

			# Ignore blank lines

			if len(word_list) == 0:
				continue

			# Obey the resultant command line

			try:
				self.obey_command_line(word_list)

			except EOFError:
				# Raised by typing "exit", so do so

				self.in_interactive = FALSE
				break


	def interactive_intro(self,args):
		"""Output appropriate messages at the start of an interactive session."""

		print "Interactive command environment"
		print "(use exit or `EOF' to exit the environment)"
		print

		if len(args) > 0:
			print "The rest of the command line after an `interactive' command"\
			      " is ignored"
			print "In this case, the following commands were ignored:",
			for word in args:
				print word,
			print
			print


#---------------------------------------------------------------------------------
class Example(CommandLine):
	"""An example of subclassing the command line class."""

	def __init__(self):

		# Do the command line initialisation

		CommandLine.__init__(self)

		# Define our own data

		self.had_fred = FALSE

		# Add some commands

		self.commands["fred"] = self.fred
		self.commands["args"] = self.print_args

		# And extend the help string to know about them

		self.help_string = self.help_string + """
	fred		set the Fred flag
	args <args>	print the arguments
	"""

	def __repr__(self):
		if self.had_fred:
			return "Had Fred already"
		else:
			return "Fred"


	def fred(self,args):
		"""Implement the "fred" command."""

		if self.had_fred:
			print 'Had "fred" already'
		else:
			print 'Received "fred"'
			self.had_fred = TRUE


	def print_args(self,args):
		"""Print the arguments to the "args" command."""

		print "Arguments are:",args


#---------------------------------------------------------------------------------
def main():
	"""Main routine, for use in interactive use of this file as a command.

	Uses the "Example" command line subclass, to show how this may be used.
	"""

	# sys.argv[0] is the command the user typed, which we don't particularly
	# care about - let's just extract the rest of the command line...

	arg_list = sys.argv[1:]

	# Let's have a command line processor

	command_processor = Example()

	# And obey any commands

	command_processor.obey_command_line(arg_list)


#---------------------------------------------------------------------------------
# And if we're called from the command line, let's do it!

if __name__ == '__main__':
	main()
