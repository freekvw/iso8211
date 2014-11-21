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

# $Id: format.py,v 1.6 2004/04/05 17:44:57 d-rock Exp $

"""ISO 8211 format controls - interpretation thereof."""

Changes = """Modifications:

1996/04/12 (or thereabouts) - work started on proper format control parsing.

later:	Still under construction.
"""

Version = "0.1 under construction"

import sys
import os
import array
import string
from math import ceil

import misc

# I *like* TRUE and FALSE - so define them!

TRUE	= 1
FALSE	= 0

# Exceptions

iso8211_format_error = "ISO 8211 format controls"


# ----------------------------------------------------------------------
class Format(object):
	"""ISO 8211 format controls.

	Initialisation arguments:

		None

	A format control object contains:

		octets		the octet string

		extended_chars	TRUE if character subfields (A type) contain
				extended character sets, escapes or whatever
				(it is assumed that the user will set this by
				hand in the first instance, since I don't expect
				it to be used initially)

		controls	a list of Repeat and Control objects

		flatlist	a flattened version of "controls", containing
				only Control objects (that is, with all explicit
				repeats iterated out)

		count		the number of explicit format controls in this
				object (this is identical to "len(flatlist)",
				but is provided for convenience)

		repeat_from	the index of the entry in "flatlist" at which
				repetition would start (or None if none)

		repeat		the slice of "flatlist" which is repeated
				(this is flatlist[repeat_from:])


		current_item	the current Control object
		current_index	the current Control object's index

		unit_size       the unit size of a field, 0 indicates that a
		                field is delimited or has a single value
		
	Usage:

	1) Create a new Format object:

		fmt = format.Format()

	2) Parse a format control string using this object:

		fmt.parse("(I(1),(2A(%),R(3)))")

	   Note that it is possible to parse a new string using the
	   same object - the results of the new parse will simply
	   overwrite those of the old one.

	3) It is possible to iterate over the format controls:

		for item in fmt:
			print "item %s"%item

	   Note that this will never terminate, since format controls
	   repeat - in other words, "current_index" can become greater
	   than "count". If you want to go over each format item once,
	   do:

		for which in range(fmt.count):
			print "item %s"%fmt.item(which)
	"""

	def __init__(self):

		# We start off `empty'

		self.unset()

		# We assume that we are simply dealing with standard ASCII

		self.extended_chars = FALSE


	def __del__(self):
		pass


	def __repr__(self):
		return "Format: %s"%(`self.octets`)


	def __getitem__(self,which):
		"""Used in iteration - get the n'th format item.

		Returns Control objects in order, repeating as necessary.
		Note that "which" is 0 upwards, and that we will (in fact)
		continue iterating forever...
		"""

		# Simply return the result of "item"

		return self.item(which)


	def unset(self):
		"""Unset the format - as if the object had just been created.

		(except that the "extended_chars" value is not touched)
		"""

		# Start with an empty list of format controls

		self.octets	 = ""
		self.controls    = []
		self.flatlist    = []
		self.repeat_from = None
		self.repeat	 = []

		self.current_item  = None
		self.current_index = -1		# i.e., the first item will be the next
		self.count         = 0
		self.unit_size     = 0


	def _start_parse(self):
		"""Perform processing required before a format is defined."""

		self.unset()


	def start_format(self):
		"""Perform processing required before a format is defined `by hand'.

		Call this before any calls to "add", "start_repeat" and "end_repeat"
		are made. Don't forget to call "end_format" when finished...
		"""

		self._start_parse()


	def add(self,control):
		"""Add a format control to the current format.

		The CONTROL should be a format control, such as A(3) or 2I
		"""

		# Ensure we have the initial opening parentheses, or else our comma separator

		if self.octets == "":
			self.octets = "("
		else:
			self.octets = self.octets + ","

		# Remember the control

		self.octets = self.octets + control


	def start_repeat(self,count=1):
		"""Start a repeat sequence, repetition count COUNT (default 1)."""

		# Ensure we have the initial opening parentheses, or else our comma separator

		if self.octets == "":
			self.octets = "("
		else:
			self.octets = self.octets + ","

		# Remember the repeat

		if count != 1:
			self.octets = self.octets + `count`

		self.octets = self.octets + "("


	def end_repeat(self):
		"""End a repeat sequence."""

		self.octets = self.octets + ")"



	def end_format(self):
		"""Perform processing required when a format has been defined `by hand'.

		Call this after all the appropriate calls to "add", "start_repeat"
		and "end_repeat" have been made. No more such calls should be made
		after calling this.
		"""

		self.octets = self.octets + ")"

		self.parse(self.octets)



	def _end_parse(self):
		"""Perform processing required when a format has been defined."""

		# Flatten the resulting format

		self._flatten()

		# Which gives us the format length

		self.count = len(self.flatlist)

		# And enables us to work out the repeat slice

		if self.repeat_from != None:
			self.repeat = self.flatlist[self.repeat_from:]
		else:
			self.repeat = []

		# Look for a REPEAT TO END

		self._look_for_REPEAT_TO_END()


	def parse(self,octets):
		"""Parse the ISO 8211 format control string OCTETS."""

		# Start the format off

		self._start_parse()

		# Remember the format string

		self.octets = octets

		#print "parsing %s" % misc.printable(octets)

		# And `decode' the format string
		# We use a `FormatParser' object to do the work for us

		parser = FormatParser(self)

		self.controls = parser.parse(octets)

		self.unit_size = 0
		
		for cnt in self.controls:
			#cnt.show()
			self.unit_size += cnt.byte_width
			#print "Byte width: %s" % cnt.byte_width

		# print "  total size = %d" % self.unit_size

		# Finish the formatting

		self._end_parse()


	def _look_for_REPEAT_TO_END(self):
		"""Check for a last repeat clause to mark for writing out as REPEAT TO END.

		If the very last item in the controls list is a REPEAT 1, then we can
		mark it as a REPEAT TO END. We do this (rather nastily) by negating
		its repeat count - i.e., setting it to -1.
		"""

		# Find the last clause in the control list

		last = self.controls[-1]

		# If the top level is not a REPEAT, then we don't have a REPEAT TO END situation

		if last.is_control:
			return

		# Otherwise, we need to look inside this REPEAT to see if IT ends
		# in a REPEAT, and so on...

		#print "Looking for REPEAT TO END in  ",`self.controls`
		#print "Last item of list is          ",`last`

		while not last.is_control:
			# Hah - it was a repeat clause as well
			# Extract the last item from ITS data

			last_item = last.clause[-1]

			if not last_item.is_control:
				last = last_item
			else:
				break

			#print "Last item of list is          ",`last`

		# So that leaves us with "last" as the last clause

		#print "Which leaves us with last item",`last`

		# And if the repeat is 1, tell it that it is a REPEAT TO END

		if last.repeat == 1:
			last.repeat_to_end = TRUE
			#print "Leaving last item as          ",`last`


	def item(self,which):
		"""Return the Control object with index "which".

		Note that "which" is 0 upwards, and that it may be greater
		than the total number of controls in the format control string
		(in which case format repetition will be used to determine which
		control should be returned, and an IndexError exception will
		be raised if repetition is not enabled for this format control
		string).
		"""

		if which < 0:
			raise IndexError,"Index should be 0 or more, not %d"%which
		elif which < len(self.flatlist):
			self.current_index = which
			self.current_item  = self.flatlist[which]
		else:
			# OK - we're into repeat territory

			if self.repeat_from == None:
				raise IndexError,"Format `%s' does not repeat"%self.octets

			# Work out our position in the repeat list...

			posn = which - len(self.flatlist)
			posn = posn % len(self.repeat)

			self.current_item  = self.repeat[posn]
			self.current_index = which

		return self.current_item


	def next_item(self):
		"""Return the next Control object.

		This works out what the next Control should be, and
		expands out repetitions, etc, as necessary.
		"""

		return self.item(self.current_index + 1)


	def rewind(self):
		"""`Rewind' the format controls.

		After calling this, "next_item()" will return the first
		Control object again.
		"""

		self.current_item  = None
		self.current_index = -1


	def _flatten_item(self,item):
		"""Flatten a given item from the format control list into "flatlist"."""

		# Do what seems indicated by its type

		if item.is_control:

			# It's a format control - simply iterate out the repeat

			for count in range(item.repeat):
				self.flatlist.append(item.control)

		else:

			# It's a repeat clause
			# Note at what index in the flatlist the first entry
			# for the repeat clause will be inserted

			self.repeat_from = len(self.flatlist)

			# And flatten out the clause the appropriate number of times

			for count in range(item.repeat):
				self._flatten_list(item.clause)



	def _flatten_list(self,list):
		"""Add a flattened format control list to "flatlist"."""

		for item in list:
			self._flatten_item(item)


	def _flatten(self):
		"""Flatten the "controls" list into the "flatlist"."""

		self.flatlist    = []
		self.repeat_from = 0	# A reasonable guess

		self._flatten_list(self.controls)


	def _write_nesting(self,dfd,nesting,indent):
		"""Write a number of spaces according to the NESTING*INDENT."""

		# Actually, we can just do that

		dfd.write(nesting*indent*" ")


	def _write_item(self,dfd,item,nesting,indent):
		"""Write out a representation of the given parsed item."""

		# Do what seems indicated by its type

		if item.is_control:

			# It's a format control

			self._write_nesting(dfd,nesting,indent)

			if item.repeat != 1:
				dfd.write("%2d "%(item.repeat))
			else:
				dfd.write("   ")

			dfd.write("%s\n"%(`item.control`))

		else:

			# It's a repeat clause

			self._write_nesting(dfd,nesting,indent)

			# It is not *quite* explicit in B.2 that omitting a repeat
			# count of 1 is legitimate in this circumstance, but there
			# are examples in B.3 of such practice, and I think it looks
			# neater..

			if item.repeat_to_end:
				dfd.write("REPEAT TO END\n")
			elif item.repeat == 1:
				dfd.write("REPEAT\n")
			else:
				dfd.write("REPEAT %d\n"%item.repeat)

			self._write_list(dfd,item.clause,nesting+1,indent)

			self._write_nesting(dfd,nesting,indent)
			dfd.write("END REPEAT\n")


	def _write_list(self,dfd,list,nesting,indent):
		"""Write out a representation of a format control list."""

		for item in list:
			self._write_item(dfd,item,nesting,indent)


	def write_DFD(self,dfd,indent=3):
		"""Write out the appropriate DFD data for these format controls.

		DFD    is the file to write to
		INDENT is the number of spaces to indent by - this is multiplied
		       by the `REPEAT' depth (that is, inside the first REPEAT
		       clause, 2*INDENT is used, etc.). It defaults to 3.
		"""

		self._write_list(dfd,self.controls,1,indent)



	def show(self):
		print "Format: %s"%(padding,self.octets)




# ----------------------------------------------------------------------
class FormatParser:
	"""Used to parse a format string.

	WARNING - No checking that we haven't gone off the end of the string.
	WARNING - Various places need to check for IndexError

	Initialisation arguments:

		format		the Format object we are parsing for
				(this is needed so we can get at its
				format building functions)

	A FormatParser object contains:

		octets		the octet string we are to parse
		extended_chars	TRUE if we are allowing extended character sets
				in character (A type) subfields

		next		which octet in "octets" we are looking at next
	"""

	def __init__(self,format):

		self.format         = format
		self.extended_chars = format.extended_chars

		self.octets = None	# no format string to parse yet
		self.next   = 0		# next character we're looking at


	def __del__(self):
		# Remove any depencies, just in case

		self.format = None


	def _read_repeat_count(self):
		"""Read and return a repeat count - no count means 1.

		The current character is looked at first.
		The first non-digit found is left as the current character."""

		# Read the digit string

		repeat = self._read_digit_string()

		# And return the appropriate repeat count

		if repeat == "":
			return 1
		else:
			return int(repeat)


	def _read_digit_string(self):
		"""Read and return a digit string.

		The current character is looked at first.
		The first non-digit found is left as the current character.
		"""

		# Start with an empty string

		digits = ""

		# Keep adding characters to our digit string
		# until we hit a non-digit (or the end of the string!)

		while self.next < len(self.octets):
			octet = self.octets[self.next]

			if octet in string.digits:
				digits    = digits + octet
				self.next = self.next  + 1
			else:
				break

		return digits



	def _read_subfield_size(self,control):
		"""Read and return a subfield size specification.

		The current character is looked at first.
		If it is an opening parenthesis then we have a subfield size to read.
		If we have a subfield size to read, then it is either a subfield width,
		or a subfield delimiter.

		We return:

			(None,None)		if there is no subfield size
			("W",width)		if there is a subfield width
			("D",delimiter)		if there is a subfield delimiter

		If we had an opening parenthesis then the character after the closing
		parenthesis is left as the current character, otherwise the current
		character is unchanged.			    
		"""

		# Do we have a subfield size specification?

		if self.octets[self.next] != "(":
			return (None,None)		# No - return at once
		else:
			self.next = self.next + 1	# Yes - ignore the "("

		# OK - we do have something to read

		if self.extended_chars and control == "A":

			# If we have extended character sets, we're not allowed
			# fixed width character (A type) subfields...

			width = None
			delim = self._read_subfield_delim()

		else:
			# Otherwise, if it starts with a number then it is a width...

			if self.octets[self.next] in string.digits:
				width = self._read_subfield_width()
				delim = None
			else:
				width = None
				delim = self._read_subfield_delim()

		# Regardless, check we have the required closing parenthesis

		if self.octets[self.next] != ")":
			raise iso8211_format_error,\
			      (FMT_EXC_CLOSEPAREN,self.octets[self.next],self.next,self.octets)
		else:
			self.next = self.next + 1	# we do - just ignore it

		# And return what we must return

		if width == None:
			return ("D",delim)
		else:
			return ("W",width)


	def _read_subfield_delim(self):
		"""Read and return a subfield delimiter."""

		# The current octet starts the delimiter

		delim     = self.octets[self.next]
		self.next = self.next + 1

		# If we have extended character sets, there might be more octets,
		# but otherwise there can't be...

		if self.extended_chars:

			# The following is not accurate enough, but will do for
			# testing stuff at the moment, I guess...

			while self.next < len(self.octets):
				octet = self.octets[self.next]

				if octet != ")":
					delim     = delim + octet
					self.next = self.next + 1
				else:
					break

		return delim


	def _read_subfield_width(self):
		"""Read a subfield width.

		The current character is looked at first.
		The first non-digit found is left as the current character.
		"""

		# Read the digit string

		width = self._read_digit_string()

		# And return it as an integer

		return int(width)


	def _read_binary_form(self):
		"""Read and return the format term and width for a binary form."""

		# Which form it IS is determined by the first digit

		what = self.octets[self.next]

		if what not in string.digits or not (1 <= int(what) <= 5):
			raise iso8211_format_error,\
			      (FMT_EXC_BINFORM,what,self.next,self.octets)

		self.next = self.next + 1

		# And its width is determined by the integer after that

		width     = self.octets[self.next]
		self.next = self.next + 1

		if width not in string.digits:
			raise iso8211_format_error,\
			      (FMT_EXC_BINWIDTH,width,self.next,self.octets)

		width = int(width)

		# Check they're compatible

		if ((what == "1" or what == "2") and (width != 1 and width !=2 and \
						      width != 3 and width != 4)) or \
		   ((what == "3" or what == "4" or what == "5") and (width != 4 and width != 8)):
			raise iso8211_format_error,\
			      (FMT_EXC_BININCOMPAT,what,width,self.next-2,self.octets)

		# OK - so return them

		return (what,width)


	def _read_control(self):
		"""Read a format control character(s) and return a Control object."""

		# The current character should be the main one...

		octet = self.octets[self.next]

		self.next = self.next + 1

		if octet == "A" or octet == "I" or octet == "R" or octet == "S" or \
		   octet == "C" or octet == "X":

			# This is the simple case - we may be followed by a width
			# or user delimiter

			control    = octet
			which,size = self._read_subfield_size(octet)


		elif octet == "B":

			# This might be either bit string data, or it might be
			# the MSOF "Btw" binary form. We decide which by looking
			# at what follows it

			control = octet

			if self.octets[self.next] in string.digits:
				# It is the MSOF binary form - read its type and size

				type,size = self._read_binary_form()

				# The `type' is really part of the control...

				control = control + type
				which   = "B"

			else:
				# It is bit string data - treat it normally

				which,size = self._read_subfield_size(octet)
				if not which or not size:
					print "BLA %s" % self.octets


		elif octet == "b":

			# This is the LSOF "btw" binary form - read its type and size

			type,size = self._read_binary_form()

			# The `type' is really part of the control...

			control = octet + type
			which   = "B"

		else:
			raise iso8211_format_error,\
			      (FMT_EXC_BADCONTROL,octet,self.next-1,self.octets)

		return Control(control,which,size)


	def _read_clause(self):
		"""Read a single clause of the format string.

		A clause is defined as the stuff within a set of repeat parentheses.

		A list of Repeat objects is returned.
		"""

		# Start with an empty list

		clause = []

		# Loop reading things...

		while self.next < len(self.octets):

			# Check for the end of this clause
			# (Is an empty clause allowed? I can't remember offhand)

			if self.octets[self.next] == ")":
				self.next = self.next + 1	# ignore it
				return clause			# and return

			# If we've already read an item, we expect a comma

			if clause != []:
				if self.octets[self.next] == ",":
					self.next = self.next + 1	# ignore it
				else:
					raise iso8211_format_error,\
					      (FMT_EXC_COMMA,self.octets[self.next],self.next,self.octets)

			# Then we can generally start off with a repeat count...

			repeat = self._read_repeat_count()

			# And we expect next either a new repeat clause, or
			# a format control

			if self.octets[self.next] == "(":

				# Ignore the "("

				self.next = self.next + 1

				# Read this new clause

				new_clause = self._read_clause()

				# And add it to our list as a Repeat object

				repeat_object = Repeat(repeat,clause=new_clause)

				clause.append(repeat_object)

			else:

				# Read the format control into a Control object

				control_object = self._read_control()

				# And add it to our list as a Repeat object

				repeat_object = Repeat(repeat,control=control_object)

				clause.append(repeat_object)

		# If we got here, then we ran out of format string, without a closing ")"

		raise iso8211_format_error,(FMT_EXC_ENDCLOSE,self.octets)


	def parse(self,octets):
		"""Parse the format control string in OCTETS and return the parsed form.

		The parsed form is returned as a list of Repeat objects.
		"""

		# Set ourselves up to start on this format control string
		self.octets = octets	# the format string to parse
		self.next   = 0		# the next character we're looking at

		# Check that the first character is an opening parenthesis

		if self.octets[self.next] != "(":
			raise iso8211_format_error,(FMT_EXC_STARTOPEN,octets)
		else:
			self.next = self.next + 1	# if it's there, just ignore it

		# Return the result of parsing the format string

		return self._read_clause()


# ----------------------------------------------------------------------
class Repeat:
	"""A repeat object, containing either a repeat clause or a Control object.

	Initialisation arguments:

		count		the repeat count for this clause or Control

	one of:
		clause		a list of Repeat objects forming a repeat clause
		control		a single Control object

	A Repeat object contains:

		repeat		the repeat count for this clause or Control

	one of:
		clause		a list of Repeat objects forming a repeat clause
		control		a single Control object

		is_control	TRUE if this Repeat contains a single Control
		repeat_to_end	TRUE if this Repeat contains a repeat clause which
				is the last repeat clause in the format controls,
				and which repeats until the end of the field - that is,
				it can be written out using REPEAT TO END
	        byte_width      The size of the contained controls/repeats, or zero if
		                undetermined/delimited
	"""

	def __init__(self,count,clause=None,control=None):

		# Check we have the right number of arguments

		if clause == None and control == None:
			raise ValueError,"Repeat object requires either clause or control value"

		if clause != None and control != None:
			raise ValueError,"Repeat object requires only one of clause and control value"

		# And remember them

		self.repeat     = count
		self.clause     = clause
		self.control    = control

		self.is_control    = (self.control != None)
		self.repeat_to_end = FALSE

		self.byte_width = self.calculate_size()

	def calculate_size(self):
		# print "Calulating size of ", self
		
		if self.is_control:
			# print "is_control, byte_width = ", self.repeat * self.control.byte_width
			return self.repeat * self.control.byte_width

		sum = 0

		for subrepeat in self.clause:
			# print "  subclause:\n    ", subrepeat, " = ", subrepeat.__class__
			sum += subrepeat.byte_width

		return sum

	def __del__(self):
		# Make some attempt to tidy up

		self.clause  = None
		self.control = None


	def __repr__(self):
		if self.is_control:
			return "%d %s"%(self.repeat,self.control)
		elif self.repeat_to_end:
			return "toend %s"%(self.clause)
		else:
			return "%d %s"%(self.repeat,self.clause)


       	def show(self):
		print "Repeat: %s"%(`self`)



# ----------------------------------------------------------------------
class Control:
	"""A single format control

	Initialisation arguments:

		control		the format control character
				(the format control character and its type for a binary form)

		form		"D" (Delimited) if it is delimited
				"W" (Width)     if it has an explicit width
				"B" (Binary)    if it is a binary form, "Btw" or "btw"
				None		if none of these applies
						(so it is terminated by UT or FT, of course)
						(with the exception of "B" - see 6.4.3.3 g))

		size		a delimiter if "form" is "D",
				a width     if "form" is "W" or "B"
				and otherwise is None

	        byte_width      the width in bytes of this control, if known (not for
		                delimited fields). Otherwise 0.


	A Control object contains:

		control, type, size	as above

	"""

	def __init__(self,control,form,size):

		#print "Init control:", control, form, size
		
		self.control   = control
		self.form      = form
		self.size      = size

		if form != "D" and form != "W" and form != "B" and form != None:
			raise iso8211_format_error,("Control error: form is `%s'"%form)

		self.byte_width = 0
		
		if form == "W":
			self.byte_width = self.size
			
		# special case for binary widths
		if form == "B":
			if self.size:
				#self.byte_width = int(ceil(self.size / 8.0))
				self.byte_width = self.size
			else:
				print "Binary control without size."

	def __del__(self):
		pass


	def __repr__(self):
		if self.form == "D":
			return "%s(%s)"%(self.control,self.size)
		elif self.form == "W":
			return "%s(%d)"%(self.control,self.size)
		elif self.form == "B":
			return "%s%d"%(self.control,self.size)
		elif self.form == None:
			return "%s"%(self.control)
		else:
			return "?"


       	def show(self):
		print "Control: %s"%(`self`)


# ----------------------------------------------------------------------
# Friendlier error handling

FMT_EXC_WRITE_1		= "Write error 1"
FMT_EXC_PRINT_1		= "Print error 1"
FMT_EXC_WRITE_2		= "Write error 2"
FMT_EXC_PRINT_2		= "Print error 2"
FMT_EXC_CLOSEPAREN	= "Missing )"
FMT_EXC_BINFORM		= "Bad binary form (form)"
FMT_EXC_BINWIDTH	= "Bad binary form (width)"
FMT_EXC_BININCOMPAT	= "Bad binary form (form and width)"
FMT_EXC_BADCONTROL	= "Bad format control"
FMT_EXC_COMMA		= "Missing comma"
FMT_EXC_STARTOPEN	= "Missing ( at start"
FMT_EXC_ENDCLOSE	= "Missing ) at end"

def explain(tuple):
	"""Explain an "iso8211_format_error" exception, using the CONTEXT and TUPLE.

	Normally, one would catch a random exception and do something like:

		print "%s: %s"%(sys.exc_type,sys.exc_value)

	to print out its name and value(s). This function can be used to
	`translate' an iso8211 format error exception into something a bit
	more helpful, by outputting a proper explanation for the exception.

	For instance:

		fmt = format.Format()
		try:
			fmt.parse(control_string)
		except format.iso8211_format_error,details:
			print "Error parsing format control string\n"
			format.explain(details)

	The first, short, method may be more appropriate in production systems,
	where one expects (!) things to work, but this routine may be more
	useful in diagnostic situations, or where the user is less au fait with
	ISO/IEC 8211 itself.
	"""

	# There are various different format errors
	# - the first item in the tuple should distinguish them

	which = tuple[0]
	rest  = tuple[1:]

	if   which == FMT_EXC_WRITE_1:
		print "Internal error 1 writing format controls item data\n" \
		      "The tuple",rest[0],"contains an unknown tuple code `%s'"%(rest[1])
	elif which == FMT_EXC_PRINT_1:
		print "Internal error 1 printing format controls item data\n" \
		      "The tuple",rest[0],"contains an unknown tuple code `%s'"%(rest[1])
	elif which == FMT_EXC_WRITE_2:
		print "Internal error 2 writing format controls item\n" \
		      "The tuple",rest[0],"contains an unknown tuple code `%s'"%(rest[1])
	elif which == FMT_EXC_PRINT_2:
		print "Internal error 2 printing format controls item\n" \
		      "The tuple",rest[0],"contains an unknown tuple code `%s'"%(rest[1])
	elif which == FMT_EXC_CLOSEPAREN:
		print "Missing `)' to end a subfield size specification\n" \
		      "A `%s' was found at offset %d in `%s',\n" \
		      "when a `)' was expected"%(rest)
	elif which == FMT_EXC_BINFORM:
		print "Unknown binary form `%s'\n"\
		      "The binary form given at offset %d in `%s'\n" \
		      "is not 1 to 5"%(rest)
	elif which == FMT_EXC_BINWIDTH:
		print "The width of a binary form must be a digit\n" \
		      "The value `%s' given at offset %d in `%s' is not"%(rest)
	elif which == FMT_EXC_BININCOMPAT:
		print "The binary form and width are incompatible\n" \
		      "The binary form %s and width %d cannot go together\n" \
		      "(at offset %d in `%s')"%(rest)
	elif which == FMT_EXC_BADCONTROL:
		print "Unrecognised format control `%s'\n" \
		      "The control character at offset %d in `%s'\n" \
		      "is not one of A,I,R,S,C,B,X or b"%(rest)
	elif which == FMT_EXC_COMMA:
		print "Missing comma\n" \
		      "Found `%s' instead of comma at offset %d in `%s'"%(rest)
	elif which == FMT_EXC_STARTOPEN:
		print "The format string does not start with a `('\n" \
		      "The first character in `%s' is not a `('"%(rest)
	elif which == FMT_EXC_ENDCLOSE:
		print "The format string does not end with a `)' to match the opening `('\n" \
		      "The last character in `%s' is not a `)'"%(rest)
	else:
		# Otherwise, just print out the tuple
		print tuple


def test_show(format):
	"""Print out various stuff for the given Format object."""

	print "Format  ",format.octets
	print "Controls",format.controls
	print "Flatlist",format.flatlist
	print "Repeat from",format.repeat_from
	print "Repeat is  ",format.flatlist[format.repeat_from:]
	print "Length is  ",len(format.flatlist)


test_string_1 = "(I(1),I(2),I(3),(A(a),A(b)))"
test_string_2 = "(2(I(4),A,3A(#),R),(I(2)))"
test_string_3 = "(2(I(4),A,3A(#),R),(2(I(2)),B12))"

def test(what=None):
	"""A simple test of parsing, flattening, etc.

	WHAT may be either a number in the range 1..3 (in which case
	a sample format control string is used), or a format control
	string to `test'.
	"""

	if type(what) == type(1):
		if what == 1:
			fmt = test_string_1
		elif what == 2:
			fmt = test_string_2
		elif what == 3:
			fmt = test_string_3
		else:
			print "There is no test string #%d"%what
	elif type(what) == type("string"):
		fmt = what
	else:
		print "test() needs either an integer 1..3 or a string"
		return


	x = Format()
	x.parse(fmt)

	test_show(x)

	print "Writing out DFD:"
	x.write_DFD(sys.stdout)

	print "Iterating over x:"
	count = 0

	for item in x:
		print "   Item %d is %s"%(x.current_index,item)
		count = count + 1
		if count > 20:
			break

