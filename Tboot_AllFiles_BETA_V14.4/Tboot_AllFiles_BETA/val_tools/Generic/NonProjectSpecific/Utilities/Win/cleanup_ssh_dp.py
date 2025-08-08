#!/usr/bin/env python2.6
#############################################################################################################
# This script zips & copies all the test run artifacts to a given location (the so called cleanup script).  #
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

path.append('C:\Program Files\Intel\Origami\ClientScripts')
from cleanup_utils import CleanUpUtils, Version as cleanup_utils_version
from misc_utils import Constants, ZipUtils, Version as misc_utils_version

import posixpath

#verify that the version of all the components is the same
#assert misc_utils_version.__version__ == __version__, ("Version Mismatch - Current Script: {0} , misc_utils: {1}".format(__version__, misc_utils_version.__version__))
#assert cleanup_utils_version.__version__ == __version__, ("Version Mismatch - Current Script: {0} , cleanup_utils: {1}".format(__version__, cleanup_utils_version.__version__))

def clean_up(title):
    # Adjusting for having subdirectories enabled
    chdir("..")

    # Zipping all the artifacts.
    cwd = getcwd()
    zip_file_name = CleanUpUtils.get_zip_file_name()
    zip_file_path = abspath(join(cwd, '..', zip_file_name))
    ZipUtils.zip_directory(zip_file_path, cwd)

    # Moving the zip file to its final location taking into account possible multiple re-runs of the same test !
    scp_server = getenv(Constants.HEXA_SCP_SERVER)
    if scp_server is None:
        stderr.write('Environment variable {0} was not set !'.format(Constants.HEXA_SCP_SERVER))
        exit(42)
    dest_folder = posixpath.join(getenv(Constants.HEXA_TEST_DATA), getenv(Constants.HEXA_REMOTE_SUBDIR), title)
    dest_folder = posixpath.join("/proj/TestData/", getenv(Constants.HEXA_REMOTE_SUBDIR), title) # SESMITH Modification
    dest_file = posixpath.join(dest_folder, zip_file_name)
    check_call(['ssh', '-o', 'batchMode=yes', scp_server, '/usr/local/UVAT/Agent/bin/MakeLogDir {0} {1}'.format(dest_folder, zip_file_name)])
    check_call(['ssh', '-o', 'batchMode=yes', scp_server, 'chmod -R 0777 {0}'.format(dest_folder)])
    
	#[merlikhm]
	#Bug ID: 2161
	#Changed the way scp script is invoked - instead of passing the full path to scp
	#we now pass only the file name, and set the cwd to the folder containing the file
	#we had to to this since scp got confused with the semicolon in the path, in the c:\ portion of the path
	
	#previous version - below
	#check_call(['scp', '-q', '-B', zip_file_path, '{0}:{1}'.format(scp_server, dest_folder)])
	
	#new version - below
	#determine the folder path of the zip file
    folder_containing_zips = dirname(zip_file_path)
	
	#call scp with the file name only and set the working directory to be the folder containing the zip files
    check_call(['scp', '-q', '-B', zip_file_name, '{0}:{1}'.format(scp_server, dest_folder)], cwd= folder_containing_zips)
    check_call(['ssh', '-o', 'batchMode=yes', scp_server, 'chmod -R 0777 {0}'.format(dest_folder)])

    # Deleting or sustaining the temp artifacts.
    v = getenv(Constants.HEXA_DO_NOT_DELETE_LOGS)
    delete = not int(v) if v is not None else 1
    delete = 1
    if delete:
        chdir(gettempdir())
        # ignore_errors=True --> what can be deleted, will be deleted, don't want to fail the script just b/c delete errors
        rmtree(cwd, ignore_errors=True)


def main():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('--title', dest='title', default='')
    options, args = parser.parse_args()
    clean_up(options.title)

if __name__ == '__main__':
    main()
