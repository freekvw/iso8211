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

"""pathutils.py - Miscellaneous useful path manipulation functions.

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

	NOTE - this is not specific to ISO 8211, at all, but is needed by the
	iso8211 command, so is provided in the iso8211 package for convenience.
"""

import string
import os
import posix

# I like true and false (integer is NOT boolean)

TRUE  = 1
FALSE = 0


#---------------------------------------------------------------------------------
def expand_path(inpath):
	"""Given a path INPATH which may include "~", ".", "..", etc, expand it out."""

	# Expand out any "~" or "~user" values

	inpath = os.path.expanduser(inpath)

	# Expand out any "$environ" values

	inpath = os.path.expandvars(inpath)

	# Obtain a list of the path elements, separated by "/" (for Unix)

	list = string.split(inpath,os.sep)

	# Trundle along them, composing a final path

	pathlist = []

	# If the first item is "." or "..", we need to work that
	# out wrt the actual current directory

	if list[0] == ".":
		# Get the current path and replace the "." with it
		cwd     = os.getcwd()
		cwdlist = string.split(cwd,os.sep)
		list    = cwdlist + list[1:]

		#print "Starts with . - gives us",list

	elif list[0] == "..":
		# Get the current path, remove the final element,
		# and replace the ".." with it
		cwd     = os.getcwd()
		cwdlist = string.split(cwd,os.sep)
		list    = cwdlist[:-1] + list[1:]

		#print "Starts with .. - gives us",list

	for item in list:
		if item == "":
			# An empty string means that we had the separator by itself
			# - i.e., on Unix we had "/"
			# We need to be careful of a path starting "/" (i.e., relative
			# to root), which will get turned into ["" ""]

			#print "found \"\" - ",

			if len(pathlist) == 0:
				#print "it's the first element"
				pathlist = [""]
			elif len(pathlist) == 1 and pathlist[0] == "":
				#print "it's the second element, after \"\""
				pathlist.append("")
			else:
				#print "ignoring it"
				pass


		elif item == ".":
			# The item was the current directory
			# We don't need to do anything

			#print "found . - ignoring it"
			pass

		elif item == "..":
			# The item was the previous directory
			# We need to `back up' one in our path list
			# (but look out for "/.." which means "/")

			#print "found ..",

			if len(pathlist) > 0:
				#print " - removing previous item"
				del pathlist[-1]

		else:
			# Otherwise, just add the element to the end

			#print "found %s"%item

			pathlist.append(item)

	# So we now have a list of path elements, which should be relative to root
	# - turn it back into a path

	#print "List is:",pathlist

	path = string.join(pathlist,os.sep)

	return path

