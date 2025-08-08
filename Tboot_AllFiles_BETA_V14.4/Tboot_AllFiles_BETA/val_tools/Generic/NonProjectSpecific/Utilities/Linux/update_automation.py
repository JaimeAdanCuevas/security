#!/usr/bin/env python
#############################################################################################################
# This script rsync's automation files to the appropriate location                                          #
# The given location assumed to be on a SCP server --> the handling in this script assume valid SSH & SCP   #
# configuration to be present !.                                                                            #
# Usage : <script_path> [--title]                                                                           #
#############################################################################################################
__author__ = 'sesmith'
__version__ = '1.17'

from sys import stderr, path
from os import getcwd, getenv, chdir
from os.path import join, abspath, dirname
from shutil import rmtree
from optparse import OptionParser
from tempfile import gettempdir
from subprocess import call, check_call

path.append('/usr/local/Origami/ClientScripts/')
from cleanup_utils import CleanUpUtils, Version as cleanup_utils_version
from misc_utils import Constants, ZipUtils, Version as misc_utils_version

import posixpath

#verify that the version of all the components is the same
#assert misc_utils_version.__version__ == __version__, ("Version Mismatch - Current Script: {0} , misc_utils: {1}".format(__version__, misc_utils_version.__version__))
#assert cleanup_utils_version.__version__ == __version__, ("Version Mismatch - Current Script: {0} , cleanup_utils: {1}".format(__version__, cleanup_utils_version.__version__))

def automation_update(title):
    # Moving the zip file to its final location taking into account possible multiple re-runs of the same test !
    scp_server = getenv(Constants.HEXA_SCP_SERVER)
    if scp_server is None:
        stderr.write('Environment variable {0} was not set !'.format(Constants.HEXA_SCP_SERVER))
        exit(42)
	projectInfo = getenv('Project')
	if projectInfo is None:
	    stderr.write('Environment variable {0} was not set !'.format('Project')
		exit(43)
    
    #call rsync 
    attempts = 0
    while (attempts < 3):
        results = call(["rsync -rtpvz --ignore-errors --exclude=.svn -e 'ssh -o batchMode=yes' {0}:/lab/{1}/Origami/Current/ClientScripts /usr/local/Origami/".format(scp_server, projectInfo)], shell=True)
        if (results > 0):
            attempts = attempts + 1
        else:
            attempts = 10
    if (attempts == 3):
        exit (results) # We failed to rsync properly
    if (results == 0):
        exit (0) # We succeeded
        
def main():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('--title', dest='title', default='')
    options, args = parser.parse_args()
    automation_update(options.title)

if __name__ == '__main__':
    main()
