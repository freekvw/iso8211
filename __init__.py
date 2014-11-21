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

"""iso8211.__init__.py - header for iso8211 package

This package provides support for (initially, just reading) ISO 8211 files

Initial code: TJ Ibbs, 17 Feb 1994

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


See module variables "Changes" and "Version" for the obvious things...

This code has been written by:

	Tony J Ibbs

	Department of Geography & Topographic Science,
	University of Glasgow,
	GLASGOW  G12 8QQ
	Scotland

	Tel: (+44)141-330-6649
	Fax: (+44)141-330-4894

	Email:	tony@lsl.co.uk
	   or:	T.Ibbs@geog.gla.ac.uk

	Url: http://www.geog.gla.ac.uk/staff/res/tibbs/

Some (much) of it has been done in my own time, but some of it has been paid
for by my funders:

	Laser-Scan Ltd
	Cambridge Science Park
	Milton Road
	Cambridge CB4 4FY
	UK

	Tel: (+44)1223-420414
	Url: http://www.lsl.co.uk

This means that the copyright for this probably belongs to them. However, I
regard this as being under the same copyright as Python itself (unless they
tell me otherwise), so please bear with that.


Regardless, ANY bug reports, awkward features, general naughtiness or simply
things you would like it to do will be happily received, although since this is
only a background task, they may not get acted on fast.


See the file INSTALL for details of how to install this package.
"""

Changes = """Modifications:

1994/02/17:	Development begun, with version 0.1
		(this work being done in my spare time!)
1994/03/04:	FROZEN: Version 0.1a
		This version read directly from the DFD, rather than using
		strings to hold the directory, etc. This approach was abandoned
		for coding simplicity, even though it is likely to be wanted at
		a later stage again.
1994/03/05:	FROZEN: Version 0.2
1994/05/03:	FROZEN: Version 0.2a

1996/03/24:	Version 0.2c (what happened to 0.2b?)
		This work is now being done partially in LSL time, to support
		other work with ISO 8211 data.

		Make the DDR also keep a *list* of tag names, and use this
		when "show"ing the fields in the DDR, so that they are shown
		in the order they occur in the DDR.
		Cope with an empty array descriptor (check if it is None
		before trying to "show" it).

1996/03/28:	Add the "explain" functionality, and change the exceptions
		raised to take account of it.
		Add support for "R" records.

1996/03/29:	Finish making support for "R" records work.
		Change the DDF class to initialise with no arguments,
		and add an "open" method to open a DDF (this seems neater).
		Tidy up the printing for field controls - add some dictionaries
		to help interpret the values, rather than "hard coding" them.
		Start work on deciphering format controls.

1996/04/16:	Include (import) the new module format.py, and use it to parse
		and show format controls.

1996/04/18:	Add support for writing out DFD files.
		Add a "Version" string for the module.

1996/04/22:	Improve the DFD writing:
		If there is no array descriptor, construct one from the
		data structure.
		If there are no format controls, construct some from the data type.

		Make the "show" methods for DDR parts simpler, now we have
		DFD writing available (to give a quick scan with show, and
		leave detail to the DFD)

1996/04/23:	Sort out the `merging' of labels and format statements in the DFD.
		Add checking of various things from the field controls, etc.
		Make an Array_descriptor contain a list of Simple_array_descriptors
		(unless it is a variable array).

1996/04/24:	Carry on with checking and `merging'
		Compare a field's data structure and data type against any
		array descriptor or format controls, and make sure they match.
		Start coping with the 0..x tag separately

1996/04/25:	Rename format.py to iso8211_format.py
		Split this (by now huge) source file into smaller files, to speed
		up editing.
		Finish coding the 0..x tags.
		Generate PARENT instructions from the 0..0 binary tree (at level 3
		only, of course).
		Add more checking of various things, and also make "common" errors
		(as determined by testing SDTS data!) give warnings and continue rather
		than raising exceptions.

1996/04/26:	Detect REPEAT TO END and write it out as such to the DFD.
		Change iso8211_format.py to use objects for format items, instead
		of tuples - this allows one to go back and *change* data in format
		items, such as noting they are "repeat to end". It is also rather
		better safer feeling than relying on "knowing" the contents of a
		tuple will (happen to) be such-and-such. (It's probably also slower.
		Ah well.)

1996/05/01:	Provide functionality to split a field into subfields.
		Make a crude attempt to deal with binary forms in that splitting
		- it doesn't cope with non-divisible-by-8 sizes of binary form, and
		it doesn't turn the binary data into floating, integer, or whatever
		(it returns a string containing the octets instead), and it doesn't
		necessarily get the octet order correct.

1996/05/15:	Version 0.3
		Fix some bugs found reading level 1 data.
		Fix writing out of DFD for unlabelled fields.

1996/05/16:	Fix writing out data for unlabelled fields, and for variable array data.
		Improve the support for binary forms:

			"B(size)" is read if "size" is a multiple of 8. An exception is
				  raised (and converted to a warning) otherwise.
				  MSOF order is assumed.

			"B"       is read. No account is taken of zero padding (so this will
				  also only really work for sizes that are multiples of 8).

			"Btw" and "btw" are read. The value is converted to MSOF.

		The values read are only partially parsed. The following are reported
		by "show()" (where "<XXX>" is a hexadecimal representation, "<IIII>" is
		an integer (Python doesn't provide unsigned integers) and "<RRRR>" is
		a real number):

			for "B(size)", "B", "B51w" and "b51w" (`unsigned integer'):

				"U:0x<XXXX> (<IIII>)"

			for "B52w" and "b52w" (`signed' integer):

				"I:0x<XXXX> (<IIII>)"

			for "B53w" and "b53w" (Fixed point real):

				"R:0x<XX>/0x<XX> (<II>/<II>=<RRRR>)"

			for "B54w" and "b54w" (Floating point real):

				"F:0x<XXXX>"

			for "B55w" and "b55w" (Complex):

				"C:0x<XXXX>,0x<XXXX>"

		Note that these are largely untested (with the exception of some testing
		on "B(size)" and "B") due to lack of data to test them on.
		Note that "C" style bit strings are always left as strings.

1996/08/28	Change version to 0.4
		Minor bug fix to checking of n500 field controls against explicit
		format controls (thanks Jamie for providing the data).
		Provide elaboration of the meaning of truncated escape sequences,
		both as hex characters, and as a description for the more common
		values (well, as used in S-57). These are written to the DFD as
		comments, as well as shown in the "show()" data.
		When reporting a record's index, it may be None, so use \%s, not \%d
		(so that we get None, rather than an exception).

		In iso8211:
		Introduce "Changes" and "Version" strings.
		Add the "show field <tag> [in record <index>]" command.
		Change "show at" to be "show record at", and tidy up how commands work.


1996/08/28	Translate character mode bitstrings (since this is fairly simple, and
		appears to work, just return the value as an integer, rather than as
		a string containing the bit string and the integer).
		Make binary form translation take account of MSOF and LSOF, and have a
		stab at a more correct implementation (issues of machine architecture
		are still to be thought about, though). Support signed binary integers.

1996/09/03	This directory of files is now a package. Use:

			import ni; ni.ni()
			import iso8211.iso8211

		and so on, to use it. The "iso8211" command is in the package. All that
		is needed to use the lot is:
		a) place this directory on the PYTHONPATH - for instance, if
		   ~/lib/python exists, and it on the PYTHONPATH, then it would be
		   sufficient to place this directory within ~/lib/python
		b) make the "iso8211" command available - either link to it, or place
		   this directory on the PATH
		Being a package means that the source files can now have shorter names
		(no more need to prefix them with "iso8211_", which is nicer.
		Open a DDF in binary mode (i.e., "rb", not just "r").

		In iso8211:
		Fix bug in "cd", "list", "dir" - they need to take account of our
		notion of current directory.
		Add "Local Variables" to end for [X]Emacs, to make this file be in
		Python mode when editing it with same.
		Add "pwd" command (horrible name, but Unix compliant).
		Make "cd" and "file" more robust (not likely to raise an exception!).
		Use "ni" so that all the iso8211 stuff is in one package - this means
		that it is now possible to place the package directory somewhere, and
		all that is needed to use this package and file is to place it somewhere
		that is on the PYTHONPATH. This also allows shorter names for the
		various sources files - no need to prefix "iso8211_" to them all.


1996/09/05	Add some initial, clumsy support for DEFINING formats to format.py

		In iso8211:
		Add the "read dfd" command, to make debugging the DFD reading code easier.
		(It isn't USEFUL yet, though, except possibly for testing the format of a
		DFD file - assuming my code is right!)


1996/09/13	Create __init__.py, and move the changes, todo list and version string
		to it, as well as the main __doc__ string.

		Add a command "package" to iso8211, which can be used to get at the version,
		etc., from the command line.

1996/09/30	Add imports of the `more important' classes and functions to __init__, so
		that they may be used directly from the package - e.g.:

			import ni; ni.ni()
			import iso8211
			ddf = iso8211.DDF()

		(instead of "ddf = iso8211.iso8211.DDF()")
		Create basic README and INSTALL texts for the package.
"""

Version = "0.4 1996/09/30"

Todo = """To do (the order is not fixed for these):
	- Add more comments, particularly with reference back into the standard,
	  explaining why things are done as they are.
	- Add specific documentation about exactly what is supported.
	- Provide documentation (!).
	- Make the separation into separate source files neater and more rational.
	- Check that a version 1 file only contains version 1 type data (at the
	  moment it may contain version 2 data).
	- Separate out REPEAT BIT FIELD in the DFD.
	- Check that format controls with bit fields are legitimate (linked to the
	  previous item).
	- Cope with extended character sets (and clause 7 in general).
	- Cope with binary forms fully and properly.
	- Add a "use_ddr()" method to DDF, such that it is possible to do:
		ddf1 = DDF()
		ddf1.open("thing.ddf","r")
		ddf1.write_DFD("broken.dfd")

		<edit the broken DFD, and create working.dfd>

		ddf2 = DDF()
		ddf2.read_DFD("working.dfd")
		ddr = ddf2.ddr
		ddf1.use_ddr(ddr)
	  This is intended to cope with cases where the DDR and data do not agree
	  - the user can extract the broken DDR into a DFD, edit it to match the
	  data, create a new DDR, and then insist on using *that* to read the data
	  with. I think I prefer the use of a function to just doing "ddf1.ddr = ddr",
	  but I'll need to think about it...
	  (Is this necessary? Well, yes, in the past something like this would have
	  been very useful, and I can imagine it being so again. It can be quite easy
	  to get a DDR that doesn't match the DRs, especially if they're created by
	  separate pieces of software.)
	- Rationalise the exceptions (there shouldn't REALLY be so many!).
	  Maybe use an exception object instead of a string.
	- Add support for reading and parsing DFD files, to create an appropriate DDR.
	- Add support for creating and writing DDFs.
"""

# Make the above more easily available - if you do:
#
#	import ni
#	ni.ni()		# (currently needed (in Python 1.3) to start "ni" up)
#	import iso8211
#	print  iso8211.Intro
#
# then you should get the sensible result...

Intro   = __doc__
#Changes = Changes
#Version = Version
#Todo    = Todo

# Similarly with the more common classes and methods...

from iso8211 import DDF
from iso8211 import Record
from iso8211 import Exceptions
from iso8211 import explain_by_hand
from iso8211 import debugging
from iso8211 import list


#__.DDF             = DDF		# Our main class
#__.Record          = Record		# Our main subsidiary class
#__.Exceptions      = Exceptions		# The tuple of our exceptions
#__.explain_by_hand = explain_by_hand	# The function that explains exceptions
#__.debugging       = debugging		# TRUE if we want debug information
#__.list            = list		# List DDF files in a directory
