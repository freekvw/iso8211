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

"""Miscellenaous stuff for support within iso8211.py

Separated into this file to make the source files shorter and more manageable.
"""

import sys
import os
import array
import string
import Dates

import format


# ----------------------------------------------------------------------

# Are we debugging?

debugging = 0


# ----------------------------------------------------------------------
# Exceptions
# ==========

class iso8211_error(Exception):
	"ISO 8211 error"
	pass

iso8211_version_error	= "ISO 8211 unknown version"
iso8211_mode_error	= "ISO 8211 file mode error"
iso8211_file_error	= "ISO 8211 file error"
iso8211_dir_error	= "ISO 8211 directory error"

class iso8211_index_error(Exception):
	"ISO 8211 index error"
	pass

iso8211_array_error	= "ISO 8211 fixed array error"
iso8211_syntax_error	= "ISO 8211 syntax error"
iso8211_unsupported	= "ISO 8211 unsupported feature"
iso8211_format_error	= "ISO 8211 format error"
iso8211_internal_error	= "ISO 8211 internal error"
iso8211_unexpected	= "ISO 8211 unexpected value"
iso8211_concat_error	= "ISO 8211 Cartesian label error"
iso8211_fcfmt_error	= "ISO 8211 format/field controls error"
iso8211_noarray_error	= "ISO 8211 no array descriptor"
iso8211_noformat_error	= "ISO 8211 no format controls"

# A tuple of all of the exceptions...

Exceptions = (iso8211_error,iso8211_version_error,iso8211_mode_error,
	      iso8211_file_error,iso8211_dir_error,iso8211_index_error,
	      iso8211_array_error,iso8211_syntax_error,iso8211_unsupported,
	      iso8211_format_error,iso8211_internal_error,iso8211_unexpected,
	      iso8211_concat_error,iso8211_fcfmt_error,iso8211_noarray_error,
	      iso8211_noformat_error)


# ----------------------------------------------------------------------
# Useful things
# =============
# - FT is used to terminate fields
# - UT is the default terminator for variable length subfields
# - CIRCUMFLEX is used to pad out the end of a DDF

FT		= "\x1e"	# field terminator (01/14)
UT		= "\x1f"	# unit terminator  (01/15)
SPACE		= "\x20"	# space            (02/00)
CIRCUMFLEX	= "\x5e"	# circumflex       (05/14)
ESC		= "\x1b"	# escape           (01/11)

# Seek modes

SEEK_START	= 0
SEEK_REL	= 1
SEEK_END	= 2

# I *like* TRUE and FALSE as values to return - so define them!

TRUE	= 1
FALSE	= 0

# The version of ISO 8211 that is being used is indicated by a SPACE
# or a digit one character - this is because the version field contained
# a space in the previous version of ISO 8211! For convenience, let's
# define some shorthand so I don't need to remember that below.

ISO8211_V0 = ' '		# ISO 8211 - 1985
ISO8211_V1 = '1'		# ISO 8211 - 1994

# Data structure codes (for the field controls)

ISO8211_DS_ELEMENTARY	= '0'
ISO8211_DS_VECTOR	= '1'
ISO8211_DS_ARRAY	= '2'
ISO8211_DS_CONCATENATED	= '3'

# Data type codes (for the field controls)

ISO8211_DT_CHARACTER			= '0'
ISO8211_DT_IMPLICIT_POINT		= '1'
ISO8211_DT_EXPLICIT_POINT		= '2'
ISO8211_DT_EXPLICIT_POINT_SCALED	= '3'
ISO8211_DT_CHAR_MODE_BITSTRING		= '4'
ISO8211_DT_BINARY_BITSTRING		= '5'
ISO8211_DT_MIXED			= '6'

# Array descriptor type

ISO8211_ARRAY_NOT		= -1
ISO8211_ARRAY_FIXED		=  0
ISO8211_ARRAY_VARIABLE		=  1
ISO8211_ARRAY_LABELLED		=  2

# Some dictionaries, giving printable names for some of the above

ds_dict = {"0":"elementary, zero dimensions",
	   "1":"vector, one dimension",
	   "2":"array, multiple dimensions",
	   "3":"concatenated data"}

dt_dict = {"0":"character string",
	   "1":"implicit point",
	   "2":"explicit point",
	   "3":"explicit point scaled",
	   "4":"character mode bit string",
	   "5":"bit string including binary forms",
	   "6":"mixed data types"}

bintype_dict = {"1":"unsigned integer",
		"2":"signed integer",
		"3":"fixed point real",
		"4":"floating point real",
		"5":"floating complex"}


# ----------------------------------------------------------------------
# Miscellaneous functions
# =======================

def list(directory):
	"""List all the DDF files in a directory.

	This simply looks for all files ending ".ddf" or ".DDF" in the directory.
	"""

	return filter(file_is_DDF,os.listdir(directory))


def file_is_DDF(filespec):
	"""The filter function for `list'.

	This is used to determine if a file is actually a DDF. We shall be
	fairly simplistic and just look for the characters ".ddf" or ".DDF" at
	the end.  This may not work (for instance) on systems such as VMS
	(where there are also version numbers at the end) or Macintosh (where
	files don't in general have extensions), or if the user is awkward and
	likes capital letters... Maybe the user should be able to supply a
	function to perform this test.  """

	root, ext = os.path.splitext(filespec)

	return (ext == ".ddf" or ext == ".DDF")


# ----------------------------------------------------------------------

# The non-printing characters, and some representations for them

print_dict = {"\x00" : "<NUL>", # "^@"
	      "\x01" : "<SOH>", # "^A"
	      "\x02" : "<STX>", # "^B"
	      "\x03" : "<ETX>", # "^C"
	      "\x04" : "<EOT>", # "^D"
	      "\x05" : "<ENQ>", # "^E"
	      "\x06" : "<ACK>", # "^F"
	      "\x07" : "<BEL>", # "^G"
	      "\x08" : "<BS>",  # "^H"
	      "\x09" : "<TAB>", # "^I"
	      "\x0a" : "<LF>",  # "^J"
	      "\x0b" : "<VT>",  # "^K"
	      "\x0c" : "<FF>",  # "^L"
	      "\x0d" : "<CR>",  # "^M"
	      "\x0e" : "<SO>",  # "^N"
	      "\x0f" : "<SI>",  # "^O"
	      "\x10" : "<DLE>", # "^P"
	      "\x11" : "<DC1>", # "^Q"
	      "\x12" : "<DC2>", # "^R"
	      "\x13" : "<DC3>", # "^S"
	      "\x14" : "<DC4>", # "^T"
	      "\x15" : "<NAK>", # "^U"
	      "\x16" : "<SYN>", # "^V"
	      "\x17" : "<ETB>", # "^W"
	      "\x18" : "<CAN>", # "^X"
	      "\x19" : "<EM>",  # "^Y"
	      "\x1a" : "<SUB>", # "^Z"
	      ESC    : "<ESC>", # "^["
	      "\x1c" : "<FS>",  # "^\"
	      "\x1d" : "<GS>",  # "^]"
	      FT     : "<FT>",	# "<RS>" or "^^" or ";"
	      UT     : "<UT>",	# "<US>" or "^_" or "&"
	      "\x7F" : "<DEL>"}

def printable(str,dict=print_dict):
	"""Replace unprintable characters in the given STR.

	Uses the given DICT to translate characters
	- the keys are the characters (strings) to translate, and the
	  values are what to replace them by.

	The default dictionary contains all the standard non-printing charaters,
	including (specifically):

		FT  : "<FT>"
		UT  : "<UT>"
		ESC : "<ESC>"

	Returns a new string which results from this translation.
	"""

	if str == None or len(str) == 0:
		return str
	else:
		tmp  = str
		keys = dict.keys()

		for key in keys:
			tmp = _repl_str(tmp,key,dict[key])

		return tmp


def iso6429_printable(str):
	"""Replace characters in the given STR according to ISO 6429.

	Note: at the moment this only deals with ESC and CSI.

	Returns a new string which results from this translation.
	"""

	# A dictionary of what we represent specially (in order of priority)

	iso6429_print_dict = {ESC+"[" : "CSI", # "^[["
			      ESC     : "ESC", # "^["
			      "\x9b"  : "CSI"}

	return printable(str,iso6429_print_dict)


def _repl_str(str,fnd,rep):
	"""Replace all occurrences of FND in STR with REP."""

	workstr = str		# a copy of the string to work on
	posn    = 0
	while TRUE:
		posn = string.find(workstr,fnd,posn)
		if posn == -1:
			break
		else:
			workstr = workstr[:posn] + rep + workstr[posn+1:]
			posn    = posn + len(fnd)

	return workstr


def iso2022_charset(str,in_ddr=FALSE):
	"""Given a truncated escape sequence for ISO 2022, return a description.

	If IN_DDR is TRUE then we assume we're looking at DDR RP 17-19"""

	if str == "   ":
		return "ISO/IEC 646 IRV (ASCII)"
	elif str == "-A ":
		return "ISO 8859 part 1 (Latin 1)"
	elif str == "%/@":
		return "ISO/IEC 10646 UCS-2 level 1"
	elif str == "%/A":
		return "ISO/IEC 10646 UCS-4 level 1"

	# What happened to "%/B" ?

	elif str == "%/C":
		return "ISO/IEC 10646 UCS-2 level 2"
	elif str == "%/D":
		return "ISO/IEC 10646 UCS-4 level 2"
	elif str == "%/E":
		return "ISO/IEC 10646 UCS-2 level 3"
	elif str == "%/F":
		return "ISO/IEC 10646 UCS-2 level 3"

	# Things we should really only get in the DDR RP 17-19

	elif in_ddr and str == " ! ":
		return "Fields have ISO 2022 escapes"
	elif in_ddr and str == "HHH":
		return "Fields have ISO/IEC 10646 escapes"

	# Oh dear - we don't know what we've got

	else:
		return "(not known to this software)"


def pretty_hex(str):
	"""Return a `pretty' hex representation of the bytes in STR.

	Each hex pair is separated from its neighbour by a space..."""

	temp   = binary_printable(str)
	retstr = ""
	spaced = FALSE

	while temp != "":
		if spaced:
			retstr = retstr + " "
		retstr = retstr + temp[0:2]
		temp   = temp[2:]
		spaced = TRUE

	return retstr


def binary_printable(str):
	"""Return a "hex" representation of of the bytes in STR."""

	hex_dict = {"\x00":"00", "\x01":"01", "\x02":"02", "\x03":"03",
		    "\x04":"04", "\x05":"05", "\x06":"06", "\x07":"07",
		    "\x08":"08", "\x09":"09", "\x0a":"0a", "\x0b":"0b",
		    "\x0c":"0c", "\x0d":"0d", "\x0e":"0e", "\x0f":"0f",
		    "\x10":"10", "\x11":"11", "\x12":"12", "\x13":"13",
		    "\x14":"14", "\x15":"15", "\x16":"16", "\x17":"17",
		    "\x18":"18", "\x19":"19", "\x1a":"1a", "\x1b":"1b",
		    "\x1c":"1c", "\x1d":"1d", "\x1e":"1e", "\x1f":"1f",
		    "\x20":"20", "\x21":"21", "\x22":"22", "\x23":"23",
		    "\x24":"24", "\x25":"25", "\x26":"26", "\x27":"27",
		    "\x28":"28", "\x29":"29", "\x2a":"2a", "\x2b":"2b",
		    "\x2c":"2c", "\x2d":"2d", "\x2e":"2e", "\x2f":"2f",
		    "\x30":"30", "\x31":"31", "\x32":"32", "\x33":"33",
		    "\x34":"34", "\x35":"35", "\x36":"36", "\x37":"37",
		    "\x38":"38", "\x39":"39", "\x3a":"3a", "\x3b":"3b",
		    "\x3c":"3c", "\x3d":"3d", "\x3e":"3e", "\x3f":"3f",
		    "\x40":"40", "\x41":"41", "\x42":"42", "\x43":"43",
		    "\x44":"44", "\x45":"45", "\x46":"46", "\x47":"47",
		    "\x48":"48", "\x49":"49", "\x4a":"4a", "\x4b":"4b",
		    "\x4c":"4c", "\x4d":"4d", "\x4e":"4e", "\x4f":"4f",
		    "\x50":"50", "\x51":"51", "\x52":"52", "\x53":"53",
		    "\x54":"54", "\x55":"55", "\x56":"56", "\x57":"57",
		    "\x58":"58", "\x59":"59", "\x5a":"5a", "\x5b":"5b",
		    "\x5c":"5c", "\x5d":"5d", "\x5e":"5e", "\x5f":"5f",
		    "\x60":"60", "\x61":"61", "\x62":"62", "\x63":"63",
		    "\x64":"64", "\x65":"65", "\x66":"66", "\x67":"67",
		    "\x68":"68", "\x69":"69", "\x6a":"6a", "\x6b":"6b",
		    "\x6c":"6c", "\x6d":"6d", "\x6e":"6e", "\x6f":"6f",
		    "\x70":"70", "\x71":"71", "\x72":"72", "\x73":"73",
		    "\x74":"74", "\x75":"75", "\x76":"76", "\x77":"77",
		    "\x78":"78", "\x79":"79", "\x7a":"7a", "\x7b":"7b",
		    "\x7c":"7c", "\x7d":"7d", "\x7e":"7e", "\x7f":"7f",
		    "\x80":"80", "\x81":"81", "\x82":"82", "\x83":"83",
		    "\x84":"84", "\x85":"85", "\x86":"86", "\x87":"87",
		    "\x88":"88", "\x89":"89", "\x8a":"8a", "\x8b":"8b",
		    "\x8c":"8c", "\x8d":"8d", "\x8e":"8e", "\x8f":"8f",
		    "\x90":"90", "\x91":"91", "\x92":"92", "\x93":"93",
		    "\x94":"94", "\x95":"95", "\x96":"96", "\x97":"97",
		    "\x98":"98", "\x99":"99", "\x9a":"9a", "\x9b":"9b",
		    "\x9c":"9c", "\x9d":"9d", "\x9e":"9e", "\x9f":"9f",
		    "\xa0":"a0", "\xa1":"a1", "\xa2":"a2", "\xa3":"a3",
		    "\xa4":"a4", "\xa5":"a5", "\xa6":"a6", "\xa7":"a7",
		    "\xa8":"a8", "\xa9":"a9", "\xaa":"aa", "\xab":"ab",
		    "\xac":"ac", "\xad":"ad", "\xae":"ae", "\xaf":"af",
		    "\xb0":"b0", "\xb1":"b1", "\xb2":"b2", "\xb3":"b3",
		    "\xb4":"b4", "\xb5":"b5", "\xb6":"b6", "\xb7":"b7",
		    "\xb8":"b8", "\xb9":"b9", "\xba":"ba", "\xbb":"bb",
		    "\xbc":"bc", "\xbd":"bd", "\xbe":"be", "\xbf":"bf",
		    "\xc0":"c0", "\xc1":"c1", "\xc2":"c2", "\xc3":"c3",
		    "\xc4":"c4", "\xc5":"c5", "\xc6":"c6", "\xc7":"c7",
		    "\xc8":"c8", "\xc9":"c9", "\xca":"ca", "\xcb":"cb",
		    "\xcc":"cc", "\xcd":"cd", "\xce":"ce", "\xcf":"cf",
		    "\xd0":"d0", "\xd1":"d1", "\xd2":"d2", "\xd3":"d3",
		    "\xd4":"d4", "\xd5":"d5", "\xd6":"d6", "\xd7":"d7",
		    "\xd8":"d8", "\xd9":"d9", "\xda":"da", "\xdb":"db",
		    "\xdc":"dc", "\xdd":"dd", "\xde":"de", "\xdf":"df",
		    "\xe0":"e0", "\xe1":"e1", "\xe2":"e2", "\xe3":"e3",
		    "\xe4":"e4", "\xe5":"e5", "\xe6":"e6", "\xe7":"e7",
		    "\xe8":"e8", "\xe9":"e9", "\xea":"ea", "\xeb":"eb",
		    "\xec":"ec", "\xed":"ed", "\xee":"ee", "\xef":"ef",
		    "\xf0":"f0", "\xf1":"f1", "\xf2":"f2", "\xf3":"f3",
		    "\xf4":"f4", "\xf5":"f5", "\xf6":"f6", "\xf7":"f7",
		    "\xf8":"f8", "\xf9":"f9", "\xfa":"fa", "\xfb":"fb",
		    "\xfc":"fc", "\xfd":"fd", "\xfe":"fe", "\xff":"ff"}

	new_str = ""

	for ch in str:
		new_str = new_str + hex_dict[ch]

	return new_str

# ----------------------------------------------------------------------
def dump(filename):
	"""Dump out a DDF in a very simple (and presumably quick) manner.

	This is a simple alternative for someone who just wants a quick
	dump of an ISO 8211 file for some purpose, without wanting to
	`decode' it properly. It's the sort of thing I might do as a first
	stab at deciding exactly why a file is not actually a valid ISO 8211
	DDF.
	"""

	# Simply put, open the given file and ask it to print itself out

	ddf = DDF(filename,"r")
	ddf.show()

# ----------------------------------------------------------------------
def read_to_char_or_end(octets,char):
	"""Read a string terminated by either CHAR or end-of-string.

	That is, if there is a CHAR, end at that, otherwise end at end-of-string.
	"""

	if len(octets) == 0:
		return octets

	posn = string.find(octets,char,0)

	if posn == -1:				# not ended by CHAR
		posn = len(octets)		# so use the whole string

	return octets[:posn]


def read_to_UT_or_end(octets):
	"""Read a string terminated by either UT or end-of-string.

	That is, if there is a UT, end at that, otherwise end at end-of-string.
	"""

	return read_to_char_or_end(octets,UT)



def read_to_UT_or_FT(octets):
	"""Read a string terminated by either UT or FT.

	Note that it looks for a UT first, and then (if not found) for an FT.
	"""

	if len(octets) == 0:
		return octets

	posn = string.find(octets,UT,0)

	if posn == -1:				# not ended by UT
		posn = string.find(octets,FT,0)		# what about FT?
		if posn == -1:				# not ended by FT either...
			raise iso8211_syntax_error,("string not terminated by UT or FT",
						    printable(octets))

	return octets[:posn]

def read_to_FT(octets):
	"""Read a string terminated by FT"""

	if len(octets) == 0:
		return octets

	posn = string.find(octets,FT,0)
	if posn == -1:				# not ended by FT
		raise iso8211_syntax_error,("string not terminated by FT",
					    printable(octets))

	return octets[:posn]

def read_to_UT(octets):
	"""Read a string terminated by UT"""

	if len(octets) == 0:
		return octets

	posn = string.find(octets,UT,0)
	if posn == -1:				# not ended by UT
		raise iso8211_syntax_error,("string not terminated by UT",
					    printable(octets))

	return octets[:posn]


# ----------------------------------------------------------------------
def nought_tag(size,which):
	"""Return a 0..WHICH tag, of length SIZE."""

	if type(which) != type("1"):
		which = `which`

	return (size-1)*"0" + which

def is_nought_tag(tag):
	"""Check if this is a 0..x tag."""

	start = tag[:-1]
	end   = tag[-1]

	# The definition is any of 0..0 throught 0..9
	# - so that's a sequence of zeroes followed by a digit

	if start == len(start)*"0" and end in string.digits:
		return TRUE
	else:
		return FALSE


# ----------------------------------------------------------------------
def read_item(data,control):
	"""Read an item from the start of DATA, using the format CONTROL.

	Returns a tuple containing the item read (as a string) and what is
	left of DATA.

	DATA should *not* include the final FT (that should have been stripped off).

	Raises IndexError if an attempt is made to read data from a zero
	length data string.
	"""

	#print "Read_item: control %s, form %s, size %s"%(control.control,control.form,control.size)
	#print "Read_item: control =  %s"%(control)
	#print "              data = '%s' (%s)"%(printable(data),binary_printable(data))

	# Check for zero length data!

	if data == "":
		raise IndexError,"End of data"

	# Now parse something sensible

	if control.form == "D":

		item = read_to_char_or_end(data,control.size)
		data = data[len(item)+1:]
			
	elif control.form == "W":

		if control.control == "B":

			# We have a B(size) item

			item,data = _read_WB_item(data,control.size)

		else:
			# We have a (normal) format

			item = data[:control.size]
			data = data[control.size:]
			
	elif control.form == "B":

		# We have a Btw or btw item

		item,data = _read_Btw_item(data,control)

	else:
		if control.control == "B":

			# We have a B item

			item,data = _read_B_item(data)

		else:
			# We have a "read until UT (or end of data)" item

			item = read_to_UT_or_end(data)
			data = data[len(item)+1:]

	#print "       return item = '%s' (%s)"%(printable(item),binary_printable(item))
	#print "       return data = '%s' (%s)"%(printable(data),binary_printable(data))
	#print

	return (item,data)


def _read_Btw_item(data,control):
	"""Read a Btw item from the start of DATA.

	Returns a tuple containing the item read (as a string) and what is
	left of DATA.

	The order of octets is:

		"B"	MSOF (most  significant octet first)
		"b"	LSOF (least significant octet first)

	(as discussed in 6.4.3.3 h))

	In the case of a "b" format, we reorder the octets into MSOF
	"""

	# We have a Btw or btw item

	# If it is complex, it is double the size

	if control.control[1] == "5":
		size = control.size * 2
	else:
		size = control.size

	# First off, we can extract the relevant number of octets

	item = data[:size]
	data = data[size:]

	# And now interpret them

	if control.control[0] == "b":
		# LSOF form - reverse it

		thing = ""
		for count in range(control.size-1,-1,-1):
			thing = thing + item[count]

		item = thing

	# So we've now got the MSOF form, regardless of the format

	# As of yet, we don't do anything with it...

	return (item,data)



def _read_WB_item(data,size):
	"""Read a B(SIZE) item from the start of DATA.

	Returns a tuple containing the item read (as a string) and what is
	left of DATA.

	The order of octets is defined in 6.4.3.3 f) - or rather, it is not
	discussed there. I assume that this means that MSOF (most significant
	octet first) is to be used (cf the "C" format).
	"""

	# The size is from the format - a "B(size)" format
	# So the "size" is in bits. At the moment, we don't have proper
	# support, we can only handle octet multiples (so a width of 7
	# will cause us to give up...)

	if size % 8 != 0:
		raise ValueError,\
		      "Unable to cope with bit strings of width %d (not a multiple of 8)"%size
	else:
		size = size / 8

	item = data[:size]
	data = data[size:]

	return (item,data)



def _read_B_item(data):
	"""Read a B item from the start of DATA.

	Returns a tuple containing the item read (as a string) and what is
	left of DATA.

	The order of octets is defined in 6.4.3.3 g) NOTE 23 to be MSOF.
	"""

	# We have a variable width bit string - a "B" format
	# Character 0 gives us the length of the size

	#print "Format is B"
	#print "data is  ",data

	count = int(data[0])
	data  = data[1:]

	#print "count is ",count
	#print "data is  ",data

	# The next "count" characters give us the size in bits

	size = int(data[:count])
	data = data[count:]

	#print "size is  ",size
	#print "data is  ",data

	# But we actually read up to the end of the final octet

	count = (size+7)/8

	#print "count is ",count

	item = data[:count]
	data = data[count:]

	#print "item is  ",item
	#print "data is  ",data

	return (item,data)



def parse_item_with_control(control,item):
	"""Given an ITEM (a string), parse it according to CONTROL.

	CONTROL is a Control object, and this is actually a jacket
	for a call of:

		parse_item(CONTROL.control,ITEM)

	Returns the relevant value.
	"""

	return parse_item(control.control,item)


def parse_item(datatype,item):
	"""Given an ITEM (a string), parse it according to the DATATYPE.

	DATATYPE is a control (as in the Control class) - that is, something like
	"I", "R", "b1", etc., that determines the datatype of the item.

	Returns the relevant value.
	Raises ValueError if the datatype is "X", unrecognised, or cannot
	be converted.
	"""

	if datatype == "A":

		value = item

	elif datatype == "I":

		try:
			value = int(item)
		except ValueError,what:
			raise ValueError,("%s (datatype I, value `%s')"%(what,item))

	elif datatype == "R":

		try:
			value = float(item)
		except ValueError,what:
			raise ValueError,("%s (datatype R, value `%s')"%(what,item))

	elif datatype == "S":

		try:
			value = float(item)
		except ValueError,what:
			raise ValueError,("%s (datatype S, value `%s')"%(what,item))

	elif datatype == "C":

		#value = "%s (%d)"%(item,_char_bitstring(item))
		value = _char_bitstring(item)

	elif datatype == "X":

		raise ValueError,"`X' is not a datatype, in parse_item()"

	elif datatype[0] == "B" or datatype[0] == "b":

		value = parse_binary_item(datatype,item)

	else:
		raise ValueError,"Unknown datatype `%s' to parse_item()"%datatype

	return value


def parse_binary_item(datatype,item):
	"""Given an ITEM (a string), parse it according to the DATATYPE.

	DATATYPE is a binary control - one of "B", "B<n>" or "b<n>",
	where <n> is 1..5

	Returns the relevant value.
	Raises ValueError if the datatype is "b" (by itself), or we have serious
	problems
	"""

	# Work out what datatype we have, exactly

	if len(datatype) == 1:
		if datatype == "B":
			# We have a variable length bit string [6.4.3.3 g)]
			# Force it to be an integer
			type = "1"
		else:
			raise ValueError,\
			      "Datatype `b' without a qualifier is not allowed,"+\
			      " in parse_item()"
	else:
		type = datatype[1]

	# Which byte ordering we have is determined by the datatype letter
	#FIXME changed
	if datatype[0] == "B":
		msof = FALSE
	else:
		msof = TRUE

	# Work out something that we can guarantee to be able to print

	print_value = binary_printable(item)

	# And have a go at translating the bits...

	if type == "1":		# Integer, unsigned

		value = "U:0x%s (%d)"%(print_value,_unsigned_int(msof,item))

	elif type == "2":	# Integer, signed

		value = "I:0x%s (%d)"%(print_value,_signed_int(msof,item))

	elif type == "3":	# Real, fixed point

		# Dissect the whole and fractional parts out
		# - each occupies half of the length of the item

		length = len(item)
		intstr = item[:length/2]
		decstr = item[length/2:]
		intpart =   _signed_int(msof,intstr)
		decpart = _unsigned_int(msof,decstr)

		value = "R:0x%s/0x%s (%d/%d=%f)"%(binary_printable(intstr),
						  binary_printable(decstr),
						  intpart,decpart,float(intpart)/decpart)

	elif type == "4":	# Real, floating

		# This is as defined in IEC 559, so at the moment we
		# can't hope to do much with it...

		value = "F:0x%s"%(print_value)

	elif type == "5":	# Complex, floating

		# This is a pair of floating point numbers, each
		# of size "w"

		length  = len(item)
		realstr = item[:length/2]
		imagstr = item[length/2:]

		value = "C:0x%s,0x%s"%(binary_printable(realstr),binary_printable(imagstr))

	return value


def _signed_int(msof,data):
	"""Interpret the octets of DATA as a signed integer in MSOF/LSOF order.

	If MSOF is TRUE, we have most significant octet first, otherwise
	we have least significant octet first.

	We can't just use "atoi" because we don't know the byte order of
	the machine we are running on.

	NOTE: THIS IS NOT PORTABLE, AS IT ASSUMES BYTE ORDER.
	"""

	result = _unsigned_int(msof,data)

	negative = FALSE

	if msof:
		#print len(data), ord(data[0])
		if (ord(data[0]) & 0x80):
			negative = TRUE		# is that right?
	else:
		if (ord(data[-1]) & 0x80):
			negative = TRUE		# is that right?

	if negative:
		result = result - 2**32		# is that right?

	return result


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


def _char_bitstring(data):
	"""Interpret the string DATA as a character mode bitstring.

	That is, each character is either "0" or "1".
	"""

	result = 0

	for char in data:
		if char == "1":
			result = result * 2 + 1
		elif char == "0":
			result = result * 2
		else:
			raise iso8211_error,\
			      "value `%s' is not allowed in a character mode bit string"%char

	return result


def read_and_parse_item(data,control):
	"""Read an item from the start of DATA, using the format CONTROL, and parse it.

	Returns a tuple containing the item read (as an item of the appropriate datatype)
	and what is left of DATA.

	DATA should *not* include the final FT (that should have been stripped off).

	Raises IndexError if an attempt is made to read data from a zero
	length data string.

	This is an `obvious' use of "read_item" and "parse_item_with_control" together.
	"""

	item,data = read_item(data,control)

	return parse_item_with_control(control,item),data


# ----------------------------------------------------------------------
# Friendlier error handling

def explain():
	"""Explain an iso8211 exception.

	This function is provide for use when an iso8211 exception is expected.
	It does two things:

	1) it explains the exception in more detail than one would get by
	   just catching the exception and printing out its name and value
	2) it handles those nasty details of actually finding out which
	   exception it is and looking up its details

	For instance:

		try:
			<something iso8211-ish>
		except iso8211.Exceptions:
			iso8211.explain()

	If the function is called for an exception that is NOT an iso8211
	exception, it will just report it using:

		print "%s: %s"%(sys.exc_type,sys.exc_value)

	(This is essentially just a jacket for the "explain_by_hand" function,
	 but it is provided as a simpler interface)
	"""

	# Find out what happened

	exception = sys.exc_type
	details   = sys.exc_value

	# And just let the internal routine figure out what should be said

	explain_by_hand(exception,details)



def explain_by_hand(exception,tuple):
	"""Explain the given EXCEPTION, using the values in the TUPLE.

	Normally, one would catch a random exception and do something like:

		print "%s: %s"%(sys.exc_type,sys.exc_value)

	to print out its name and value(s). This function can be used to
	`translate' an iso8211 module exception into something a bit
	more helpful, by putting a proper explanation around the exception.

	For instance:

		try:
			<something iso8211-ish>
		except iso8211.Exceptions:
			iso8211.explain(sys.exc_type,sys.exc_value)

	The first, short, method may be more appropriate in production systems,
	where one expects (!) things to work, but this routine may be more
	useful in diagnostic situations, or where the user is less au fait with
	ISO/IEC 8211 itself.

	Exception		Contents of tuple
	---------		-----------------
	iso8211_error		(descriptive_string)
	iso8211_version		(version_number_string)
	iso8211_mode_error	(mode_char)
	iso8211_file_error	(descriptive_string)
	iso8211_dir_error	(EXC_DIR_SIZE,entry_size,dir_length,string_left)
			     or	(EXC_DIR_NOTFT,last_octet)
			     or	(EXC_DIR_FLDFT,field_tag,octets)
			     or	(EXC_DIR_FMTLEN,field_tag,format_controls,octets)
			     or (EXC_DIR_TAGPAIRFT,field_tag,octets)
			     or (EXC_DIR_TAGPAIR,field_tag,tag_size,octets)
	iso8211_index_error	(index,string_describing_index_and_limits)
	iso8211_array_error	(field_tag,count,length,octets)
	iso8211_syntax_error	(descriptive_string,incorrect_data)
	iso8211_unsupported	(descriptive_string)
	iso8211_unexpected	(what,where,tag,expected)
	iso8211_concat_error	(tag,which)
	iso8211_format_error	(tag,stuff for __.format.explain())
	iso8211_fcfmt_error	(tag,field controls,expected,format controls)
	iso8211_noarray_error	(tag,data)
	iso8211_noformat_error	(tag,data)

	anything else		(whatever it likes)
	"""

	# First of all, give the exception name
	# - note that we don't automatically write a newline

	print "%s: "%(exception),

	# Then explain in detail what went wrong
	# Basically, we want a big switch statement...

	if exception == iso8211_error:

		# A general error - so we expect just a descriptive string

		print "%s"%tuple

	elif exception == iso8211_version_error:

		# We expect the erroneous version number string

		print str_version%tuple

	elif exception == iso8211_mode_error:

		# We expect a string, containing the unexpected mode
		# and we pass that to the explantory text

		print str_mode_error%tuple

	elif exception == iso8211_file_error:

		# We expect a descriptive string

		print "%s"%tuple

	elif exception == iso8211_dir_error:

		# There are various different directory errors
		# - the first item in the tuple should distinguish them

		which = tuple[0]
		rest  = tuple[1:]

		if   which == EXC_DIR_SIZE:

			# We have some work to do for this explanation

			entry_size = rest[0]
			dir_length = rest[1]
			string     = rest[2]

			remainder = dir_length%entry_size

			print str_dir_size%(entry_size,entry_size,entry_size,
					    dir_length,remainder,
					    printable(string))

		elif which == EXC_DIR_NOTFT:

			print str_dir_notft%printable(rest[0])

		elif which == EXC_DIR_FLDFT:

			tag    = rest[0]
			octets = rest[1]

			print str_dir_fldft%(tag,printable(octets))

		elif which == EXC_DIR_FMTLEN:

			tag      = rest[0]
			controls = rest[1]
			octets   = rest[2]

			print str_dir_fmtlen%(tag,
					      printable(controls),
					      printable(octets))

		elif which == EXC_DIR_TAGPAIRFT:

			tag      = rest[0]
			octets   = rest[1]

			print str_dir_tagpairft%(tag,
						 printable(octets))

		elif which == EXC_DIR_TAGPAIR:

			tag      = rest[0]
			size	 = rest[1]
			octets   = rest[2]

			print str_dir_tagpair%(tag,
					       size,
					       len(octets),
					       printable(octets))

		else:
			print "%s"%rest

	elif exception == iso8211_array_error:

		# We expect a field tag, the count we read, the number
		# of dimension values we found, and the octets we read

		print str_array_error%tuple

	elif exception == iso8211_index_error:

		# We expect a string and an integer
		# - the integer is the index we were given, and the string is
		#   something along the lines of "field indices must be 0 or more"

		print "Unexpected index %d (%s)"%tuple

	elif exception == iso8211_syntax_error:

		# We expect a descriptive string, and the erroneous data

		print tuple[0]
		print 'Data was: "%s"'%printable(tuple[1])

	elif exception == iso8211_unsupported:

		# Just describe what is unsupported
		# - do it this way in case we were given a tuple
		#   of more than one part

		print "%s"%tuple

	elif exception == iso8211_format_error:

		# Split the tuple into two parts:

		tag  = tuple[0]
		rest = tuple[1:]

		# Explain the first part ourselves

		print "Error parsing format controls for field `%s'"%tag

		# And hand the detailed part down to the "format" module

		__.format.explain(rest)

	elif exception == iso8211_unexpected:

		#		   what   where        tag            expected
		print "Unexpected `%s' in %s in field `%s' - expected %s"%tuple

	elif exception == iso8211_concat_error:

		print "Only the last Cartesian label in an array descriptor can be a `table'\n" \
		      "In field `%s', Cartesian label %d (0 = first) is a table\n" \
		      "The full array descriptor is: %s"%tuple

	elif exception == iso8211_noarray_error:

		print "Concatenated data requires an array descriptor\n" \
		      "In field `%s', the data structure code is 3 (concatenated data),\n" \
		      "but the array descriptor is null (zero length)\n" \
		      "Field description is: `%s'"%(tuple[0],printable(tuple[1]))

	elif exception == iso8211_noformat_error:

		print "Mixed data requires format controls\n" \
		      "In field `%s', the data type code is 6 (mixed data types),\n" \
		      "but the format controls are null (zero length)\n" \
		      "Field description is: `%s'"%(tuple[0],printable(tuple[1]))

	elif exception == iso8211_fcfmt_error:

		print "Incompatible format control\n" \
		      "In field `%s', the field controls `%s' indicate format `%s'\n" \
		      "but the actual format controls are `%s'"%tuple

	else:

		# Otherwise, just print out the tuple

		print tuple


# ----------------------------------------------------------------------
# Here are some big strings we use in our `explain' routine, and also
# some constants we use to decide which string is wanted when the same
# exception is raised

# Tuple should be (opening_mode)
str_mode_error = """Invalid opening mode "%s".
The recognised opening modes are:
	"r"	open the DDF for reading
	"w"	open the DDF for writing (not yet implemented)
"""

# Tuple should be (version_number_string)
str_version_error = """The version `number' in the leader is "%s".
This software knows about the following versions of ISO 8211:
	ISO 8211 - 1985   (version 0) which has a " " (space)
	ISO/IEC 8211:1994 (version 1) which has a "1"
and since this is neither, it cannot continue.
"""

# Tuple should be (EXC_DIR_SIZE,entry_size,dir_length)
EXC_DIR_SIZE = "Directory size is not (N*entry_size)+1"
str_dir_size = """The directory size is not correct.

The directory is made up of individual entries, each of
size %d, with an FT at the end. That is, the directory
should be (N*%d)+1 octets long, where "N" is the number
of entries in the directory.

However, the entry size is %d and the directory size is
%d, which leaves %d characters ("%s")
at the end of the directory, instead a single FT.
"""

# Tuple should be (EXC_DIR_NOTFT,last_octet)
EXC_DIR_NOTFT = "Last octet of directory not FT"
str_dir_notft = """ISO 8211 directory error [notft]:

The last octet of the directory is "%s", not FT.
"""

# Tuple should be (EXC_DIR_FLDFT,field_tag,data)
EXC_DIR_FLDFT = "Format controls don't end with FT"
str_dir_fldft = """ISO 8211 directory error [fldft]:

The format controls for field '%s' are not terminated by FT.

The relevant data is: "%s"
"""

# Tuple should be (EXC_DIR_FMTLEN,field_tag,format_controls,octets)
EXC_DIR_FMTLEN = "Format controls don't fill field description"
str_dir_fmtlen = """ISO 8211 directory error [fmtlen]:

The format controls for field '%s' are not long enough to
fill the field description.

The format controls are: "%s"
The data as a whole is:  "%s"
"""

# Tuple should be (EXC_DIR_TAGPAIRFT,field_tag,octets)
EXC_DIR_TAGPAIRFT = "Field tag pairs don't end with FT"
str_dir_tagpairft = """ISO 8211 directory error [tagpairft]

The field tag pair list in field `%s' does not end with an FT.

The octets read are: "%s"
"""

# Tuple should be (EXC_DIR_TAGPAIR,field_tag,tag_size,octets)
EXC_DIR_TAGPAIR = "Field tag pair list should be even number of tags"
str_dir_tagpair = """ISO 8211 directory error [tagpair]

The field tag pair list in field `%s' is not an even number of tags.
The tag size is %d, but the field tag pair list is %d octets long.

The octets read are: "%s"
"""

str_array_error = """Invalid fixed array dimensions for field "%s".
The dimension count is %d, but there are %d dimension values given
(the actual octets are "%s").
"""
