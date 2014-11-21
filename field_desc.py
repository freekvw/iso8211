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

"""Field description stuff for use within iso8211.py

Separated into this file to make the source files shorter and more manageable.
"""

# $Id: field_desc.py,v 1.8 2004/04/05 17:44:57 d-rock Exp $

import sys
import os
import array
import string
import Dates

from   misc   import *
import format



# ----------------------------------------------------------------------
class Field_desc:
	"""An ISO 8211 data descriptive field.

	Initialisation arguments:

		ddr		the DDR we are working in
		tag		the tag whose descriptive field we are reading
		octets		the data descriptive field's data

	A Field_desc object contains:

		ddr			back reference to our DDR
		tag			the tag we are a description for

		field controls		
		data field name		
		array descriptor
		format controls
	"""

	def __init__(self,ddr,tag,octets):

		# Do the basic initialisation

		self._setup(ddr,tag,octets)

		# And set up our field controls, field name, array descriptor and format controls

		self._process()


	def _setup(self,ddr,tag,octets):
		"""Called at the start of initialisation by ALL field descriptions.

		Sets the tag, octets and DDR reference, and defines all our values
		(mostly as None).
		"""

		# Remember the information we are given

		self.ddr    = ddr
		self.tag    = tag
		self.octets = octets

		# Remember our level

		self.level = ddr.leader.interchange_level

		# And unset our contents

		self.field_controls   = None
		self.data_field_name  = None
		self.array_descriptor = None
		self.format_controls  = None

	def _process(self):
		"""Called during initialisation to setup the rest of our contents."""

		# Working out the field controls is easy - they just come first

		fc_len  = self.ddr.leader.field_control_length
		octets  = self.octets

		self.field_controls  = Field_controls(self.tag,self.level,octets[0:fc_len])

		# The data field name is then everything up to the first UT
		# (or FT at level 1)

		octets = octets[fc_len:]

		self._read_field_name(octets)

		# Given the field controls, we can work out a basic guess
		# at the array descriptor and format controls - so do so

		self.array_descriptor = Array_descriptor(self.tag,self.field_controls)
		self.format_controls  = Format_controls (self.tag,self.field_controls)

		# If our level is 1, that's all we expect, otherwise
		# we have other things to look for...

		if self.level > 1:

			# Read the array descriptor and format controls
			# (not forgetting to ignore the UT character that ended
			# the data field name)

			octets = octets[len(self.data_field_name)+1:]

			self._read_for_levels_2_and_3(self.tag,octets)

		# Check things made sense

		self.array_descriptor.check(self)
		self.format_controls.check(self)


	def _read_field_name(self,octets):
		"""Read the data field name."""

		# At level 1, the data field name is all that is in the field
		# description, so it is ended by FT. At other levels, it is
		# ended by UT. So read these appropriately

		if self.level == 1:
			self.data_field_name = read_to_FT(octets)
		else:
			# In 6.4.1, para 1, it says:
			# "Missing elements of the data description shall be represented by
			#  adjacent delimiters and a terminal string of adjacent delimiters
			#  shall not be replaced by the field delimiter."
			#        ^^^
			# Some data written by the SDTS FIPS123 library (in particular) seems
			# to disobey this - I need to check what the previous version of ISO 8211
			# has to say, since that's what they've coded to...

			# So how do we handle this?
			# The two problems I've found are:
			# 1) null array descriptor and format controls, so they omitted the UTs
			# 2) terminating the data field name with an FT instead of a UT - it may
			#    be that (1) is a special case of this

			# So first, try to read up to a terminating FT
			# (at worst, this should read to the end of the field description)

			temp = read_to_FT(octets)

			# Then try to do it correctly

			try:
				self.data_field_name = read_to_UT(octets)
			except iso8211_syntax_error:
				print "Warning: Data field name for `%s' was not terminated by UT\n" \
				      "         Data read was: `%s'\n" \
				      "         Assuming field name SHOULD be: `%s'"%\
				      (self.tag,printable(octets),printable(temp))

				self.data_field_name = temp

			# If reading it to a UT or FT gives us a shorter result than
			# just reading to a UT, then we have found error (2) - so complain
			# and use the `correct' data

			if len(temp) < len(self.data_field_name):
				print "Warning: Data field name for `%s' was terminated by FT "\
				      "(instead of UT)\n" \
				      "         Data read was: `%s'\n" \
				      "         Assuming field name SHOULD be: `%s'"%\
				      (self.tag,printable(octets),printable(temp))

				self.data_field_name = temp


	def _read_for_levels_2_and_3(self,tag,octets):
		"""Read the array descriptor and format controls.

		These are only present for levels 2 and 3."""

		# The array descriptor (if any) is up to the next UT
		# (not forgetting to ignore the UT character that ended
		# the data field name)

		if len(octets) > 1:

			array_desc = read_to_UT_or_FT(octets)

			

			try:
				self.array_descriptor.parse(array_desc)
			except iso8211_no_array_error:
				# Give better data for this exception
				# (the array descriptor can't see our octets)
				raise iso8211_noarray_error,(self.tag,self.octets)

			# And the format controls (if any) come after that
			# (not forgetting to ignore the UT or FT character
			# that ended the array descriptor)

			octets = octets[len(array_desc)+1:]

			# If the array descriptor was ended by the terminal FT,
			# then we may indeed not have any format controls
			# So check the length of the string we're left with...

			if len(octets) > 0:
				self.format_controls.parse_with_FT(octets)


	def __del__(self):
		"""Attempt to defeat any circular references we might have."""

		#if debugging:
		#	print "__del__ for",`self`

		self.ddr = None


	def __repr__(self):
		return "Field description for tag `"+self.tag+"'"


	def _write_lab_fmt_vector(self,dfd,vector,width,count):
		"""Write out the DFD statements for a vector, with formats."""

		format = self.format_controls

		if count == 0:
			dfd.write("   FOR\n")
		else:
			dfd.write("   BY\n")

		# If this is the first vector in the Cartesian array,
		# and it has a single, null label, then it is a wildcard,
		# announcing a "table"
		# Oterwise, we just write out the labels...

		for label in vector:

			# Get the next format control

			control = format.next_item()

			# If it is an "X" control, it is not labelled
			# - so output it unlabelled and try again

			while control.control == "X":
				spaces = (len(self.tag)+2)*" "
				dfd.write("      %s  %s\n"%(spaces,`control`))
				control = format.next_item()

			dfd.write("      %-*s  %s\n"%(width+2,"'%s'"%label,`control`))


	def _write_lab_fmt(self,dfd):
		"""Write out the DFD statements for our labels, with formats.

		We assume that the labels are already known to make sense with the
		format controls...
		"""

		format = self.format_controls
		labels = self.array_descriptor

		# Make sure we start at the first format control

		format.rewind()

		# Find out how many simple array descriptors we have

		num_components = labels.num_structures()

		# Write each out

		for which in range(num_components):

			# We separate Cartesian labels with "THEN"

			if which > 0:
				dfd.write("THEN\n")

			# Extract the structure

			structure = labels.structures[which]

			# If it is not a Cartesian label, just write it out

			if not structure.labelled:
				structure.write_DFD(dfd)
				continue

			# So it is a Cartesian label - find out how many vector labels
			# there are in it

			num_vectors = structure.num_vectors()

			# Write each out

			for index in range(num_vectors):

				# Extract the vector

				vector = structure.vector_label(index)

				# It is only the LAST vector that can be written out
				# with merged formats

				if index == (num_vectors - 1):
					# Merge this (last) vector

					# The "width" is used to format labels properly
					# (see Simple_array_descriptor._write_DFD_vector()
					#  for an explanation of what we're doing)

					width = structure.max_label_len

					self._write_lab_fmt_vector(dfd,vector,width,index)
				else:
					# We are not merging format and labels for this vector,
					# so we can just ask it to write itself out

					structure.write_DFD_vector(dfd,vector,index)


	def _stm_report(self,dfd,msg):
		"""Used in debugging _safe_to_merge()."""

		if debugging:
			dfd.write("   --    "+msg+"\n")



	def _safe_to_merge(self,dfd):
		"""Is it safe to merge the labels and formats for this field?

		We return TRUE if we think merging makes sense, FALSE if we do not,
		and None (which is also false) if we're not sure.
		"""

		format = self.format_controls
		labels = self.array_descriptor

		if debugging:
			dfd.write("   -- Considering merging labels and formats\n")

		self._stm_report(dfd,"Format: %s"%format.octets)
		self._stm_report(dfd,"Labels: %s"%labels.octets)

		# If we have an unlabelled field, then we can't merge!

		if labels.unlabelled:
			self._stm_report(dfd,"[NO] (Unlabelled)")
			return FALSE
		else:
			self._stm_report(dfd,"[OK] (Not unlabelled)")

		# If we have a variable array descriptor, then it is plainly not
		# possible to merge labels and formats, since there are no labels

		if labels.variable:
			self._stm_report(dfd,"[NO] (Variable array)")
			return FALSE
		else:
			self._stm_report(dfd,"[OK] (Not variable)")

		# If any of the structures individually cannot be merged, then
		# it will stop us doing the whole lot

		for structure in labels.structures:
			# Numeric arrays don't have labels, so can't be merged

			self._stm_report(dfd,"Structure: `%s'"%structure.octets)

			if not structure.labelled:
				self._stm_report(dfd,"[NO] (Numeric array)")
				return FALSE
			else:
				self._stm_report(dfd,"[OK] (Labelled)")

			# We are only allowed to merge structures with a dimensionality of
			# 0, 1 or 2 (B.2.6.2)

			if structure.dimension > 2:
				self._stm_report(dfd,"[NO] (Dimension %d, not 1..2)"%structure.dimension)
				return FALSE
			else:
				self._stm_report(dfd,"[OK] (Dimension %d)"%structure.dimension)

			# We can't merge a structure with no labels (unless it is
			# elementary, when it is OK)

			if structure.cartesian_label == [['']] and \
			   self.field_controls.data_structure != ISO8211_DS_ELEMENTARY:
				self._stm_report(dfd,"[NO] (Unlabelled, not elementary)")
				return FALSE
			else:
				if structure.cartesian_label == [['']]:
					self._stm_report(dfd,"[OK] (Unlabelled, but elementary)")
				else:
					self._stm_report(dfd,"[OK] (Labelled)")

		# If the last array descriptor is NOT a table, then we have a fixed
		# number of (expanded) labels, so we should be OK

		if not labels.is_table(-1):
			self._stm_report(dfd,"[OK] (Final structure not a table)")
			return TRUE
		else:
			self._stm_report(dfd,"[..] (Final structure is a table)")

		# Otherwise, we have a final table in our structures

		# Do we have any "X" format controls in our format
		# (these make life difficult, because they don't get
		# labelled)

		got_X = FALSE

		for item in format.flatlist:
			if item.control == "X":
				got_X = TRUE
				break

		# If we DID have an "X", then I think this is too difficult
		# to handle at the moment...

		if got_X:
			self._stm_report(dfd,"[NO] (Format includes `X')")
			return FALSE
		else:
			self._stm_report(dfd,"[OK] (Format does not include `X')")

		# Work out how many (expanded) labels we have, in all
		# but the last structure

		early_labels   = 0
		num_structures = len(labels.structures)

		for which in range(num_structures - 1):
			early_labels = early_labels + len(labels.structures[which].labels)

		# And how many (expanded but starting with "*") labels are there
		# in that final table?

		final_labels = len(labels.structures[-1].labels)

		self._stm_report(dfd,"Flat   count (labels) = %d"%early_labels)
		self._stm_report(dfd,"Repeat count (labels) = %d"%final_labels)
		self._stm_report(dfd,"Flat   count (format) = %d"%len(format.flatlist))
		self._stm_report(dfd,"Repeat count (format) = %d"%len(format.repeat))

		# Is that compatible with the format controls?

		# If we only have one structure, then the label flat count will
		# be zero. In that count, if the other counts are all the same,
		# we will be OK

		if num_structures == 1:
			self._stm_report(dfd,"Only one structure")
			if final_labels == len(format.flatlist) == len(format.repeat):
				self._stm_report(dfd,"[OK] (Flat and repeat counts match)")
				return TRUE
			else:
				self._stm_report(dfd,"[..] (Flat and repeat counts do not match)")

		# Otherwise, we have multiple structures - these will be a series of
		# "flat" tuples, finishing with the table. So if the flat and repeat
		# patterns for both labels and formats happen to be the same, then we
		# should be OK

		self._stm_report(dfd,"More than one structure")

		if early_labels == len(format.flatlist) and \
		   final_labels == len(format.repeat):
			self._stm_report(dfd,"[OK] (Flat and repeat counts match)")
			return TRUE
		else:
			self._stm_report(dfd,"[..] (Flat and repeat counts do not match)")

		# Otherwise, that's probably enough difficult thinking for now

		self._stm_report(dfd,"[NO] (Nowt else to test)")
		return FALSE


	def write_labels_and_formats(self,dfd,merge=TRUE):
		"""Write out the formats and labels to the DFD.

		MERGE is TRUE if want to intertwine labels and formats when possible,
		and FALSE if we never want to.
		"""

		# For interest's sake, write out the ORIGINAL format controls

		dfd.write("   -- Format controls: %s\n"%self.format_controls.octets)

		# And now do it prettily

		if merge and self._safe_to_merge(dfd):
			self._write_lab_fmt(dfd)
		else:
			self.array_descriptor.write_DFD(dfd)
			self.format_controls.write_DFD(dfd)


	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is TRUE if want to intertwine labels and formats when possible,
		and FALSE if we never want to.
		"""

		# Still a way to go with this, but it's a beginning...

		dfd.write("\n"
			  "FIELD '%s' '%s'\n"%(self.tag,self.data_field_name))

		if self.level == 3 and self.ddr.parents != {}:
			try:
				parent = self.ddr.parents[self.tag]
				dfd.write("   PARENT '%s'\n"%parent)
			except KeyError:
				print "Warning: Field `%s' does not have an entry in the " \
				      "field tag pair list"%self.tag

		self.field_controls.write_DFD(dfd)

		self.write_labels_and_formats(dfd,merge)

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)

		if self.level == 3 and self.ddr.parents != {}:
			try:
				parent = self.ddr.parents[self.tag]
			except KeyError:
				parent = "<None found in tag pair list>"

			print "            parent              = `%s'"%parent

		self.field_controls.show()

		print "            data field name     = `%s'"%printable(self.data_field_name)

		if self.array_descriptor != None:
			self.array_descriptor.show()
		else:
			print "            array descriptor is <empty>"

		if self.format_controls != None:
			self.format_controls.show()
		else:
			print "            format controls are <empty>"


# ----------------------------------------------------------------------
class Field_desc_00(Field_desc):
	"""An ISO 8211 data descriptive field for tag "0..0" (File control field)

	This is a sub-class of the normal Field_desc field.
	"""

	def __init__(self,ddr,tag,octets):

		# We can do the normal "setup" call safely enough

		Field_desc._setup(self,ddr,tag,octets)

		# We then want to read the field controls

		fc_len  = ddr.leader.field_control_length

		self.field_controls  = Field_controls(tag,self.level,octets[0:fc_len])

		# If we're at a level greater than 1, the field controls should
		# be all zeroes - check...

		if self.level > 1:
			if self.field_controls.data_structure     != "0"  or \
			   self.field_controls.data_type          != "0"  or \
			   self.field_controls.auxiliary_controls != "00":
				print "Warning: First four octets of field controls for `%s'" \
				      "are `%s',\n" \
				      "         instead of `0000' - see ISO/IEC 8211 6.2.1.1"%\
				      (self.tag,octets[0:4])

		# The external file title is (effectively) the data field name,
		# except that the rules about whether there is a UT or an FT
		# at its end are a bit different

		octets = octets[fc_len:]

		if self.level == 3:
			# We may optionally have the file title and then a list
			# of field tag pairs

			self.external_file_title = read_to_UT_or_FT(octets)

			# Remove the file title and its terminator from the
			# start of our octets

			octets = octets[len(self.external_file_title)+1:]

			# If we have any octets left, then we have a list of field tag pairs

			if len(octets) > 0:
				self._read_field_tag_pairs(octets)

		else:
			# We only have the file title

			self.external_file_title = read_to_FT(octets)


	def _read_field_tag_pairs(self,octets):
		"""Read a list of field tag pairs into the DDR "parents" dictionary."""

		# Work out the size of field tags

		ddr  = self.ddr
		size = ddr.leader.sizeof_field_tag

		# The octets should be an even multiple of that, with a final FT

		if octets[-1] != FT:
			raise iso8211_dir_error,(EXC_DIR_TAGPAIRFT,self.tag,self.octets)

		octets = octets[:-1]

		# The octets should be COUNT*size long, and COUNT should be even

		count = len(octets) / size

		if count * size != len(octets) or count % 2 != 0:
			raise iso8211_dir_error,(EXC_DIR_TAGPAIR,self.tag,size,self.octets)

		# The `binary tree' is formed of pairs of the form:
		#	parent tag : child tag
		# so it should be fairly easy to interpret...

		ddr.parents = {}

		for index in range(0,count,2):
			base = index * size

			#print "parent  %2d -> %s"%(base,     octets[base     :base+size])
			#print "child   %2d -> %s"%(base+size,octets[base+size:base+size*2])

			parent = octets[base     :base+size]
			child  = octets[base+size:base+size*2]

			# Key is child, value is parent

			ddr.parents[child] = parent

			# And remember the order we find the children in, so we can
			# reconstruct the ordering in the tree, if necessary

			ddr.child_list.append(child)

		# And check that the list makes sense with regard to 0..<digit> tags

		self._check_list(ddr,size)


	def _check_list(self,ddr,size):
		"""Check that the field tag pair lists make sense wrt 0..<digit> tags."""

		# Check that none of the 0..<digit> tags occur in the tree
		# (except for 0..1, of course, which we check is never a parent)

		nought1 = nought_tag(size,1)

		# Keep some state so we don't complain twice about a single tag

		bad_tags = []
		bad_0001 = FALSE

		for child in ddr.child_list:
			parent = ddr.parents[child]

			self._check_tag(child, nought1,bad_tags)
			self._check_tag(parent,nought1,bad_tags)

			if child == nought1:
				if not bad_0001:
					print "Warning: tag `%s' should never be a child in the"\
					      " field tag list"%child
					bad_0001 = TRUE


	def _check_tag(self,tag,nought1,bad_tags):
		"""Check if a tag is allowed in the field tag list."""

		if is_nought_tag(tag) and tag != nought1:
			if tag not in bad_tags:
				print "Warning: tag `%s' should not occur in the field tag list"%tag
				bad_tag.append(tag)


	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is ignored - it is included for compatibility with our
		parent class.
		"""

		dfd.write("\n"
			  "FIELD '%s' '%s'\n"%(self.tag,self.external_file_title))

		if self.level == 3 and self.ddr.parents != {}:
			dfd.write("   -- Field tag pairs:\n")

			for child in self.ddr.child_list:
				dfd.write("   --    Field `%s' has child `%s'\n"%\
					  (self.ddr.parents[child],child))

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)
		print "            external file title = `%s'"%printable(self.external_file_title)
		if self.level == 3 and self.ddr.parents != {}:
			print "                field tag pairs =",
			count = 0
			for child in self.ddr.child_list:
				if count % 4 == 0:
					if count != 0:
						print "\n                                 ",
				else:
					print " ",

				print "%s -> %s"%(self.ddr.parents[child],child),
				count = count + 1
			print



# ----------------------------------------------------------------------
class Field_desc_01(Field_desc):
	"""An ISO 8211 data descriptive field for tag "0..1" (Record identifier field)

	This is a sub-class of the normal Field_desc field.
	"""

	def __init__(self,ddr,tag,octets):

		# Mostly, this field behaves just like any other field,
		# except that it is the ROOT of the tag pair list (if any)

		# So do the normal initialisation

		Field_desc.__init__(self,ddr,tag,octets)

		# I should really check all sorts of stuff, but let's
		# not bother for the moment



	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is TRUE if want to intertwine labels and formats when possible,
		and FALSE if we never want to.
		"""

		# Still a way to go with this, but it's a beginning...

		dfd.write("\n"
			  "FIELD '%s' '%s'\n"%(self.tag,self.data_field_name))

		# Don't attempt to write out any PARENT information

		self.field_controls.write_DFD(dfd)

		self.write_labels_and_formats(dfd,merge)

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)

		# Don't attempt to write out any PARENT information

		self.field_controls.show()

		print "            data field name     = `%s'"%printable(self.data_field_name)

		if self.array_descriptor != None:
			self.array_descriptor.show()
		else:
			print "            array descriptor is <empty>"

		if self.format_controls != None:
			self.format_controls.show()
		else:
			print "            format controls are <empty>"


# ----------------------------------------------------------------------
class Field_desc_02(Field_desc):
	"""An ISO 8211 data descriptive field for tag "0..2" (User application field)

	This is a sub-class of the normal Field_desc field.
	"""

	def __init__(self,ddr,tag,octets):

		# Just about everything that normal field descriptions want is irrelevent
		# All we need REALLY do is remember our original octets - so let's just
		# do the basic "setup" call, which does all we need

		Field_desc._setup(self,ddr,tag,octets)


	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is ignored - it is included for compatibility with our
		parent class.
		"""

		dfd.write("\n"
			  "FIELD '%s'\n"%(self.tag))

		dfd.write("   CONTENT '%s'\n"%iso6429_printable(self.octets))

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)
		print "            content             = `%s'"%iso6429_printable(self.octets)


# ----------------------------------------------------------------------
class Field_desc_03(Field_desc):
	"""An ISO 8211 data descriptive field for tag "0..3" (Announcers or field identifiers)

	This is a sub-class of the normal Field_desc field.
	"""

	def __init__(self,ddr,tag,octets):

		# Just about everything that normal field descriptions want is irrelevent
		# All we need REALLY do is remember our original octets - so let's just
		# do the basic "setup" call, which does all we need

		Field_desc._setup(self,ddr,tag,octets)


	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is ignored - it is included for compatibility with our
		parent class.
		"""

		dfd.write("\n"
			  "FIELD '%s'\n"%(self.tag))

		dfd.write("   ESCAPE '%s'\n"%iso6429_printable(self.octets))

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)
		print "            announcers         = `%s'"%iso6429_printable(self.octets)



# ----------------------------------------------------------------------
class Field_desc_09(Field_desc):
	"""An ISO 8211 data descriptive field for tag "0..9" (Recursive tree LINKS field)

	This is a sub-class of the normal Field_desc field.
	"""

	def __init__(self,ddr,tag,octets):

		# Mostly, this field behaves just like any other field,
		# except that it is not included in the tag pair list

		# So do the normal initialisation

		Field_desc.__init__(self,ddr,tag,octets)

		# I should really check all sorts of stuff, but let's
		# not bother for the moment



	def write_DFD(self,dfd,merge=TRUE):
		"""Write out the appropriate DFD data for this field description.

		MERGE is TRUE if want to intertwine labels and formats when possible,
		and FALSE if we never want to.
		"""

		# Still a way to go with this, but it's a beginning...

		dfd.write("\n"
			  "FIELD '%s' '%s'\n"%(self.tag,self.data_field_name))

		# Don't attempt to write out any PARENT information

		self.field_controls.write_DFD(dfd)

		self.write_labels_and_formats(dfd,merge)

		dfd.write("END FIELD\n")


	def show(self):
		"""Print out the contents of this field description."""

		print "        Field description for tag `%s'"%(self.tag)

		# Don't attempt to write out any PARENT information

		self.field_controls.show()

		print "            data field name     = `%s'"%printable(self.data_field_name)

		if self.array_descriptor != None:
			self.array_descriptor.show()
		else:
			print "            array descriptor is <empty>"

		if self.format_controls != None:
			self.format_controls.show()
		else:
			print "            format controls are <empty>"


# ----------------------------------------------------------------------
class Field_controls:
	"""An ISO 8211 data field's field controls

	Initialisation arguments:

		tag		the tag for the field we belong to
		level		the level of the file
		octets		the field control string

	A Field_controls object contains:

		tag			the tag we relate to
		octets			the field control string

		data_structure     	RP 0
		data_type          	RP 1
		auxiliary_controls 	RP 2..3
		printable_ft       	RP 4
		printable_ut       	RP 5
		truncated_esc_sequence	RP 6..8 if present


	"""

	def __init__(self,tag,level,octets):

		self.tag    = tag
		self.octets = octets
		self.level  = level

		# Unset the basic quantities we remember

		self.data_structure     = None
		self.data_type          = None
		self.auxiliary_controls = None
		self.printable_ft       = None
		self.printable_ut       = None

		# The length of the field controls depends upon the level

		if level == 1:
			self._read_for_level_1()
		else:
			self._read_for_levels_2_and_3()


	def _read_for_level_1(self):
		"""At level 1, we only get (maybe) the truncated escape sequence."""

		if len(self.octets) > 0:
			self.truncated_esc_sequence = self.octets
		else:
			self.truncated_esc_sequence = None

		# We can `make up' some of the rest, since at level 1
		# all fields are elementary, and are "strings"

		self.data_structure = ISO8211_DS_ELEMENTARY
		self.data_type      = ISO8211_DT_CHARACTER


	def _read_for_levels_2_and_3(self):
		"""At levels 2 and 3 we get "real" field controls."""

		# Dissect the field controls

		self.data_structure     = self.octets[0:1]
		self.data_type          = self.octets[1:2]
		self.auxiliary_controls = self.octets[2:4]
		self.printable_ft       = self.octets[4:5]
		self.printable_ut       = self.octets[5:6]

		if len(self.octets) > 6:
			self.truncated_esc_sequence = self.octets[6:]
		else:
			self.truncated_esc_sequence = None

		# Check they make sense
		# Are the values we found in the right overall range?

		if (self.data_structure not in string.digits)  or \
		   int(self.data_structure) < 0 or int(self.data_structure) > 3:
			raise iso8211_unexpected,(self.data_structure,"data structure code",tag,"0..3")

		if (self.data_type not in string.digits)  or \
		   int(self.data_type) < 0 or int(self.data_type) > 6:
			raise iso8211_unexpected,(self.data_type,"data type code",tag,"0..6")

		# Auxiliary controls are only used for binary forms, and are quite
		# constrained in the values they can take

		if self.auxiliary_controls != "00":
			if self.data_type != "5":
				raise iso8211_unexpected,\
				      (self.auxiliary_controls,"auxiliary controls",tag,
				      "00 (as data type code is %s)"%self.data_type)
			else:
				what  = self.auxiliary_controls[0]
				width = self.auxiliary_controls[1]

				# Check against 6.4.3.3 h) table 3

				if ((what == "1" or what == "2") and \
				    (width != "1" and width != "2" and width != "3" and width != "4")):
					raise iso8211_unexpected,\
					      (self.auxiliary_controls,"auxiliary controls",tag,
					       "%s1..%s4"%(what,what))

				elif ((what == "3" or what == "4" or what == "5") and \
				      (width != "4" and width != "8")):
					raise iso8211_unexpected,\
					      (self.auxiliary_controls,"auxiliary controls",tag,
					       "%s4 or %s8"%(what,what))


	def __repr__(self):
		return "Field controls for tag `"+self.tag+"'"


	def _write_DFD_comment(self,dfd):
		"""Output an informative comment about the data."""

		# In the following, the exceptions shouldn't happen, as the data should
		# have been checked at an earlier stage...

		try:
			dfd.write("   -- Field is %s,"%ds_dict[self.data_structure])
		except:
			dfd.write("   -- Field is unrecognised data structure %s,"%self.data_structure)

		try:
			dfd.write(" %s"%dt_dict[self.data_type])
		except:
			dfd.write(" unrecognised data type %s"%self.data_type)

		if self.auxiliary_controls != "00":
			char1 = self.auxiliary_controls[0:1]
			width = int(self.auxiliary_controls[1:2])

			try:
				dfd.write(" (binary: %s, width %d)"%(bintype_dict[char1],width))
			except:
				dfd.write(" (unrecognised binary type %s, width %d)"%(char1,width))

		dfd.write("\n")


	def write_DFD(self,dfd):
		"""Write out the appropriate DFD data for these field controls."""

		# An informative comment of exactly what we derived our information from
		# is nice, I think, so generate one...

		if self.level > 1:
			self._write_DFD_comment(dfd)

		# And output the stuff it is up to us to write out

		if self.level > 1:
			if self.printable_ft != ';' or self.printable_ut != '&':
				dfd.write("   PRINTABLE GRAPHICS '%s%s'\n"%(self.printable_ft,
									    self.printable_ut))

		if self.truncated_esc_sequence != None:
			dfd.write("   ESCAPE  '%s' -- hex %s (%s)\n"%\
				  (self.truncated_esc_sequence,
				   pretty_hex(self.truncated_esc_sequence),
				   iso2022_charset(self.truncated_esc_sequence)))


	def show(self):
		"""Print out the contents of these field controls."""

		print "            field controls      = `%s'"%(printable(self.octets))

		if self.level > 1:
			print "            data structure code = `%s'"%(self.data_structure),
			try:
				print "\t(%s)"%ds_dict[self.data_structure]
			except:
				print "\t(unrecognised data structure)"

			print "            data type code      = `%s'"%(self.data_type),
			try:
				print "\t(%s)"%dt_dict[self.data_type]
			except:
				print "\t(unrecognised data type)"

			print "            auxiliary controls  = `%s'"%(self.auxiliary_controls),

			if self.auxiliary_controls == "00":
				print
			else:
				char1 = self.auxiliary_controls[0:1]
				width = int(self.auxiliary_controls[1:2])

				try:
					print "\t(%s, width %d)"%(bintype_dict[char1],width)
				except:
					print "\t(unrecognised binary type, width %d)"%width

			print "            printable graphics: FT = '%s', UT = '%s'"%(self.printable_ft,
										      self.printable_ut)

		if self.truncated_esc_sequence != None:
			print "            truncated esc sequence = `%s' (hex %s: %s)"%\
			      (printable(self.truncated_esc_sequence),
			       pretty_hex(self.truncated_esc_sequence),
			       iso2022_charset(self.truncated_esc_sequence))


# ----------------------------------------------------------------------
class Array_descriptor:
	"""An ISO 8211 data field's array descriptor

	Initialisation arguments:

		tag		the tag for the field we belong to
		field_controls	the field controls for this field

	These are used to `guess' a reasonable array descriptor definition,
	which is further refined by use of the "parse()" method if there is
	an array descriptor for this field.

	An Array_descriptor object contains:

		tag			the tag we relate to
		structure_code		the data structure code (RP 0 of field controls)

		octets			the array descriptor string

		unlabelled		TRUE if this array descriptor is for an unlabelled
					field - this means that "octets" is empty, and
					"variable" is FALSE

		variable		TRUE if this field contains an array of
					variable dimensions (6.4.3.2.1),
					FALSE if it contains a concatenated structure
					(see "structures" below for more on this)
					(only relevant if "structure_code" is "2" or "3")

	If not "variable":

		structures		a list of Simple_array_descriptors, each of which
					is either a Cartesian label or a fixed numeric
					array descriptor

	For handling expanded labels (if not "variable"):

		current_structure	the current structure's index
		current_index		the current expanded label's index in that structure
		current_item		the current expanded label


	Note that it is possible to do:

		for label in array_desc:
			<process label>
	"""

	def __init__(self,tag,field_controls):

		self.tag    		= tag
		self.field_controls	= field_controls
		self.octets 		= None
		self.unlabelled		= TRUE
		self.variable		= FALSE
		self.structures		= []

		# Try to guess what our description is

		self._decide_default()

		# Set up for iterating through the expanded labels

		if not self.variable:
			self.rewind()


	def _decide_default(self):
		"""Try to work out what default information we can..."""

		# Study 6.4.1 (especially table 2) and 6.4.3.2 for the reasons
		# for what we do below...

		structure_code  = self.field_controls.data_structure
		self.structures	= []

		if structure_code == ISO8211_DS_ELEMENTARY:
			# We have elementary data - a single subfield
			# Assume it is `labelled', but with a single zero length label

			self.variable   = FALSE
			self.unlabelled = TRUE

			empty_element = Simple_array_descriptor(self.tag,self,"")
			self.structures.append(empty_element)

		elif structure_code == ISO8211_DS_VECTOR:
			# We have vector data
			# This requires a vector label, which we will have to
			# get later on. If we aren't given one later on, we
			# have to degenerate to the elementary case (as we are
			# allowed to do in 6.4.3.2.4 NOTE 19)
			# (6.4.1, table 2 indicates that this data structure
			#  contains a 'Vector label', so it can't be a variable
			#  array)

			self.variable   = FALSE
			self.unlabelled = TRUE

			empty_element   = Simple_array_descriptor(self.tag,self,"")
			self.structures.append(empty_element)

		elif structure_code == ISO8211_DS_ARRAY:
			# We have array (multi-dimensional) data
			# Assume it is of variable array dimension (i.e., the
			# array dimensions specified in the data) until we are
			# told otherwise

			self.variable   = TRUE
			self.unlabelled = FALSE		# This is NOT unlabelled data

		elif structure_code == ISO8211_DS_CONCATENATED:
			# We have concatenated data
			# This requires an array descriptor, and there's not
			# much we can say until we've seen that

			self.variable   = FALSE
			self.unlabelled = TRUE

		else:
			raise iso8211_internal_error,\
			      "Array_descriptor (field `%s'): unknown data structure code `%s'"%\
			      (self.tag,structure_code)


	def check(self,field_desc):
		"""Check the array descriptor makes sense.

		Call this after finishing reading in the field description, to check
		that we have all the information we need for this field.

		Raises an appropriate exception if things don't check out.
		"""

		# Basically, we're checking up on the guesses made in
		# _decide_default(), to see if the information that was
		# wanted has been provided...

		structure_code = self.field_controls.data_structure

		# The only one we couldn't guess for was concatenated structures

		if structure_code == ISO8211_DS_CONCATENATED:
			if self.structures == []:
				raise iso8211_noarray_error,(self.tag,field_desc.octets)


	def __del__(self):
		# Remove any references elsewhere

		self.field_controls = None
		self.structures     = None


	def __repr__(self):
		return "Array descriptor for tag `"+self.tag+"'"


	def parse(self,octets):
		"""Given the OCTETS for an array descriptor, work out their meaning."""

		# Since this can be called more than once (in theory, at least)
		# reinstate our guess as to our state

		self._decide_default()

		# If the array descriptor is of zero length, but we have
		# multi-dimensional data, then we have variable array dimensions
		# - there will be values in the data indicating the dimension and
		#   extents of the array

		structure_code = self.field_controls.data_structure

		if len(octets) == 0:

			# We do not have any array descriptor
			# For elementary, vector and array data, this simply means that
			# we must use the guess we already had
			# However, if we NEED an array descriptor, this is an error...

			if structure_code == ISO8211_DS_CONCATENATED:
				# This is raised with our own octets, because we can't
				# see the field descriptors' - but we fully expect our
				# caller to remedy that...
				raise iso8211_noarray_error,(self.tag,self.octets)

		else:
			# Otherwise, we have an explicit array descriptor
			# Remember the octets we were given

			self.octets = octets

			# Note that we are labelled

			self.unlabelled = FALSE

			# Note that we are not a variable array

			self.variable = FALSE

			# And parse them into a concatenated structure

			self._parse_concatenated(octets)

			# And do they make internal sense?

			self.check_legal()

			# Finally, set up for iterating through the expanded labels

			self.rewind()


	def _parse_concatenated(self,octets):
		"""Parse the array descriptor OCTETS as concatenated structures."""

		# Create a list of structures, where each structure is a Cartesian label,
		# which is a list of vector labels, and where each vector label is a list
		# of subfield labels

		# First, split on "\\" (separating Cartesian labels)

		self.structures = []

		compound_list = string.splitfields(octets,"\\\\")

		for structure in compound_list:

			cartesian_label = Simple_array_descriptor(self.tag,self,structure)

			# Add the cartesian label to our concatenated structures list

			self.structures.append(cartesian_label)


	def __getitem__(self,which):
		"""Used in iteration - get the n'th expanded label.

		Returns expanded labels in order. If we are a table,
		they will repeat as necessary.

		Note that "which" is 0 upwards.
		"""

		# Simply return the result of "expanded_label"

		return self.item(which)


	def item(self,which):
		"""Return the expanded label with index "which".

		Works for both Cartesian labels and fixed arrays - for the former
		it returns an expanded label, and for the latter it returns an
		array "index" string.

		Raises ValueError if called for a variable dimension array.

		Note that "which" is 0 upwards, and that (if we are a table)
		it may be greater than the length of "labels".
		"""

		if self.variable:
			raise ValueError,"Unable to determine labels for variable arrays"

		if which < 0:
			raise IndexError,"Index should be 0 or more, not %d"%which
		elif which == self.current_index:
			return self.current_item
		elif which < self.current_index:
			self.rewind()
			while self.current_index < which:
				label = self.next_item()
			return label
		else:
			while self.current_index < which:
				label = self.next_item()
			return label


	def next_item(self):
		"""Return the next expanded label.

		Raises ValueError if called for a variable dimension array.

		Raises IndexError if there is no next label.
		"""

		if self.variable:
			raise ValueError,"Unable to determine labels for variable arrays"

		# Try the current structure first

		structure = self.structures[self.current_structure]

		try:
			self.current_index = self.current_index + 1
			self.current_item  = structure.item(self.current_index)
		except IndexError:
			# Hmm - is there another structure to try?

			self.current_structure = self.current_structure + 1

			if self.current_structure > (len(self.structures) - 1):
				raise IndexError,"No more labels"

			structure          = self.structures[self.current_structure]
			self.current_index = 0
			self.current_item  = structure.item(self.current_index)

		return self.current_item


	def rewind(self):
		"""`Rewind' the position in the expanded label list.

		After calling this, "next_item()" will return the first
		expanded label again.

		Raises ValueError if called for a variable dimension array.
		"""

		if self.variable:
			raise ValueError,"Unable to determine labels for variable arrays"

		self.current_structure = 0
		self.current_item      = None
		self.current_index     = -1


	def write_DFD(self,dfd):
		"""Write out the appropriate DFD data for this array descriptor.

		This routine copes with all forms of array descriptor (including
		empty ones), but does not attempt to fold labels in with format
		controls.
		"""

		structure_code = self.field_controls.data_structure

		if self.variable:
			# Variable array dimensions

			dfd.write("   -- Variable array dimensions\n")
			dfd.write("   STRUCTURE CODE %s -- %s\n"%(structure_code,
								  ds_dict[structure_code]))

		else:
			for structure in self.structures:
				structure.write_DFD(dfd)


	def num_structures(self):
		"""Returns the number of Cartesian labels in this array descriptor."""

		return len(self.structures)


	def num_vectors(self,which):
		"""Returns the number of vector labels in the "which"th Cartesian label.

		Note that the first Cartesian label is index 0, and the last can
		be found as index -1 (in other words, normal selection numbering).

		Raises IndexError if WHICH is out of range.
		"""

		cartesian_label = self.structures[which]

		return cartesian_label.num_vectors()


	def structure(self,which):
		"""Returns the simple array descriptor with index WHICH.

		SURELY THIS ISN'T NEEDED - JUST USE: array_desc.structures[which] DIRECTLY

		Note that the first simple array descriptor is index 0, and the last
		can be found as index -1 (in other words, normal selection numbering).

		Raises IndexError if WHICH is out of range.
		"""

		return self.structures[which]


	def vector_label(self,which1,which2):
		"""Returns a specific vector label.

		WHICH1 identifies the simple array descriptor (0 is the first), which
		       must, of course, be a Cartesian label
		WHICH2 identifies the vector label in that Cartesian label (0 is the first)

		Raises IndexError if either WHICH is out of range.
		"""
		cartesian_label = self.structures[which1]

		return cartesian_label.vector_label(which2)


	def is_table(self,which):
		"""Returns true if the WHICH'th simple array descriptor is a
		Cartesian label and a table.

		A Cartesian label is a table if its first vector label is null,
		but is NOT a table if it contains only a single (null) subfield
		label.

		Note that the first Cartesian label is index 0, and the last can
		be found as index -1 (in other words, normal selection numbering).

		Raises IndexError if WHICH is out of range.
		"""

		# Extract the first vector label from the requested Cartesian label

		cartesian_label = self.structures[which]

		return cartesian_label.is_table


	def check_legal(self):
		"""Check if the concatenated data structure makes sense.

		This checks that only the last Cartesian label (if any) is a
		table. It raises an appropriate exception if this goes wrong.
		"""

		# Figure out how many Cartesian labels there are

		count = self.num_structures()

		# Check that the non-last ones are not tables

		for which in range(count-1):
			if self.is_table(which):
				raise iso8211_concat_error,(self.tag,which,self.octets)


	def next_label(self):
		"""Return the next (expanded) subfield label.

		If this is a variable array field, return ValueError
		If there is no next label, return IndexError.
		"""

		if self.variable:
			return ValueError,"Field has variable array data (no labels)"

		



	def show(self):
		"""Print out the contents of this array descriptor."""

		print "            array descriptor"
		#print "            array descriptor    = '%s'"%printable(self.octets)

		if self.variable:
			print "                Variable array dimensions"
		else:
			for structure in self.structures:
				structure.show()



# ----------------------------------------------------------------------
class Simple_array_descriptor:
	"""An ISO 8211 simple (non-compound) array descriptor.

	Array_descriptor objects use objects of this class to hold information
	about entries in a (potentially) concatenated structure. This means
	that this object may hold either:

	- a Cartesian label (6.4.3.2.4), or
	- a numeric array descriptor (6.4.3.2.1) of type "fixed"

	(a numeric array descriptor held here has to be of type "fixed" since
	a variable array is indicated by the absence of an array descriptor,
	and we only exist in the PRESENCE of such...)

	Initialisation arguments:

		tag		the tag for the field we belong to
		parent		the Array_descriptor that owns us
		octets		the octets that define our array descriptor

	A Simple_array_descriptor object contains:

		tag			the tag we relate to
		octets			the array descriptor string

		labelled		TRUE  if we are a Cartesian label
					FALSE if we are a numeric array descriptor

		dimension		the number of dimensions
					For a Cartesian label, this is the number of
					dimensions indicated by the labelling.
					For a numeric array descriptor, this is the
					number of extents given.

	For a Cartesian label:

		cartesian_label		A Cartesian label, which is a list of vector labels,
						   each of which is a list of subfield labels

		max_label_len		The length of the longest subfield label in the
					Cartesian label

		labels			A list of the expanded labels for this Cartesian label

		is_table		TRUE if we are a table

	For a numeric array descriptor:

		extents			the extent in each dimension

	For handling expanded labels:

		current_item		the current expanded label
		current_index		the current expanded label's index

	Note that it is possible to do:

		for label in simple_array_desc:
			<process label>
	"""

	def __init__(self,tag,parent,octets):
		self.tag    	= tag
		self.parent	= parent
		self.octets 	= octets

		self.labelled		= TRUE	# A guess
		self.dimension		= None
		self.extents		= None
		self.cartesian_label	= []
		self.max_label_len	= 0
		self.is_table		= FALSE # A guess

		# Set up for iteration

		self.labels = []
		self.rewind()

		# And find out...

		self._parse()


	def __del__(self):
		# Remove any references elsewhere

		self.parent = None


	def __repr__(self):
		return "Simple array descriptor for tag `"+self.tag+"'"


	def _parse(self):
		"""Given the OCTETS for an array descriptor, work out their meaning."""

		if len(self.octets) == 0:
			# As a special case, if we have an empty array descriptor, then
			# we count that as a single null label

			self._parse_labels()

			self.labelled = TRUE

		else:
			# Otherwise, do we have fixed array dimensions?
			
			try:
				# Split the string on ","

				numbers = string.splitfields(self.octets,",")

				self.dimension = int(numbers[0])
				numbers        = numbers[1:]

				if len(numbers) != self.dimension:
					raise iso8211_array_error, \
					      ("Fixed array dimension error",tag,self.dimension)

				self.extents = []

				for number in numbers:
					self.extents.append(int(number))

				self.labelled = FALSE

			except ValueError:

				# No, it isn't that - try for labels

				self._parse_labels()

				# And do they make internal sense?

				self.labelled = TRUE

				# Finally, are we a table?

				self._check_table()

			# Work out our list of (expanded) labels

			self._expand_labels()


	def _parse_labels(self):
		"""Parse the array descriptor OCTETS as labels."""

		# Parse our octets as a list of vector labels,
		# where each vector label is a list of subfield labels

		self.cartesian_label = []

		# Split on "*" (separating vector labels)

		vectors = string.splitfields(self.octets,"*")

		for vector in vectors:

			# Split on "!" (separating subfield labels)
			# - this gives us a vector label (a list of subfield labels)

			vector_label = string.splitfields(vector,"!")

			# Add the vector label to our cartesian label

			self.cartesian_label.append(vector_label)

		# Work out the dimensionality
		# 0d -> elementary, a single subfield (in a single vector)
		# 1d -> vector,     a single vector
		# 2d -> array,      a pair of vectors
		# 3d -> array,      three vectors

		if len(self.cartesian_label) == 1 and len(self.cartesian_label[0]) == 1:
			self.dimension = 0
		else:
			self.dimension = len(self.cartesian_label)

		# Calculate the length of the longest subfield label
		# (this will later be useful in formatting the DFD neatly)

		self.max_label_len = 0

		for vector in self.cartesian_label:
			for label in vector:
				if len(label) > self.max_label_len:
					self.max_label_len = len(label)


	def _expand_labels(self):
		"""Expand out the Cartesian labels."""

		if self.labelled:
			self.labels = self._expand_labels_lab(self.cartesian_label)
		else:
			#print self.dimension,self.extents
			self.labels = expand_labels_num(self.extents)


	def _expand_labels_lab(self,vectors):
		"""Return a list of the labels generated from the given vectors."""

		this = vectors[0]	# The first vector
		rest = vectors[1:]	# The list of the remaining vectors

		if rest == []:
			# We don't have any more vectors after this
			return this

		else:
			# Expand out the rest

			temp = self._expand_labels_lab(rest)

			# And expand the result of that against "this"

			labels = []

			for item in this:
				for label in temp:
					#labels.append(item + "*" + label)
					labels.append(item + label)

			return labels


	def __getitem__(self,which):
		"""Used in iteration - get the n'th expanded label.

		Returns expanded labels in order. If we are a table,
		they will repeat as necessary.

		Note that "which" is 0 upwards.
		"""

		# Simply return the result of "expanded_label"

		return self.item(which)


	def item(self,which):
		"""Return the expanded label with index "which".

		Works for both Cartesian labels and fixed arrays - for the former
		it returns an expanded label, and for the latter it returns an
		array "index" string.

		Note that "which" is 0 upwards, and that (if we are a table)
		it may be greater than the length of "labels".
		"""

		if which < 0:
			raise IndexError,"Index should be 0 or more, not %d"%which
		elif which < len(self.labels):
			self.current_index = which
			self.current_item  = self.labels[which]
		elif self.is_table:
			# OK - we're a table, so we're into repeat territory
			# Work out our position in the repeat...

			posn = which % len(self.labels)

			self.current_item  = self.labels[posn]
			self.current_index = which

		else:
			raise IndexError,\
			      "Index should be 0 through %d, not %d"%(len(self.labels)-1,which)

		return self.current_item


	def next_item(self):
		"""Return the next expanded label."""

		return self.item(self.current_index + 1)


	def rewind(self):
		"""`Rewind' the position in the expanded label list.

		After calling this, "next_item()" will return the first
		expanded label again.
		"""

		self.current_item  = None
		self.current_index = -1


	def write_DFD_vector(self,dfd,vector,count):
		"""Write out the DFD statements for a vector - a list of subfield labels."""

		# The first vector starts with "FOR", the rest start with "BY"

		if count == 0:
			dfd.write("   FOR")
		else:
			dfd.write("   BY ")

		# If this is the first vector in the Cartesian array,
		# and it has a single, null label, then it is a wildcard,
		# announcing a "table"
		# Oterwise, we just write out the labels...

		if count == 0 and len(vector) == 1 and vector[0] == '':
			dfd.write("            -- table")	# wildcard - no labels to write out
		else:
			width = self.max_label_len + 2
			for label in vector:
				dfd.write(" %-*s"%(width,"'%s'"%label))

		dfd.write("\n")



	def _write_DFD_cartesian(self,dfd):
		"""Write out the DFD statements for a single Cartesian label."""

		# Check for the special case of a single, NULL label

		if self.cartesian_label == [['']]:

			structure_code = self.parent.field_controls.data_structure

			# If it is an elementary item, then we can do a "FOR ''",
			# otherwise we are better off doing a "STRUCTURE CODE" statement

			if structure_code == ISO8211_DS_ELEMENTARY:
				dfd.write("   FOR ''\n")
			else:
				dfd.write("   STRUCTURE CODE %s -- unlabelled %s\n"%\
					  (structure_code,ds_dict[structure_code]))

		else:
			# Otherwise, simply write out the individual vectors, one by one

			count = 0
			for vector in self.cartesian_label:
				self.write_DFD_vector(dfd,vector,count)
				count = count + 1


	def write_DFD(self,dfd):
		"""Write out the appropriate DFD data for this simple array descriptor.

		This routine does not attempt to fold labels in with format controls.
		"""


		if self.labelled:
			# A Cartesian label - write it out

			self._write_DFD_cartesian(dfd)

		else:
			# Fixed array dimensions - note we don't write out the
			# number of dimensions

			#dfd.write("   -- dimension %d, extents %s\n"%(self.dimension,self.extents))
			dfd.write("   NUMERIC DESCRIPTOR ")

			count = 0

			for item in self.extents:

				if count != 0:
					dfd.write(",")

				dfd.write("%d"%item)
				count = count + 1

			dfd.write("\n")


	def num_vectors(self):
		"""Returns the number of vector labels in our Cartesian label.

		Note that the first Cartesian label is index 0, and the last can
		be found as index -1 (in other words, normal selection numbering).

		Raises IndexError if we are not a Cartesian label.
		"""

		if self.cartesian_label == None:
			raise IndexError,"Not a Cartesian label"
		else:
			return len(self.cartesian_label)


	def vector_label(self,which):
		"""Returns the WHICH'th vector label (0 is the first).

		Raises IndexError if WHICH is out of range.
		"""

		return self.cartesian_label[which]


	def _check_table(self):
		"""Determines if this Cartesian label is a table.

		A Cartesian label is a table if its first vector label is null,
		but is NOT a table if it contains only a single (null) subfield
		label.
		"""

		# Extract the first vector label from the requested Cartesian label

		vector_label_0  = self.cartesian_label[0]

		# Is the first vector label null?

		if len(vector_label_0) == 1 and vector_label_0 == ['']:
			# It is null - but are we actually just a single subfield
			# label which is null, which doesn't count?

			self.is_table = (len(self.cartesian_label) != 1)
		else:
			# It is not null

			self.is_table = FALSE


	def show(self):
		"""Print out the contents of this simple array descriptor."""

		print "               simple array descriptor (%s)"%printable(self.octets)

		if self.labelled:
			print "                   Labelled:",self.octets
			print "                   which is:",self.cartesian_label

##			if self.labels != []:
##				print "                   expanded labels are:",
##				count = 0
##				for label in self.labels:
##					if count > 0:
##						print "                                       ",
##					count = count + 1
##					print "`%s'"%label

		else:
			print "                   Fixed array dimensions"
			print "                   dimension =",self.dimension
			print "                   extents   =",self.extents




# ----------------------------------------------------------------------
class Format_controls(format.Format):
	"""An ISO 8211 data field's format controls. A subclass of Format.

	Initialisation arguments:

		tag		the tag for the field we belong to
		field_controls	the field controls for this field

	A Format_controls object contains (above what its parent class has):

		tag		the tag we relate to
	"""

	def __init__(self,tag,field_controls):

		# Do our parent's initialisation

		format.Format.__init__(self)

		# And do our own specific stuff

		self.tag            = tag
		self.field_controls = field_controls

		# Guess a format according to the data type

		format_string = self._guess_format_string()

		if format_string != None:
			self.parse(format_string)

	def parse_with_FT(self,octets):
		"""Parse the given format controls.

		OCTETS is the format control string from the DDR, including the
		final FT."""

		# The format controls should fill the octets we were given,
		# except that the last octet should be FT - check it and lose it

		if octets[-1] != FT:
			raise iso8211_dir_error,(EXC_DIR_FLDFT,tag,octets)
		else:
			octets = octets[:-1]

		# And parse the remaining string (if any)

		if len(octets) > 0:
			self.parse(octets)

		# Check that that format is compatible with our field controls

		self._check_format()


	def parse(self,octets):
		"""Parse the given format controls."""

		# Note that if parsing the format control string fails,
		# we re-raise the "__.format.py" error as an equivalent
		# error of our own, with the field tag prepended to the
		# details tuple

		try:
			format.Format.parse(self,octets)
			# print "%s = %d bytes" % (self.tag, self.unit_size)
		except format.iso8211_format_error,details:
			raise iso8211_format_error,((tag,) + details)



	def _guess_format_string(self):
		"""Guess a format control string from our field controls.

		This returns an appropriate format control string, or None
		if there isn't one.
		"""

		type = self.field_controls.data_type
		aux  = self.field_controls.auxiliary_controls

		if type == ISO8211_DT_CHARACTER:
			return "(A)"
		elif type == ISO8211_DT_IMPLICIT_POINT:
			return "(I)"
		elif type == ISO8211_DT_EXPLICIT_POINT:
			return "(R)"
		elif type == ISO8211_DT_EXPLICIT_POINT_SCALED:
			return "(S)"
		elif type == ISO8211_DT_CHAR_MODE_BITSTRING:
			return "(C)"
		elif type == ISO8211_DT_BINARY_BITSTRING:

			if aux == "00":
				# This actually means "non-binary form or binary form
				# with formats", since we can't distinguish here...
				#return "(B)"		# assume non-binary form
				return None
			else:
				# This guess is imprecise - see the last paragraph on
				# page 19 of the standard - we actually need to know if
				# the binary controls have set our default ordering...
				# (otherwise, we assume LSOF, as here)
				return "(b%s)"%aux	# assume binary form [see 6.4.3.3 h)]

		elif type == ISO8211_DT_MIXED:
			return None			# there is no sensible guess
		else:
			raise iso8211_internal_error,\
			      "Format_controls (field `%s'): unknown data type code `%s'"%\
			      (self.tag,type)



	def _check_format(self):
		"""Check that our format is compatible with our field controls."""

		# Work out our initial guess (from the field controls) again

		guess = self._guess_format_string()

		# If it's None, we have nowt to do

		if guess == None:
			return

		# Remove the parentheses round it (which we don't need here)

		guess = guess[1:-1]

		# Otherwise, check that all the format controls in our final format
		# are compatible

		# (Should we raise an exception, or just grumble noisily?)

		for item in self.flatlist:
			control = item.control

			if control != guess:
				if guess == "B" and (control[0] == "B" or control[0] == "b"):

					# Binary forms are awkward, since our `guess' of "B" doesn't
					# actually tell us anything very useful if we have explicit
					# format controls. We're OK if we have the `BITSTRING' type
					# (which we remember as "B") with no auxiliary controls
					# (i.e., "00"), but a "B" or "b" format control

					continue

				elif control == "X":

					# We mustn't forget to allow "X" controls, as well, which
					# should just be ignored at this point...

					continue

				else:

					# Oh dear - looks like we have a problem

					print "Warning: In field `%s' the field controls `%s'" \
					      " indicate format `%s'\n" \
					      "         but the actual format controls are `%s'"%\
					      (self.tag,self.field_controls.octets,guess,self.octets)
					break

					# We USED to do the following - remember it just in case
					##raise iso8211_fcfmt_error,\
					##      (self.tag,self.field_controls.octets,guess,self.octets)


	def check(self,field_desc):
		"""Check the format controls make sense.

		Call this after finishing reading in the field description, to check
		that we have all the information we need for this field.

		Raises an appropriate exception if things don't check out.
		"""

		# Basically, we're checking up on the guesses made in
		# _guess_format_string(), to see if the information that
		# was wanted has been provided...

		type = self.field_controls.data_type

		# The only one we couldn't guess for was mixed

		if type == ISO8211_DT_MIXED:
			if self.controls == []:
				raise iso8211_noformat_error,(self.tag,field_desc.octets)
				


	def __del__(self):
		# Remove any references elsewhere

		self.field_controls = None

		# And do our parent's stuff as well, for safety

		format.Format.__del__(self)



	def __repr__(self):
		return "Format controls for tag `"+self.tag+"'"


	def write_DFD(self,dfd):
		"""Write out the appropriate DFD data for these format controls."""

		try:
			format.Format.write_DFD(self,dfd)
		except format.iso8211_format_error,details:
			raise iso8211_format_error,((self.tag,) + details)


	def show(self):
		"""Print out the contents of these format controls."""

		print "            format controls     = `%s'"%printable(self.octets)



# ----------------------------------------------------------------------
def expand_labels_num(extents):
	"""Return a list of the labels generated from the given numeric extents.

	EXTENTS is a list of the array extents.
	"""

	#print "Extents:",extents

	this = extents[0]	# The first extent
	rest = extents[1:]	# The list of the remaining extents

	labels = []

	if rest == []:
		# We don't have any more extents after this

		for count in range(1,this+1):
			labels.append(`count`)

	else:
		# Expand out the rest

		temp = expand_labels_num(rest)

		# And expand the result of that against "this"

		for count in range(1,this+1):
			for label in temp:
				labels.append(`count` + "," + label)

	return labels

# ----------------------------------------------------------------------
def test_array_sub(a,desc):
	"""Print out the labels for descriptor DESC in the array descriptor A."""

	print "Array descriptor `%s'"%desc

	a.parse(desc)

	a.show()

	count = 0
	while count < 20:
		try:
			label = a.next_item()
			print "   Label %2d: %s"%(count,label)
		except:
			print "   Label %2d: <%s: %s>"%(count,sys.exc_type,sys.exc_value)
			break

		count = count + 1

def test_array():
	"""Simple test code for array descriptors."""

	f = Field_controls("Fred",2,"0000;&")
	a = Array_descriptor("Fred",f)

	test_array_sub(a,"A!B")
	test_array_sub(a,"A*B")
	test_array_sub(a,"A!B*C!D")
	test_array_sub(a,"A!B*C!D\\\\X!Y*Z")
	test_array_sub(a,"A!B*C!D\\\\*X!Y")

