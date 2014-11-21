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

"""iso8211.dfd.py - support for reading DFD files."""

# $Id: dfd.py,v 1.3 2004/04/05 17:44:57 d-rock Exp $

Changes = """Modifications:

1996/08/29	Work started
1996/09/04	Classes Line and Item abstracted and used
1996/09/05	"read dfd" command added to the iso8211 "shell" command
		More work done herein to report on the details of more lines
"""

Version = "0.1 1996/09/05"

import sys
import os
import array
import string

from   __.misc   import printable, iso2022_charset
from   __.format import Format

# I *like* TRUE and FALSE - so define them!

TRUE	= 1
FALSE	= 0

# Exceptions

dfd_file_error  = "ISO 8211/DFD file error"
dfd_mode_error  = "ISO 8211/DFD file mode error"
dfd_parse_error = "ISO 8211/DFD parse error"
dfd_eof         = "ISO 8211/DFD end of file"
dfd_unexpeof    = "ISO 8211/DFD unexpected end of file"


# ----------------------------------------------------------------------
class DFD:
	"""DFD - a class for reading in DFD files and creating the appropriate DDR.

	Initialisation arguments:

		debug			optional - whether to enable debug output

	A DFD object contains:

		name			the name of the DFD file being read
		file			the `stream' for the file itself

		line_num		the line number of the current record in that file
		record			the record as read from the file

		debug			TRUE if we want extra information printed out

		ddr			the DDR we are creating

		in_intro		TRUE if we're in the introductory part of the DFD,
					where we are allowed to have file id, etc
		had_leader		TRUE if we've had leader info for the file

	"""

	def __init__(self,debug=TRUE):

		self.name       = None
		self.file       = None
		self.ddr        = None
		self.line_num   = 0
		self.debug      = debug
		self.in_intro   = TRUE
		self.had_leader = FALSE


	def __del__(self):
		"""Delete a DFD - closes the relevent file."""

		#if self.debug:
		#	print "__del__ for",`self`

		self.close(self)


	def __repr__(self):
		if self.file != None:
			return "ISO 8211 DFD " + self.name
		else:
			return "ISO 8211 DFD - closed"


	def open(self,name,mode="r"):
		"""Open the named DFD.

		name	the name of a DFD file
		mode	the mode to open it with - currently only "r" (read)
			is supported, and that is also the default
		"""

		# Check we don't already have a file open

		if self.file != None or self.name != None:
			raise dfd_file_error,"DFD file %s is already open"%self.name

		# Check we recognised the opening mode

		if mode != "r":
			raise dfd_mode_error,"unknown mode `%s'"%mode

		# OK - we're safe - try to open the file

		self.file = open(name,mode)
		self.name = name

		# And unset various things

		self.ddr      = None
		self.line_num = 0

		self.in_intro   = TRUE
		self.had_leader = FALSE


	def close(self):
		"""Close the DFD."""

		if self.file != None:
			self.file.close()

		self.line_num = 0


	def read(self,name):
		"""Read the named DFD, and return an equivalent DDR."""

		self.open(name,"r")

		try:
			try:
				self._process_file()
			except dfd_parse_error,detail:
				line,text = detail
				self._report_error(line,text)
		finally:
			self.close()


	def _process_file(self):
		"""Read the lines from the DFD and process them."""

		self.line_num   = 0
		self.in_intro   = TRUE
		self.had_leader = FALSE

		# And start our processing loop

		while 1:
			try:
				self._process_next_line()
			except dfd_eof:
				return


	def _report_error(self,line,detail):
		"""Report on a general parsing error."""

		if line == None:
			print "Error in line %d: %s"%(self.line_num,detail)
		else:
			print "Error in line %d: %s"%(line.which,detail)
			print "Line is:",line.record


	def _report_warning(self,line,detail):
		"""Report on a general parsing warning."""

		print "Warning in line %d: %s"%(line.which,detail)
		print "Line is:",line.record


	def _get_next_line(self):
		"""Returns the next non-comment, non-blank line from the current DFD.

		Returns it as the a list of words and strings (see _split_with_strings
		below for details)

		Any leading or trailing whitespace will have been removed (the ACTUAL
		line read is held in "self.record").

		Raises dfd_eof if it cannot find a next line.
		"""

		while 1:
			# Read the next line in

			self.line_num = self.line_num + 1

			record = self.file.readline()
			if not record:
				if self.debug:
					print "Line %3d: EOF"%(self.line_num)
				raise dfd_eof,self.line_num


			line = Line(self.line_num,record)

#			if self.debug:
#				print line

			if line.empty():
				continue			# blank line or comment

			return line


	def _process_next_line(self):
		"""Read the next line and do what seems appropriate."""

		# Read the next significant line in

		line = self._get_next_line()

		# And decide what to do based on the first word...

		action = line[0]

		if action.is_string():
			raise dfd_parse_error,(line,"Line starts with a string")


		if action.match("TITLE"):
			if not self.in_intro:
				raise dfd_parse_error,(line,"TITLE only allowed before LEADER")

			title = self._get_string(line,1,"file-title")
			self._check_rubbish(line,1)

			if self.debug:
				print ">>> TITLE '%s'"%title

			pass

		elif action.match("AUTHOR"):
			if not self.in_intro:
				raise dfd_parse_error,(line,"AUTHOR only allowed before LEADER")

			author = self._get_string(line,1,"file-author")
			self._check_rubbish(line,1)

			if self.debug:
				print ">>> AUTHOR '%s'"%author

			pass

		elif action.match("DATE"):
			if not self.in_intro:
				raise dfd_parse_error,(line,"DATE only allowed before LEADER")

			date = self._get_string(line,1,"file-date")
			self._check_rubbish(line,1)

			if self.debug:
				print ">>> DATE '%s'"%date

			pass

		elif action.match("INCLUDE"):

			file = self._get_string(line,1,"file-spec")
			self._check_rubbish(line,1)

			raise dfd_parse_error,(line,"INCLUDE not yet implemented")

		elif action.match("LEADER"):

			self._check_rubbish(line,0)

			if self.debug:
				print ">>> LEADER"

			self.in_intro = FALSE

			self._read_leader()

			self.in_intro   = FALSE
			self.had_leader = TRUE

		elif action.match("DEFAULT"):

			if not self.had_leader:
				raise dfd_parse_error,(line,"LEADER is required before DEFAULT")

			self._process_default(line)

		elif action.match("FIELD"):

			if not self.had_leader:
				raise dfd_parse_error,(line,"LEADER is required before first FIELD")

			self._read_field(line)

		elif action.match("LOCAL"):

			if self.debug:
				print ">>> LOCAL construct ignored (%s)"%(line[1:])

			pass

		else:
			raise dfd_parse_error,(line,"Unrecognised construct `%s'"%action)



	def _read_leader(self):
		"""Read the contents of a LEADER...END LEADER structure."""

		while 1:
			# Read the next significant line in

			try:
				line = self._get_next_line()

			except dfd_eof,detail:
				raise dfd_unexpeof,"End of file not expected inside LEADER data"

			# Do what seems appropriate

			if line[0].match("END") and line[1].match("LEADER"):

				self._check_rubbish(line,1)

				if self.debug:
					print ">>> END LEADER"

				self.had_leader = TRUE

				return

			elif line[0].match("TAG") and line[1].match("LENGTH"):

				length = self._get_number(line,2,"tag length")
				self._check_rubbish(line,2)

				if self.debug:
					print ">>>    TAG LENGTH %d"%length

				pass

			elif line[0].match("LEVEL"):

				level = self._get_number(line,1,"level")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    LEVEL %d"%level

				pass

			elif line[0].match("VERSION"):

				version = self._get_number(line,1,"version")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    VERSION %d"%version

				pass

			elif line[0].match("FORM"):

				form = self._get_string(line,1,"form")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    FORM '%s'"%form

				pass

			elif line[0].match("INLINE") and line[1].match("EXTENSION") and\
			     line[2].match("CODE"):

				code = self._get_string(line,3,"inline extension code")
				self._check_rubbish(line,3)

				if self.debug:
					print ">>>    INLINE EXTENSION CODE '%s'"%code

				pass

			elif line[0].match("APPLICATION") and line[1].match("INDICATOR"):

				appl = self._get_string(line,2,"application indicator")
				self._check_rubbish(line,2)

				if self.debug:
					print ">>>    APPLICATION INDICATOR '%s'"%printable(appl)

				pass

			elif line[0].match("ESCAPE"):

				esc = self._get_string(line,1,"truncated escape or collection number")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    ESCAPE '%s' (%s)"%(printable(esc),
									 iso2022_charset(esc,TRUE))

				pass

			else:
				raise dfd_parse_error,\
				      (line,"Unrecognised LEADER construct `%s'"%line[0])


	def _process_default(self,line):
		"""Read the rest of a DEFAULT line.:"""

		if line[1].match("PARENT"):

			parent = self._get_string(line,2,"parent tag")
			self._check_rubbish(line,2)

			if self.debug:
				print ">>> DEFAULT PARENT '%s'"%parent

		elif line[1].match("PRINTABLE") and line[2].match("GRAPHICS"):

			graphics = self._get_string(line,3,"printable graphics")
			self._check_rubbish(line,3)

			if self.debug:
				print ">>> PRINTABLE GRAPHICS '%s'"%graphics

		elif line[1].match("ESCAPE"):

			escape = self._get_string(line,2,"truncated escape/collection number")
			self._check_rubbish(line,2)

			if self.debug:
				print ">>> ESCAPE '%s' (%s)"%(printable(escape),
							      iso2022_charset(escape,TRUE))

		else:
			raise dfd_parse_error,\
			      (line,"Unrecognised DEFAULT construct `%s'"%line[1])



	def _read_field(self,line):
		"""Read the contents of a FIELD...END FIELD structure."""

		# Deal with the rest of the FIELD line

		tag  = self._get_string(line,1,"field tag")

		if len(line) > 2:
			name = self._get_string(line,2,"field name")
			self._check_rubbish(line,2)
		else:
			name = ""
			self._check_rubbish(line,1)

		if self.debug:
			print ">>> FIELD '%s' '%s'"%(tag,name)

		# Prime the formatting

		format = Format()

		format.start_format()

		# Deal with the rest of the field structure

		while 1:
			# Read the next significant line in

			try:
				line = self._get_next_line()

			except dfd_eof,detail:
				raise dfd_unexpeof,"End of file not expected inside FIELD data"

			# Do what seems appropriate

			if line[0].match("END") and line[1].match("FIELD"):

				self._check_rubbish(line,1)

				if self.debug:
					print ">>> END FIELD"

				return

			elif line[0].match("PARENT"):

				parent = self._get_string(line,1,"parent tag")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    PARENT '%s'"%parent

				pass

 			elif line[0].match("PRINTABLE") and line[1].match("GRAPHICS"):

				graphics = self._get_string(line,2,"printable graphics")
				self._check_rubbish(line,2)

				if self.debug:
					print ">>>    PRINTABLE GRAPHICS '%s'"%graphics

				pass

			elif line[0].match("ESCAPE"):

				escape = self._get_string(line,1,"truncated escape/collection number")
				self._check_rubbish(line,1)

				if self.debug:
					print ">>>    ESCAPE '%s' (%s)"%(printable(escape),
									 iso2022_charset(escape,TRUE))

				pass

 			elif line[0].match("STRUCTURE") and line[1].match("CODE"):

				# This will read until END FIELD for us

				self._read_labels(line,"STRUCTURE CODE",format)

				if self.debug:
					print format
					#format.write_DFD(sys.stdout)
				return

 			elif line[0].match("NUMERIC") and line[1].match("DESCRIPTOR"):

				# This will read until END FIELD for us

				self._read_labels(line,"NUMERIC DESCRIPTOR",format)

				if self.debug:
					print format
					#format.write_DFD(sys.stdout)
				return

 			elif line[0].match("FOR"):

				# This will read until END FIELD for us

				self._read_labels(line,"FOR",format)

				if self.debug:
					print format
					#format.write_DFD(sys.stdout)
				return


 			elif line[0].match("BY"):

				raise dfd_parse_error,(line,"Cannot have BY before FOR")

 			elif line[0].match("REPEAT"):

				raise dfd_parse_error,(line,"Cannot have REPEAT before FOR")

 			elif line[0].match("END") and line[1].match("REPEAT"):

				raise dfd_parse_error,(line,"Cannot have END REPEAT before FOR")

 			elif line[0].match("THEN"):

				raise dfd_parse_error,(line,"Cannot have THEN before FOR")

			else:
				raise dfd_parse_error,\
				      (line,"Unexpected item %s"%line[0])



	def _read_labels(self,line,which_for,format):
		"""Given a FOR, NUMERIC DESCRIPTOR or STRUCTURE CODE, read the labels/formats.

		WHICH_FOR is the string that got us into this.

		We read until we find END FIELD.
		"""

		# Note if we've had a format control with a label, or whatever

		had_format           = FALSE
		had_format_alone     = FALSE
		had_label_and_format = FALSE

		# Count our REPEAT depth

		repeat_count = 0

		# What we do first depends on why we were called

		if which_for == "STRUCTURE CODE":

			code = self._get_string(line,2,"structure code")
			self._check_rubbish(line,2)

			if self.debug:
				print ">>>    STRUCTURE CODE '%s'"%code

			pass

		elif which_for == "NUMERIC DESCRIPTOR":

			if self.debug:
				print ">>>    NUMERIC DESCRIPTOR",line[2:]

			pass

		elif which_for == "FOR":

			if self.debug:
				print ">>>    FOR",line[1:]

			for item in line[1:]:
				if self.debug:
					print ">>>       label %s"%(item)

		# Then loop reading lines until we find END FIELD

		while 1:
			try:
				line = self._get_next_line()

			except dfd_eof,detail:
				raise dfd_unexpeof,"End of file not expected inside FIELD data"

			# Do what seems appropriate

			if line[0].match("END") and line[1].match("FIELD"):

				self._check_rubbish(line,1)

				if self.debug:
					print ">>> END FIELD"

				format.end_format()

				if repeat_count != 0:
					raise dfd_parse_error,\
					      (line,"END REPEAT missing before END FIELD")

				return

 			elif line[0].match("STRUCTURE") and line[1].match("CODE"):

				raise dfd_parse_error,\
				      (line,"Already had %s in this field definition"%which_for)

 			elif line[0].match("NUMERIC") and line[1].match("DESCRIPTOR"):

				raise dfd_parse_error,\
				      (line,"Already had %s in this field definition"%which_for)

 			elif line[0].match("FOR"):

				raise dfd_parse_error,\
				      (line,"Already had %s in this field definition"%which_for)

 			elif line[0].match("BY"):

				if self.debug:
					print ">>>    BY",line[1:]

				if which_for != "FOR":
					raise dfd_parse_error \
					      (line,"Cannot have BY with %s"%which_for)

				if had_format:
					raise dfd_parse_error,\
					      (line,"Cannot have BY after format controls")

				for item in line[1:]:
					if self.debug:
						print ">>> label %s"%(item)

 			elif line[0].match("REPEAT"):

				if not had_for:
					raise dfd_parse_error,\
					      (line,"Cannot have REPEAT before FOR")

				self._process_repeat(line,format)

				repeat_count = repeat_count + 1

				pass

 			elif line[0].match("END") and line[1].match("REPEAT"):

				self._check_rubbish(line,1)

				if self.debug:
					print ">>>       END REPEAT"

				if not had_for:
					raise dfd_parse_error,\
					      (line,"Cannot have END REPEAT before FOR")

				if repeat_count == 0:
					raise dfd_parse_error,\
					      (line,"END REPEAT does not close a previous REPEAT")
				else:
					repeat_count = repeat_count - 1

				format.end_repeat()

 			elif line[0].match("THEN"):

				self._check_rubbish(line,0)

				if self.debug:
					print ">>>    THEN"

				# Check the end of the `fieldlet'

				if repeat_count != 0:
					raise dfd_parse_error,\
					      (line,"END REPEAT missing before THEN")

				# The next line should be a FOR, STRUCTURE CODE or NUMERIC DESCRIPTOR

				try:
					line = self._get_next_line()

				except dfd_eof,detail:
					raise dfd_unexpeof,"End of file not expected inside FIELD data"

				if line[0].match("FOR"):
					self._read_labels(line,"FOR",format)			# recurse!
				elif line[0].match("NUMERIC") and line[1].match("DESCRIPTOR"):
					self._read_labels(line,"NUMERIC DESCRIPTOR",format)	# recurse!
				elif line[0].match("STRUCTURE") and line[1].match("CODE"):
					self._read_labels(line,"STRUCTURE CODE",format)	# recurse!
				else:
					raise dfd_parse_error,\
					      (line,"THEN must be followed by FOR, NUMERIC DESCRIPTOR or STRUCTURE CODE")

				# And the function we called should have dealt with END FIELD, so just return

				return

			else:
				# We should have one of:
				#	'label'
				#	'label'  format
				#	         format
				# If we have a format, then all succeeding lines must also have formats
				# If we have a format with no label, then any following lines may not have labels
				# Note that:
				#	FOR 'fred' 'jim'
				#	   A(1)
				#	   A(1)
				# is perfectly legal, but:
				#	FOR 'fred'
				#	         A(1)
				#	   'jim' A(1)
				# doesn't look right to me at all - luckily [B.2.6.2 1)] appears to outlaw it

				if not line[0].is_string():
					# We appear to have just a format control

					self._check_rubbish(line,0)

					if had_label_and_format:
						raise dfd_parse_error,\
						      (line,
						       "Not expecting format here (expected label and format)")
					if self.debug:
						print ">>>       format",line[0]

					format.add(line[0].text)

					had_format_alone = TRUE
					had_format       = TRUE

				elif len(line) == 2 and not line[1].is_string():
					# We appear to have a label and a format control

					self._check_rubbish(line,1)

					# Try to guard against illegal forms such as:
					#	FOR 'fred' 'jim'
					#	  'alan'  A(1)

					if had_format_alone:
						raise dfd_parse_error,\
						      (line,
						       "Not expecting label %s here (we already had a format alone)"%line[0])

					if self.debug:
						print ">>>       label %s format %s"%(line[0],line[1])

					format.add(line[1].text)

					had_label_and_format = TRUE
					had_format           = TRUE

				else:
					# Hopefully, we have one or more labels

					if had_format_alone or had_label_and_format:
						raise dfd_parse_error,\
						      (line,
						       "Expecting a format to go with label %s"%line[0])

					for item in line:
						if item.is_string():
							if self.debug:
								print ">>>       label %s"%(item)
						else:
							raise dfd_parse_error,\
							      (line,
							       "Unexpected non-label %s"%item)


	def _process_repeat(self,line,format):
		"""Read the rest of a REPEAT line.:"""

		if line[1].match("TO") and line[2].match("END"):

			self._check_rubbish(line,2)

			if self.debug:
				print "      REPEAT TO END"

			format.start_repeat()

		elif line[1].match("BIT") and line[2].match("FIELD"):

			self._check_rubbish(line,3)

			if self.debug:
				print "      REPEAT BIT FIELD"

			format.start_repeat()

		else:
			repeat = self._get_number(line,1,"repeat count")

			if self.debug:
				print "      REPEAT",repeat

			format.start_repeat(repeat)



	def _check_rubbish(self,line,after):
		"""Grumble about (and ignore) rubbish after item AFTER."""

		if line.rubbish_after(after):
			self._report_warning(line,"Extraneous text ignored: %s"%line.rubbish(after))


	def _check_keyword(self,line,which,expect):
		"""Check for the expected keyword, and raise an exception if it is not there."""

		item = line[which]
		if not item.is_keyword():
			raise dfd_parse_error,\
			      (line,"Expected keyword %s, found string %s instead"%(expect,item))
		elif not item.match(expect):
			raise dfd_parse_error,\
			      (line,"Expected keyword %s, found keyword %s instead"%(expect,item))


	def _get_string(self,line,which,what):
		"""Retrieve the string at offset WHICH, and raise an exception if it is not."""

		item = line[which]
		if not item.is_string():
			raise dfd_parse_error,\
			      (line,"Expected string (%s), found keyword %s instead"%(what,item))
		else:
			return item.text


	def _get_number(self,line,which,what):
		"""Retrieve the number at offset WHICH, and raise an exception if it is not."""

		item = line[which]
		if not item.is_number():
			raise dfd_parse_error,\
			      (line,"Expected number (%s), found %s instead"%(what,item))
		else:
			return int(item.text)


# ----------------------------------------------------------------------
class Line:
	"""A line from the DFD.

	Initialisation arguments:

		which		the record's line number
		record		the record as read from the DFD
		debug		TRUE if the dismantling of the record should be reported on

	A Line object contains:

		which		the record's line number
		record		the record as read from the DFD
		line		the line as a list of Items
	"""

	def __init__(self,which,record,debug=FALSE):

		self.which  = which
		self.record = record
		self.line   = self._split(record,debug)


	def __repr__(self):
		return "Line %3d: %s"%(self.which,self.line)


	def __getitem__(self,which):
		"""Used in iteration - get the n'th Item from this line."""
		
		try:
			item = self.line[which]
		except IndexError:
			raise IndexError,"%d is more than %d"%(which,len(self.line)-1)

		return item


	def __getslice__(self,ii,jj):
		"""Implement slicing - NB: returns a list of Items."""

		list = []
		for count in range(ii,jj):
			list.append(self.line[count])

		return list


	def __len__(self):
		return len(self.line)


	def item(self,which):
		"""Get the which'th item from this record."""

		return self.__getitem__(which)


	def empty(self):
		"""Is this record `empty' - either a blank line, or a comment?"""

		return not len(self.line)	# Length is zero (== false) => empty is true


	def rubbish_after(self,after):
		"""If there are any items after item AFTER, then return TRUE.

		AFTER is the index of the last meaningful item. Note that the
		index of the first item is 0.
		"""

		if len(self.line) > (after+1):
			return TRUE
		else:
			return FALSE


	def rubbish(self,after):
		"""If there are any items after item AFTER, then return them.

		AFTER is the index of the last meaningful item. Note that the
		index of the first item is 0.

		The value returned is either None or a string composed of the
		`rubbish' items separated by spaces.
		"""

		start = after+1
		end   = len(self.line)

		if end > start:
			string = ""
			for count in range(start,end):
				if string != "":
					string = string + " "

				string = string + `self.line[count]`

			return string
		else:
			return None


	def _split(self,record,debug):
		"""Split a line into words and strings, and lose any trailing comments.

		Returns a list of keyword and string Items.

		Assumes that a line is composed of whitespace separated words
		and strings. Strings are delimited by an opening single quote and
		a closing single quote. Doubled single quotes in a string produce
		a single quote in the final string. Comments are started by a
		hyphen, and ended by end of line.
		"""

		# We'll do this the simple but slow way for the moment

		result = []
		this   = ""

		in_string = FALSE
		in_word   = FALSE

		count = 0
		endat = len(record)

		while count < endat:
			char = record[count]

			if debug: print "CHAR `%s'"%char,

			#if char == " " or char == "\t":
			if char in string.whitespace:
				if in_string:
					this = this + char
					if debug: print "add to string"
				elif in_word:
					in_word = FALSE
					result.append(Item(this,TRUE))
					if debug: print "end word",this
				else:
					if debug: print "ignore"
					pass

			elif char == "'":
				if in_string:
					if (count+1) != endat and record[count+1] == "'":
						this  = char
						count = count+1
						if debug: print "escaped quote in",this
					else:
						in_string = FALSE
						result.append(Item(this,FALSE))
						if debug: print "end string",this
		       		elif in_word:
					this = this + char	# Allows fred'jim as a word
					if debug: print "add to word"
				else:
					in_string = TRUE
					this      = ""
					if debug: print "start string"

			elif char == "-":
				if in_string or in_word:
					this = this + char
					if debug: print "add to string/word"
				else:
					if debug: print "end at comment"
					break			# End on a comment character

			else:
				if in_string or in_word:
					if debug: print "add to string/word"
					this = this + char
				else:
					if debug: print "start word"
					in_word = TRUE
					this    = char

			count = count + 1


		if in_word:
			result.append(Item(this,TRUE))
			if debug: print "last word",this
		elif in_string:
			self._report_warning('String "%s" not terminated by "\'"'%this)
			result.append(Item(this,FALSE))

		return result


	def _report_error(self,detail):
		"""Report on a general parsing error."""

		print "Error in line %d: %s"%(self.which,detail)
		print "Line is:",self.record


	def _report_warning(self,detail):
		"""Report on a general parsing warning."""

		print "Warning in line %d: %s"%(self.which,detail)
		print "Line is:",self.record



# ----------------------------------------------------------------------
class Item:
	"""An item in a line from the DFD.

	Initialisation arguments:

		is_keyword	TRUE if it is, FALSE if it is a string
		text		the text of the item

	An Item object contains:

		text		the text of the item
		is_keyword	TRUE if it is, FALSE if it is a string

	An item is either a string or a keyword.
	"""

	def __init__(self,text,is_keyword):

		self.is_keyword = is_keyword
		self.text       = text


	def __repr__(self):

		if self.is_keyword:
			return printable(self.text)
		else:
			return "'" + printable(self.text) + "'"


	def is_keyword(self):
		"""Return true if the item is a keyword."""
		return self.is_keyword


	def is_string(self):
		"""Return true if the item is a string (i.e., not a keyword)."""

		if self.is_keyword:
			return FALSE
		else:
			return TRUE


#		return not self.is_keyword


	def is_number(self):
		"""Return true if the item is a number (not a string)."""

		if self.is_keyword:
			try:
				temp = int(self.text)
				return TRUE
			except:
				return FALSE
		else:
			return FALSE	# not a `keyword'


	def text(self):
		"""Return the text for an item."""
		return self.text


	def match(self,what):
		"""Return true if the item's text matches WHAT (ignores keywordness)."""

		return what == self.text



# ----------------------------------------------------------------------
def test(name):
	dfd_parser = DFD(TRUE)

#	print dfd_parser._split_with_strings("FIELD 'string' 'string2'")

	dfd_parser.read(name)



def test2(record):
	print "Record:",record

	line = Line(1,record,FALSE)

	print line

	count = 1
	for item in line:
		print count,item
		count = count + 1

	if line.empty():
		print "Empty line"
	else:
		print "Non-empty line"


	print "Item %d is %s"%(len(line)/2,line[len(line)/2])

	print line

	rubbish_after(line,len(line)/2)
	rubbish_after(line,len(line)-1)
	rubbish_after(line,len(line))
	rubbish_after(line,len(line)+1)

	print line[1:]
	print line[len(line)/2:len(line)]
	print line[-1:]


def rubbish_after(line,count):
	print "Rubbish after %d:"%count,
	if line.rubbish_after(count):
		print "yes",line.rubbish(count)
	else:
		print "no"
