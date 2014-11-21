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

# $Id: iso8211.py,v 1.9 2004/04/05 17:44:57 d-rock Exp $

"""iso8211.py - support for handling ISO/IEC 8211 files.

See iso8211.__init__.py for details (particularly the "Changes", "Version"
and "Todo" strings).

Initial code: TJ Ibbs, 17 Feb 1994

Initially, just supports sequential access to the file.

The structure of a DDF (as held here) is:

	DDF
	 |
	[1] --- DDR (nb: sub-class of Record)
	 |	\
	 |	{ "tag" :: Field_desc }
	 |		   \
	 |		    field_controls, data_field_name,
	 |		    array_descriptor, format_controls
	 |
	[*] --- Record
	 	\
		[1] --- Leader
		 |
		[1] --- Directory
		 |	 |
		 |	[*] --- Field
		 |		\
		 |		 tag, length, data
		 |
		[1] --- Field_area
"""

import sys
import os
import array
import string
import Dates

# import ni; ni.ni()

from   misc       import *
from   field_desc import *
import format


# ----------------------------------------------------------------------

class DDF:
	"""DDF - an ISO 8211 data definition file.

	This is the class for ISO 8211 files (which are `generally' referred
	to as DDFs, data definition files), and is the main class in the
	iso8211 module.

	Initialisation arguments:

		None

	In "r" (read) mode, the named DDF is opened for read, and the DDR
	(record 0, the data description record) is read in and made the
	current record.

	A DDF object contains:

		name			the name of the DDF
		file			the `stream' for the file itself
		current_record		the current Record (DR)

		next_posn		the position (seek offset) in the file of the
					next record
		next_index		the index of the next record
					(the first record is index 0, which is the DDR)

		R_index			the index of the "R" record in a file (if any)
		R_leader		the leader from that record
		R_directory		the directory from that record

		ddr			the DDR (data definition record, record 0)

	It is possible to iterate over the records in a DDF:

		ddf = iso8211.DDF

		ddf.open("file.ddf","r")

		for record in ddf:
			record.show()

	This example "show"s each record, starting with the first data record
	(i.e., it starts with record 1, not record 0, the DDR).
	"""

	def __init__(self):

		# Just unset the things we want to exist...

		self._unset_things()


	def __del__(self):
		"""Delete a DDF - closes the relevent file."""

		#if debugging:
		#	print "__del__ for",`self`

		self.close(self)


	def __repr__(self):
		if self.file != None:
			return "ISO 8211 DDF " + self.name
		else:
			return "ISO 8211 DDF - closed"


	def __getitem__(self,which):
		"""Used in iteration - get the n'th record.

		Starts with the first data record (record 1), not with
		the DDR (record 0)."""
		
		try:
			record = self.record(which+1)
		except iso8211_index_error:
			raise IndexError

		return record


	def open(self,name,mode="r"):
		"""Open the named DDF.

		name	the name of a DDF
		mode	the mode to open it with - currently only "r" (read)
			is supported, and that is also the default
		"""

		# Check we don't already have a file open

		if self.file != None or self.name != None:
			raise iso8211_file_error,"File %s is already open"%self.name

		# Check we recognised the opening mode

		if mode != "r":
			raise iso8211_mode_error,mode

		# OK - we're safe - try to open the file
		# (use `binary' mode for safety - this doesn't do anything on
		#  some systems, but should be safe anyway, I believe)

		self.file = open(name,mode+"w")
		self.name = name

		if mode == "r":
			self.ddr = DDR(self)	# read the DDR

			self.current_record = self.ddr		# DDR is current record
			self.next_index     = 1			# `next' record is first DR
			self.next_posn      = self.ddr.length	# which is after the DDR


	def close(self):
		"""Close the DDF."""

		if self.file != None:
			self.file.close()
			self._unset_things()


	def _unset_things(self):
		"""Called by "__init__" and "close" to unset things."""

		self.file	    = None
		self.name	    = None

		self.next_posn      = 0		# position of the *next* record
		self.next_index     = 0		# which is assumed to be record 0
		self.current_record = None	# no current record
		self.ddr	    = None	# no DDR

		self.R_index	    = None	# we haven't found an "R" record, so
		self.R_leader       = None	# we don't need to remember any information
		self.R_directory    = None	# about it...


	def next_record(self):
		"""Return the next logical record in the DDF.

		This also becomes the current record.

		Note that if the file was opened with mode "r" then record 0 (the DDR)
		will have been read in automatically when the file was opened, and
		will be the current record (so the `next' record will be record 1).
		"""

		# TODO: Hmmm. There has to be a better way to do this.
		# How about creating an array of record offsets on the fly?

		if self.file == None:
			raise iso8211_file_error,"There is no file open"

		self.current_record = Record(self,self.next_posn,self.next_index)
		self.next_posn      = self.next_posn  + self.current_record.length
		self.next_index     = self.next_index + 1

		return self.current_record


	def record(self,which):
		"""Return the record with index WHICH, where the DDR has index 0.

		This also becomes the current record.

		There are doubtless more efficient ways of doing this, but if the
		record wanted is the current record, we return it, otherwise, we
		rewind if we need to, and then start reading records until we get
		to the one with the right index.

		(The advantage of this approach is that it enables us to deal
		correctly with the records after an "R" record, which don't
		have their own leader/directory.)
		"""

		if self.file == None:
			raise iso8211_file_error,"There is no file open"

		if which < 0:
			raise iso8211_index_error,which,"record indices must be 0 or more"
		elif which == self.current_record.index:
			return self.current_record		# we already have it in hand
		elif which < self.current_record.index:
			self.rewind()				# it's earlier than we are now

		# Here, we are positioned before the record we want, so we
		# must read until we get to it. We will have the right record
		# in hand when self.next_index is 1 greater than which (ie, the
		# next record to be read would be the one after the one we want)

		while self.next_index <= which:
			self.next_record()

		return self.current_record


	def rewind(self):
		"""Rewind to the start of the DDF.

		Note that this makes the next record to be read the DDR (record 0).
		"""

		self.next_posn      = 0
		self.next_index     = 0
		self.current_record = None

		# And don't forget to forget any "R" record information
		# (as we patently haven't read it yet)

		self.R_index     = None		# Is this needed?
		self.R_leader    = None
		self.R_directory = None


	def write_DFD(self,dfd_name,merge=TRUE,title=None,author=None,date=None):
		"""Write the contents of the current DDR to the specified DFD file.

		DFD_NAME	is the name of the file to write to. It will be
				created as a new text file.

		MERGE		is TRUE if labels and formats should be intertwined
				when possible, and FALSE if they never should be

		TITLE		is the string to be used in the file identification
				TITLE - if None, then something will be made up.
		AUTHOR		is the string to be used in the file identification
				AUTHOR - if None, then something will be made up.
		DATE		is the string to be used in the file identification
				DATE - if None, the current date will be used.
		"""

		# So open the specified DFD file

		dfd = open(dfd_name,"w")

		today = Dates.today()

		# Write out our file identification information

		if title == None:
			head,tail = os.path.split(self.name)
			title = "DFD for %s"%tail

		if author == None:
			author = "Python module iso8211"

		if date == None:
			date = today

		dfd.write("TITLE        '%s'\n"%title)
		dfd.write("AUTHOR       '%s'\n"%author)
		dfd.write("DATE         '%s'\n"%date)

		# And some useful comments

		dfd.write("\n"
			  "-- This DFD (Data field definition) file was automatically created\n"
			  "-- by the Python iso8211 module from the DDF (Data definition file)\n"
			  "-- %s on %s\n\n"%(self.name,today))

		# And now do the work...

		self.ddr.write_DFD(dfd,merge)


	def show(self):
		"""Print out the contents of the DDF."""

		print self

		self.ddr.show()

		for record in self:
			print
			record.show()


		# Use the following instead if you want to see the exception
		# that is used to terminate the file reading...

#		self.rewind()
#		record = self.next_record()	# ignore the DDR, we already did that
#
#		try:
#			while TRUE:
#				record = self.next_record()
#				record.show()
#
#		except EOFError, detail:
#			print "End of file: ",detail


# ----------------------------------------------------------------------
class Record:
	"""An ISO 8211 (logical) record.

	For consistency, this class should probably be called "DR"
	(i.e., data record), but I personally think that would be unhelpful.

	Initialisation arguments:

		ddf		the DDF containing this record
		posn		our seek offset in that DDF
		index		which record we are (0 is the DDR)

		reading		are we reading, rather than writing
				(defaults to TRUE)

	A Record object contains:

		ddf		the associated DDF
		posn		the position of this record in the file
		index		the index of this record in the file

		length		the record's length

		leader		the record's leader
		directory	the record's directory
		field_area	the record's field area

	It is possible to iterate over the fields in a record:

		for field in record:
			field.show()

	This example "show"s each field, starting with the first field, which
	has index 0.

	NOTE that we rely upon our knowledge that, if we are reading in record
	     <n>, then we will previously have read in record <n-1>, to allow
	     simple jandling of "R" records.
	"""

	def __init__(self,ddf,posn,index,reading=TRUE):

		self.ddf   = ddf		# which DDF we're a record of
		self.posn  = posn		# where we start in it
		self.index = index		# which record we are

		# I'm initialising these in case `leader' raises an
		# end of file error - in which case I want a sanitary
		# record structure...

		self.directory  = None
		self.field_area = None
		self.length     = 0

		# If we are reading, read in the record's data

		if reading:
			self._read(ddf,posn,index)


	def _read(self,ddf,posn,index):
		"""Read a record's data from disk."""

		# If this is a normal record, read the leader information
		# Otherwise, use the leader we are given

		if ddf.R_leader == None:
			self.leader = Leader(self,posn)
		else:
			self.leader = ddf.R_leader
			self.leader.record = self	# Don't forget to personalise it

			# The field area in records after an "R" record starts
			# at the start of the record, so doctor the leader to suit

			if self.leader.base_address != 0:	# i.e., we haven't done it yet
				leader = self.leader

				# The record is only as long as the field area

				leader.record_length = leader.record_length - leader.base_address
				leader.base_address  = 0


		# We care particularly about the record length,
		# so keep our own copy for convenience

		self.length = self.leader.record_length

		# Set up the field area

		self.field_area = Field_area(self,posn+self.leader.base_address)

		# If this is a normal record, read the directory (which
		# tells us what is in the field area)
		# Otherwise, use the directory we are given

		if ddf.R_directory == None:
			self.directory = Directory(self,posn+24)
		else:
			self.directory = ddf.R_directory
			self.directory.record = self	# Don't forget to personalise it

		# If the leader said this is an "R" record, then we need
		# to remember the leader and directory for future records
		# (but don't bother to do it after the first time!)

		if self.leader.leader_id == "R" and ddf.R_leader == None:
			ddf.R_index     = self.index		# Is this needed?

			ddf.R_leader    = self.leader
			ddf.R_directory = self.directory


	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.ddf	= None
		self.leader     = None
		self.field_area = None
		self.directory  = None


	def __repr__(self):
		return "Record "+`self.index`+" attached to "+`self.ddf`


	def __getitem__(self,which):
		"""Used in iteration - get the n'th field."""
		
		try:
			field = self.field(which)

		except iso8211_index_error:
			raise IndexError

		return field


	def field_entry(self,index):
		"""Return the INDEX'th field's entry from the directory."""

		return self.directory.entry(index)


	def field(self,index):
		"""Return the INDEX'th field from the record.

		The first field has index 0."""

		return self.directory.field(index)


	def show(self,with_leader=TRUE):
		"""Print out information about this record.

		If WITH_LEADER is specified, and is false, then the
		leader data for this record will not be show.
		"""

		if self.index == None:
			print "Record <unknown index> at offset %d"%(self.posn)
		else:
			print "Record %d at offset %d"%(self.index,self.posn)

		if with_leader:
			self.leader.show()

		self.directory.show()


# ----------------------------------------------------------------------
class Leader:
	"""An ISO 8211 record's leader.

	Initialisation arguments:

		record		the Record we are in	       (is this needed?)
		posn		the seek offset of the record  (is this needed?)
		reading		are we reading, rather than writing
				(defaults to TRUE)

	A Leader object contains:

		record			the associated Record
		posn			our location in the file (same as the record's!)
		octets			the leader as a 24 byte octet string

		record_length		the record length
		leader_id		the leader id ("L", "D" or "R")
		base_address		base address of the field area

		sizeof_field_len	size of Field Length   field in Entry Map
		sizeof_field_pos	size of Field Position field
		sizeof_field_tag	size of Field Tag      field

	and, if it is the DDR leader:

		interchange_level       the interchange level
		inline_code_extension   the inline code extension indicator
		version_number          the version `number'
		application_indicator   the application indicator
		field_control_length	the field control length
		extended_character_set	the extended character set indicator

	Note that the following are held as integers:

		"interchange_level"	(1..3),
		"version_number"    	(0 or 1, according to whether the actual value
				    	 was " " or "1"),
		"field_control_length".

	The other DDR specific leader values are held as characters.
	"""

	def __init__(self,record,posn,reading=TRUE):
		self.record = record	# back-reference
		self.posn   = posn	# just in case

		# Unset various things - these are only used in DDR leaders

		self.interchange_level      = None
		self.inline_code_extension  = None
		self.version_number         = None
		self.application_indicator  = None
		self.field_control_length   = None
		self.extended_character_set = None

		# If we are reading, read in the leader data

		if reading:
			self._read(record,posn)


	def _read(self,record,posn):
		"""Read in the leader data from disk."""

		# Read the leader data

		file = record.ddf.file

		file.seek(posn,SEEK_START)
		self.octets = file.read(24)

		if self.octets[0] == CIRCUMFLEX:
			raise EOFError,"Circumflex detected at end of file"

		# Extract the things that we get in all DRs

		self._extract_data(self.octets)

		# If this is the DDR leader, extract its special information

		if self.leader_id == "L":
			self._extract_DDR_data(self.octets)

		# If this is NOT the DDR leader, check that the size of field tag field
		# gives the same size as in the DDR's leader (5.2.1.5.4, last sentence)

		if self.leader_id != "L":
			# Find the DDR (!)
			ddr = self.record.ddf.ddr

			if self.sizeof_field_tag != ddr.leader.sizeof_field_tag:
				print "Warning: Size of field tag in record %s is %d\n" \
				      "         It should be %d (to match the DDR)"%\
				      (self.record.index,
				       self.sizeof_field_tag,
				       ddr.leader.sizeof_field_tag)


	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.record = None


	def __repr__(self):
		return "Leader to " + `self.record`


	def _extract_data(self,octets):
		"""Extract the data we care about from our octet string."""

		# Extract the things that we get in all DRs

		self.record_length = int(octets[0:5])
		self.leader_id     = octets[6:7]
		self.base_address  = int(octets[12:17])

		self.sizeof_field_len = int(octets[20:21])
		self.sizeof_field_pos = int(octets[21:22])
		self.sizeof_field_tag = int(octets[23:24])

		#++++++++++++++++++++
		#print "Leader:",octets[0:24]
		#print "record len:  ",self.record_length
		#print "leader id:   ",self.leader_id
		#print "base address:",self.base_address
		#print "size of field len:",self.sizeof_field_len
		#print "size of field pos:",self.sizeof_field_pos
		#print "size of field tag:",self.sizeof_field_tag
		#++++++++++++++++++++

	def _extract_DDR_data(self,octets):
		"""Extract the data we only get in the DDR leader."""

		self.interchange_level      = int(octets[ 5: 6])
		self.inline_code_extension  = octets[ 7: 8]
		self.version_number         = octets[ 8: 9]
		self.application_indicator  = octets[ 9:10]
		self.field_control_length   = int(octets[10:12])
		self.extended_character_set = octets[17:20]

		# Convert the version number *into* a number

		if self.version_number == ISO8211_V0:
			self.version_number = 0
		elif self.version_number == ISO8211_V1:
			self.version_number = 1
		else:
			raise iso8211_version_error,self.version_number


	def chars(self,rp,len):
		"""Return LEN characters starting at the given RP."""

		return self.octets[rp:rp+len]


	def write_DFD(self,dfd):
		"""Write out the appropriate DFD data for this leader.

		This routine doesn't do anything if we are not in a DDR.
		"""

		if self.leader_id != "L":
			return

		dfd.write("LEADER\n")

		dfd.write("   TAG LENGTH             %d\n"%self.sizeof_field_tag)
		dfd.write("   LEVEL                  %d\n"%self.interchange_level)
		dfd.write("   VERSION                %d\n"%self.version_number)

		# For the moment, we aren't handling binary forms, so this MUST be a space
		# (or we couldn't have read the DFD)
		dfd.write("   FORM                   ' '\n")

		dfd.write("   INLINE EXTENSION CODE  '%s'\n"%self.inline_code_extension)
		dfd.write("   APPLICATION INDICATOR  '%s'\n"%self.application_indicator)
		dfd.write("   ESCAPE                 '%s' -- hex %s (%s)\n"%\
			  (self.extended_character_set,
			   pretty_hex(self.extended_character_set),
			   iso2022_charset(self.extended_character_set,in_ddr=TRUE)))

		dfd.write("END LEADER\n")


	def show(self):
		"""Print out the contents of this leader."""

		# If this is a record following an "R" record, then don't
		# print out the leader (since there isn't one)

		if self.leader_id == "R" and self.base_address == 0:
			pass
		else:
			self.show_full()


	def show_full(self):
		"""Print out the contents of this leader."""

		print "    Leader"
##		print "        string = `%s'"%self.octets
		print "        record length              = %d"%self.record_length

		if self.leader_id == "L":
			print "        interchange level          = %d"%self.interchange_level

		print "        leader id                  = `%s'"%printable(self.leader_id)

		if self.leader_id == "L":
			print "        inline code extension      = `%s'"%\
			      printable(self.inline_code_extension)
			print "        version number             = %d"%self.version_number
			print "        application indicator      = `%s'"%\
			      printable(self.application_indicator)
			print "        field control length       = %d"%self.field_control_length

		print "        base address of field data = %d"%self.base_address

		if self.leader_id == "L":
			print "        extended character set     = `%s' (hex %s: %s)"%\
			      (printable(self.extended_character_set),
			       pretty_hex(self.extended_character_set),
			       iso2022_charset(self.extended_character_set,in_ddr=TRUE))


		print "        entry map:"
		print "            size of field length   = %d"%self.sizeof_field_len
		print "            size of field position = %d"%self.sizeof_field_pos
		print "            size of field tag      = %d"%self.sizeof_field_tag



# ----------------------------------------------------------------------
class Directory:
	"""An ISO 8211 record's directory

	Initialisation arguments:

		record		the record we are in	       (is this needed?)
		posn		the seek offset of the record  (is this needed?)
		reading		are we reading, rather than writing
				(defaults to TRUE)

	A Directory object contains:

		record		the associated record

		entry_size	the size of a field's entry in the directory
		num_entries	how many directory entries there are

	And the `private' value:

		_octets		our data (this is private because future versions
				of this class may read directly from the file, for
				large directories, which do not (easily) fit in
				memory)

	"""

	def __init__(self,record,posn,reading=TRUE):
		self.record     = record	# back-reference
		self.posn       = posn		# where we are in the file

		# Work out the size of a directory entry, for convenience

		leader = self.record.leader
		self.entry_size = leader.sizeof_field_len + leader.sizeof_field_pos + \
							    leader.sizeof_field_tag

		# If we are reading, read in the directory data

		if reading:
			self._read(record,posn,leader)


	def _read(self,record,posn,leader):
		"""Read in the directory data from disk."""

		# Work out the directory length
		# - let's do this the slow way...

		field_area_length = record.length - leader.base_address
		directory_length  = record.length - field_area_length - 24

		# Read the directory into an internal string
		# (this assumes that the directory is not TOO BIG)

		# (NOTE that a directory is always at least one octet long,
		#  since the terminating FT is required)

		file = record.ddf.file

		file.seek(posn,SEEK_START)
		self._octets = file.read(directory_length)

		if self._octets == "":
			raise EOFError,"Trying to read directory in record %s"%record.index

		#++++++++++++++++++++
		#print "record length:    ",record.length
		#print "base address:     ",leader.base_address
		#print "field area length:",field_area_length,\
		#      "= record length - base address"
		#print "directory length: ",directory_length,\
		#      "= record length - field area length - 24"
		#print "size of field len:",leader.sizeof_field_len
		#print "size of field pos:",leader.sizeof_field_pos
		#print "size of field tag:",leader.sizeof_field_tag
		#pos = 0
		#while pos < directory_length:
		#	print self._octets[pos : pos+self.entry_size]
		#	pos = pos + self.entry_size
		#++++++++++++++++++++

		# The last character should be an FT, and it should be
		# at position (N * entry_size) + 1

		if (directory_length % self.entry_size) != 1:
			remainder = directory_length%self.entry_size
			raise iso8211_dir_error,(EXC_DIR_SIZE,
						 self.entry_size,
						 directory_length,
						 self._octets[-remainder])

		if self._octets[-1] != FT:
			raise iso8211_dir_error,(EXC_DIR_NOTFT,self._octets[-1])
		
		self.num_entries = (directory_length-1) / self.entry_size

		# If this is a DR, we should then really check that:
		# a) if this is a version 0 file, there is a 0..1 field (it was compulsory)
		# b) that there are no 0..0 or 0..2 or 0..3 fields (they're only in the DR)
		# c) that there are no 0..4 through 0..8 fields (they're not used)
		# d) that any 0..9 field occurs first in the record
		# e) that any 0..1 field occurs first in the record (except after a 0..9 field)

		#print "%d entries in the directory:" % self.num_entries

		self.fieldlist = []

		# split out the fields in the field area based on their unit size
		# TODO: make delimited fields work, too.
		for index in range(self.num_entries):
			entr = Directory_entry(self, self.entry(index)) 
			#print entr
			self.fieldlist.append((entr.tag, entr.pos, entr.len))
			#if self.record.index != 0:
				## fill field list based on provided sizes. Each entry is of the form
				## (tag, offset, len)
				#unit_size = self.record.ddf.ddr.dict[entr.tag].format_controls.unit_size
				#print "  unit size = %d" % unit_size
				
				#if unit_size == 0:
					#print "  fields = 1"
					#self.fieldlist.append((entr.tag, entr.pos, entr.len))
				#else:
					#print "  fields = %d" % (entr.len / unit_size)
					#for offset in range(0,entr.len, unit_size):
						#self.fieldlist.append((entr.tag, entr.pos + offset, unit_size))

		self.num_fields = len(self.fieldlist)

		if debugging:
			print "Fieldlist: "
			for fld in self.fieldlist:
				print fld

	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.record = None


	def __repr__(self):
		return "Directory to " + `self.record`


	def entry(self,index):
		"""Return a specific directory entry (as a string), by index."""

		if index < 0:
			raise iso8211_index_error,(index,"field indices must be 0 or more")

		if index >= self.num_entries:
			raise iso8211_index_error,(index,
						   "there are only "+`self.num_entries`+
						   " in the directory")

		start = index * self.entry_size
		return self._octets[start : start+self.entry_size]


	def field(self,which):
		"""Get the data for the specified field.

		The first field in a directory has index 0."""

		return Field(self,which)


	def show_as_record(self,with_leader=TRUE):
		"""Print out the contents of this directory as if it were a normal record."""

		self.record.show(with_leader)


	def show(self):
		"""Print out the contents of this directory."""

		if self.num_entries == 1:
			print "    Directory contains 1 entry"
		else:
			print "    Directory contains %d entries"%(self.num_entries)

		for ff in range(self.num_entries):
			field = self.field(ff)
			field.show()


# ----------------------------------------------------------------------
class Directory_entry(object):
	"""A component of a normal field's directory. Basically a convenience
	class for breaking out the tag, length and offset from the directory
	"""

	def __init__(self, directory, octets):
		leader = directory.record.leader

		self.tag = octets[:leader.sizeof_field_tag]

		# don't count the FT here...
		self.len = int(octets[leader.sizeof_field_tag:leader.sizeof_field_len + leader.sizeof_field_tag]) - 1
		
		self.pos = int(octets[leader.sizeof_field_tag + leader.sizeof_field_len: directory.entry_size])

	def __repr__(self):
		return "  Directory entry: %s, len %d, pos %d" % (self.tag, self.len, self.pos)
	
# ----------------------------------------------------------------------
class Field_area:
	"""An ISO 8211 record's field area

	Initialisation arguments:

		record		the record we are in (is this needed?)
		reading		are we reading, rather than writing
				(defaults to TRUE)

	A Field_area object contains:

		record		the associated record

	And the `private' value:

		_octets		our data (this is private because future versions
				of this class may read directly from the file, for
				large field areas, which do not (easily) fit in
				memory)

	"""

	def __init__(self,record,posn,reading=TRUE):
		self.record    = record	# back-reference
		self.posn      = posn	# our location in the file

		# If we are reading, read in the field area

		if reading:
			self._read(record,posn)


	def _read(self,record,posn):
		"""Read in the field area from disk."""

		# Read the field area into an internal string
		# (this assumes that the field area is not TOO BIG)

		self.length = record.length - record.leader.base_address

		# Beware - it is legal to have a record with no data

		if self.length == 0:
			self._octets = ""
		else:
			file = record.ddf.file

			file.seek(posn,SEEK_START)
			self._octets = file.read(self.length)

			if self._octets == "":
				raise EOFError,"Trying to read field area in record %s"%record.index


	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.record = None


	def __repr__(self):
		return "Field area in " + `self.record`


	def data(self,where,length):
		"""Return the specified field data.

		- do we really need to remember the string and its length
		  within this class?
		"""

		return self._octets[where:where+length]


	def show(self):
		"""Show the contents of a field area."""

		print "Field area, length %d"%(self.length)
		print "- show the contents of the field area by showing the directory..."

def _unsigned_int(msof,data):
	"""Interpret the octets of DATA as a signed integer in MSOF/LSOF order.

	If MSOF is TRUE, we have most significant octet first, otherwise
	we have least significant octet first.

	We can't just use "atoi" because we don't know the byte order of
	the machine we are running on.

	NOTE: THIS IS NOT PORTABLE, AS IT ASSUMES BYTE ORDER.
	"""

	size   = len(data)
	result = 0

	if msof:
		for count in range(size):		# eg: 0, 1, 2, 3 for size = 4
			result = (result << 8) + ord(data[count])
	else:
		for count in range(size-1,-1,-1):	# eg: 3, 2, 1, 0 for size = 4
			result = (result << 8) + ord(data[count])

	return result


# ----------------------------------------------------------------------
class Field:
	"""An ISO 8211 field.

	Used to hold information about an ISO 8211 field
	- this includes information from the directory, and also the field's
	data from the field area

	Initialisation arguments:

		directory	the directory to to use to find the field
		index		which field - the first field is at index 0
		reading		are we reading, rather than writing
				(defaults to TRUE)

	A Field object contains:

		record		the associated record

		index		index of the field's directory entry in the directory

		tag		the field's tag
		length		the length of the field's data
				(redundant, since we can get it from the data!)
		posn		the position of the field's data in the field area
		data		the field's data

	"""

	def __init__(self,directory,index,reading=TRUE):
		if index < 0:
			raise iso8211_index_error(index,"field index must be 0 or more")

		if directory.record.index == 0 and index >= directory.num_entries:
			raise iso8211_index_error(index,
						   "there are only "+`directory.num_entries`+
						   " in the directory")

		if directory.record.index > 0 and index >= directory.num_fields:
			raise iso8211_index_error(index,
						   "there are only "+`directory.num_fields`+
						   " in the directory")

		self.record = directory.record	# back reference
		self.index  = index		# which field we are (0..n)

		# If we are reading, retrieve the data for this field

		if reading:
			if self.record.index == 0:
				self._read_ddr(directory, index)
			else:
				self._read_datafield(directory, index)


	def _read_ddr(self,directory,index):
		"""Retrieve the data for this DDR field from the directory and field area."""

		# Read the directory entry for this field
		# print "Reading DDR field"

		dir_entry = directory.entry(index)

		# Dissect it

		start    = 0
		end      = self.record.leader.sizeof_field_tag
		self.tag = dir_entry[start:end]

		start       = end
		end         = end + self.record.leader.sizeof_field_len
		self.length = int(dir_entry[start:end])

		start     = end
		end       = end + self.record.leader.sizeof_field_pos
		self.posn = int(dir_entry[start:end])

		# And retrieve the field data as well

		field_area = self.record.field_area
		self.data  = field_area.data(self.posn,self.length)

		# Debugging code used to look at some dodgy DDF data, when the
		# producer thought they WERE writing data out to field 0001,
		# even thought this software claimed otherwise
		##if self.tag == "0001":
		##	print "dir_entry",directory.entry(index)
		##	print "tag",self.tag
		##	print "len",self.length
		##	print "pos",self.posn
		##	print "data",`self.data`

		# (Can self.length be zero? - NO, because we need a terminating FT...)

		if self.length == 0 or len(self.data) == 0 or self.data[-1] != FT:
			raise iso8211_error,\
			      ("Data for field %s (%s) in record %s does not end with FT\n" \
			       "Data is `%s'"%(self.index,self.tag,self.record.index,self.data))

	def _read_datafield(self,directory,index):
		"""Retrieve the data for this data field from the directory and field area."""

		# Read the directory entry for this field
		# print "Reading datafield"

		dir_entry = directory.fieldlist[index]

		# Dissect it

		self.tag = dir_entry[0]

		self.posn = dir_entry[1]

		self.length = dir_entry[2]

		# And retrieve the field data as well

		field_area = self.record.field_area

		# We fake the FT for this field, since we really just
		# grabbed exactly the right amount of data ###FIXME changed

		self.data  = field_area.data(self.posn,self.length+1)

		# print "Tag = %s, Data = %s" % (self.tag, printable(self.data))

	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.record = None


	def __repr__(self):
		return "Field "+`self.index`+" in " + `self.record`



	def split(self):
		"""Split this field's data into subfields.

		This is done according to the subfield labels (if any) and the
		format controls (if any - note that the field controls can often
		provide default format controls if none are explicitly provided).

		Returns a list of tuples:

			(subfield label, subfield control, subfield data)

		where:
			"subfield label"	is None or the expanded label for this
						subfield. For a Cartesian label, this is
						what you might expect. For a fixed array
						field, this is the appropriate descriptive
						index - for instance, "2,3".
			"subfield control"	is None or a Control object, containing the
						format control for this subfield.
			"subfield data"		is a string containing the data for this
						subfield.

		Note that "X" controls are not labelled, and do not contribute to the
		list, although they do cause data to be skipped.

		The routine "parse_item(datatype,data)" (qv) may be used to turn the
		string into a value of the appropriate datatype.

		Raises iso8211_error if there are no format controls or labels.
		"""

		# Look up our field's definition in the DDR

		ddr        = self.record.ddf.ddr
		field_desc = ddr.dict[self.tag]

		# If we don't have any format controls, or any labels, then
		# we're a bit stumped. We should always have at least some
		# sort of format control, since the field controls lead to
		# a default value, and ditto for the array descriptor.
		# So all one can really do is raise an exception, I guess.

		if field_desc.format_controls == None or field_desc.array_descriptor == None:
			raise iso8211_error, \
			      "Unable to split data - no format controls or labels\n" \
			      "Reading data for field %s (%s) in record %s\n"% \
			      (self.index,self.tag,self.record.index)


		# Lose the final FT from our data

		if len(self.data) == 0 or self.data[-1] != FT:
			raise iso8211_error(
			      "Data for field %s (%s) in record %s does not end with FT\n" \
			       "Data is `%s'"%(self.index,self.tag,self.record.index,self.data))
			#print "Data for field %s (%s) in record %s does not end with FT\n" \
			#       "Data is `%s'"%(self.index,self.tag,self.record.index,printable(self.data))
			#data = self.data
		else:
			data = self.data[:-1]

		# And process it

		if field_desc.array_descriptor.unlabelled:
			list = self._split_unlabelled(data)
		else:
			list = self._split_labelled(data)

		return list



	def _split_unlabelled(self,data):
		"""Split this unlabelled field's data into subfields.

		Returns a list of tuples:

			(None, subfield control, subfield data)

		where:
			"subfield control"	is None or a Control object, containing the
						format control for this subfield.
			"subfield data"		is a string containing the data for this
						subfield.

		Note that "X" controls are not labelled, and do not contribute to the
		list, although they do cause data to be skipped.
		"""

		# Look up our field's definition in the DDR

		ddr        = self.record.ddf.ddr
		field_desc = ddr.dict[self.tag]

		list = []

		for control in field_desc.format_controls:
			#print "Format %s"%(control)

			try:
				item,data = read_item(data,control)
			except IndexError:
				# End of data
				break
			except ValueError,why:
				print "Problem reading data for `%s' (%s):\n"\
				      "        %s"%(self.tag,control,why)
				return list

			list.append((None,control,item))

			if len(data) == 0:
				break

		return list



	def _split_labelled(self,data):
		"""Split this labelled field's data into subfields.

		Returns a list of tuples:

			(subfield label, subfield control, subfield data)

		where:
			"subfield label"	is None or the expanded label for this
						subfield. For a Cartesian label, this is
						what you might expect. For a fixed array
						field, this is the appropriate descriptive
						index - for instance, "2,3".
			"subfield control"	is None or a Control object, containing the
						format control for this subfield.
			"subfield data"		is a string containing the data for this
						subfield.

		Note that "X" controls are not labelled, and do not contribute to the
		list, although they do cause data to be skipped.
		"""

		# Look up our field's definition in the DDR

		ddr        = self.record.ddf.ddr
		field_desc = ddr.dict[self.tag]
		format     = field_desc.format_controls
		labels     = field_desc.array_descriptor

		list = []

		if labels.variable:
			# Work out the expanded labels for this variable array
			labels_iter,data = self._find_var_labels(data)
		else:
			# We can just iterate over the array descriptor itself
			labels_iter = labels

		# Iterate throught the labels

		format.rewind()		# just in case (shouldn't be needed)
		for label in labels_iter:
			# Get the format control for this item

			control = format.next_item()

			# "X" items are simply ignored - they are not labelled

			while control.control == "X":
				item,data = read_item(data,control)
				control   = format.next_item()
				#print "Ignoring `X' item:",
				#print item

			#print "Label %s, format %s"%(label,control)

			try:
				item,data = read_item(data,control)
			except IndexError:
				# End of data
				return list
			except ValueError,why:
				print "Problem reading data for `%s' (subfield %s, %s):\n"\
				      "        %s\n" \
				      "        Unread data: `%s'"% \
				      (self.tag,label,control,why,printable(data))
				return list

			list.append((label,control,item))

		return list


	def _find_var_labels(self,data):
		"""Work out the expanded labels for a variable array field.

		Returns the tuple:

			(labels,data)

		where "labels" is the expanded labels list, and
		      "data"   is what is left of the field's data
		"""

		# The array dimensions are in the data
		# Create a format control to read a UT delimited integer

		control = __.format.Control("I",None,None)

		# The first integer is the dimensionality

		dimension,data = read_and_parse_item(data,control)

		# Followed by that number of extents

		extents = []
		for count in range(dimension):
			extent,data = read_and_parse_item(data,control)
			extents.append(extent)

		# So create a list of label names from those extents

		return expand_labels_num(extents),data


	def show(self):
		"""Print out the contents of this field."""

		print "    Field",self.index
		print "        tag  =",`self.tag`

		if debugging:
			self.record.ddf.ddr.dict[self.tag].show()
			print "        data =",`printable(self.data[:-1])` # absent the final FT

		# Split the data up into subfields

		try:
			list = self.split()
		except iso8211_error,what:
			print "%s: %s"%(iso8211_error,what)
			print "        data =",`printable(self.data[:-1])` # absent the final FT
			return

		# Work out the maximum length of a label string

		if debugging:
			print "        list = ",list

		maxlen = 0
		for item in list:
			label = item[0]

			if label == None:
				continue
			elif len(label) > maxlen:
				maxlen = len(label)

		# And finally report on the data

		count = 0
		for item in list:
			label,control,value = item

			if count == 0:
				print "        data =",
			else:
				print "              ",

			count = count + 1

			if label == None:
				temp = "''"
			else:
				temp = "'%s'"%label

			print "%-5s %-*s:"%(control,maxlen+2,temp),
			if label == 'NAME':
				print "%s %s" % (_unsigned_int(FALSE, value[0]), _unsigned_int(FALSE, value[1:]))
			else:
				try:
					value = parse_item(control.control,value)
				except ValueError,what:
					print "%s: %s"%(ValueError,what)
					continue

				if type(value) == type("string"):
					print `printable(value)`
				else:
					print `value`

# ----------------------------------------------------------------------
class DDR(Record):
	"""An ISO 8211 DDR (data definition record).

	This is a sub-class of the DR class, `Record'.

	Initialisation arguments:

		ddf		the DDF we are in
		reading		are we reading, rather than writing
				(defaults to TRUE)

	A DDR object contains (as well as its Record data):

		dict			a dictionary of {field tag :: field definition}
					derived from the DDR

		list			a list of field tags, in the order they occur
					in the DDR

		parents			a dictionary of {field tag :: parent field tag}
					derived from the information in field 0..0 (if present)
		child_list		a list of the child tags, in the order they occur
					witrhin field 0..0
	"""

	def __init__(self,ddf,reading=TRUE):

		# Perform the "record" initialisation
		# - the DDR is the zeroth record, which starts at the start of the file

		Record.__init__(self,ddf,0,0,reading)

		# So far we know nothing about field tag pairs

		self.parents    = {}
		self.child_list = []

		# The main thing special about a DDR is its fields - we keep a
		# dictionary of field definitions, and a list of the tags in the
		# order they occur.

		self.dict = {}
		self.list = []

		if reading:
			self._populate_innards()


	def _populate_innards(self):
		"""Populate our innards from the data read elsewhere."""

		# Populate the dictionary of field definitions, and the list of
		# tags (ordered according to the order they came in)

		for field in self:
			tag  = field.tag
			data = field.data

			size = self.leader.sizeof_field_tag

			# Some tags are special

			if tag == nought_tag(size,0):
				# File control field
				self.dict[tag] = Field_desc_00(self,tag,data)

			elif tag == nought_tag(size,1):
				# Record identifier field
				self.dict[tag] = Field_desc_01(self,tag,data)

			elif tag == nought_tag(size,2):
				# User application field
				self.dict[tag] = Field_desc_02(self,tag,data)

			elif tag == nought_tag(size,3):
				# Announcer sequence/feature identifier field
				self.dict[tag] = Field_desc_03(self,tag,data)

			elif tag == nought_tag(size,9):
				# Recursive tree LINKS field
				self.dict[tag] = Field_desc_09(self,tag,data)

			elif is_nought_tag(tag):	# Any other 0..<digit>

				print "Warning: tag `%s' is a RESERVED tag - it should not be used"%tag

				# But be friendly and use it anyway

				self.dict[tag] = Field_desc(self,tag,data)

			else:
				# Any normal field

				self.dict[tag] = Field_desc(self,tag,data)

			self.list.append(tag)

		# Since this is a DDR, we should then really check that:
		# a) there is a 0..0 field
		# b) if this is a version 0 file, there is a 0..1 field (it was compulsory)
		# c) that there are no 0..4 through 0..8 fields (they're not used)
		# d) any 0..x tags that are there occur first and in ascending order

	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.record = None


	def __repr__(self):
		return "Data descriptive record"


	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this DDF.

		MERGE is TRUE if want to intertwine labels and formats when possible,
		and FALSE if we never want to.
		"""

		self.leader.write_DFD(dfd)

		dfd.write("\n")

		for tag in self.list:
			self.dict[tag].write_DFD(dfd,merge)


	def show(self,with_leader=TRUE):
		"""Print out the contents of this DDR."""

		print "Data description record (record 0 at offset 0)"

		if with_leader:
			self.leader.show()

		print "    Field tag dictionary:"

		if len(self.list) == 0:
			print "        Empty"
		else:
			for tag in self.list:
				self.dict[tag].show()

