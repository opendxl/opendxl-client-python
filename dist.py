# -*- coding: utf-8 -*-
################################################################################
# Copyright (c) 2017 McAfee Inc. - All Rights Reserved.
################################################################################

""" Builds documentation and packages for release """

from __future__ import absolute_import
from __future__ import print_function
import os
import re
import subprocess

# pylint: disable=no-name-in-module, import-error, missing-docstring
from distutils.dir_util import copy_tree, remove_tree
from distutils.file_util import copy_file, move_file
from distutils.core import run_setup
from distutils.archive_util import make_archive

from tempfile import mkstemp
from shutil import move

def replace(file_path, pattern, subst):
    # Create temp file
    handle, abs_path = mkstemp()
    with open(abs_path, "w") as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    os.close(handle)
    # Remove original file
    os.remove(file_path)
    # Move new file
    move(abs_path, file_path)

VERSION = __import__('dxlclient').get_product_version()
RELEASE_NAME = "dxlclient-python-sdk-" + str(VERSION)

DIST_PY_FILE_LOCATION = os.path.dirname(os.path.realpath(__file__))
DIST_DIRECTORY = os.path.join(DIST_PY_FILE_LOCATION, "dist")
DIST_DOCTMP_DIR = os.path.join(DIST_DIRECTORY, "doctmp")
SETUP_PY = os.path.join(DIST_PY_FILE_LOCATION, "setup.py")
DIST_LIB_DIRECTORY = os.path.join(DIST_DIRECTORY, "lib")
DIST_RELEASE_DIR = os.path.join(DIST_DIRECTORY, RELEASE_NAME)

# Remove the dist directory if it exists
if os.path.exists(DIST_DIRECTORY):
    print("\nRemoving dist directory: " + DIST_DIRECTORY + "\n")
    remove_tree(DIST_DIRECTORY, verbose=1)

# Make the dist directory
print("\nMaking dist directory: " + DIST_DIRECTORY + "\n")
os.makedirs(DIST_DIRECTORY)

# Call Sphinx to create API doc
print("\nCalling sphinx-apidoc\n")
subprocess.check_call(["sphinx-apidoc",
                       "--force",
                       "--separate",
                       "--no-toc",
                       "--output-dir=" + DIST_DOCTMP_DIR,
                       os.path.join(DIST_PY_FILE_LOCATION, "dxlclient")])

# Delete test files
for f in os.listdir(DIST_DOCTMP_DIR):
    if re.search("dxlclient.test.*", f):
        os.remove(os.path.join(DIST_DOCTMP_DIR, f))

# Copy files to dist/doctmp
print("\nCopying conf.py, docutils.conf, and sdk directory\n")
copy_file(os.path.join(DIST_PY_FILE_LOCATION, "docs", "conf.py"),
          os.path.join(DIST_DOCTMP_DIR, "conf.py"))
copy_file(os.path.join(DIST_PY_FILE_LOCATION, "docs", "docutils.conf"),
          os.path.join(DIST_DOCTMP_DIR, "docutils.conf"))
copy_tree(os.path.join(DIST_PY_FILE_LOCATION, "docs", "sdk"), DIST_DOCTMP_DIR)

# Call Sphinx build
print("\nCalling sphinx-build\n")
subprocess.check_call(["sphinx-build", "-b", "html", DIST_DOCTMP_DIR, os.path.join(DIST_DIRECTORY, "doc")])

replace(os.path.join(DIST_DIRECTORY, "doc", "_static", "classic.css"), "text-align: justify", "text-align: none")

# Delete .doctrees
remove_tree(os.path.join(os.path.join(DIST_DIRECTORY, "doc"), ".doctrees"), verbose=1)
# Delete .buildinfo
os.remove(os.path.join(os.path.join(DIST_DIRECTORY, "doc"), ".buildinfo"))

# Move README.html to root of dist directory
print("\nMoving README.html\n")
move_file(os.path.join(DIST_DOCTMP_DIR, "README.html"), DIST_DIRECTORY)

# Remove doctmp directory
print("\nDeleting doctmp directory\n")
remove_tree(DIST_DOCTMP_DIR)

# Call setup.py
print("\nRunning setup.py sdist\n")
run_setup(SETUP_PY,
          ["sdist",
           "--format",
           "zip",
           "--dist-dir",
           DIST_LIB_DIRECTORY])

print("\nRunning setup.py bdist_wheel\n")
run_setup(SETUP_PY,
          ["bdist_wheel",
           "--dist-dir",
           DIST_LIB_DIRECTORY,
           "--universal"])

# cp -rf sample dist
print("\nCopying sample in to dist directory\n")
copy_tree(os.path.join(DIST_PY_FILE_LOCATION, "examples"), os.path.join(DIST_DIRECTORY, "sample"))

# Copy everything in to release dir
print("\nCopying dist to " + DIST_RELEASE_DIR + "\n")
copy_tree(DIST_DIRECTORY, DIST_RELEASE_DIR)

# rm -rf build
print("\nRemoving build directory\n")
remove_tree(os.path.join(DIST_PY_FILE_LOCATION, "build"))

# rm -rf dxlclient.egg-info
print("\nRemoving dxlclient.egg-info\n")
remove_tree(os.path.join(DIST_PY_FILE_LOCATION, "dxlclient.egg-info"))

# Make dist zip
print("\nMaking dist zip\n")
make_archive(DIST_RELEASE_DIR, "zip", DIST_DIRECTORY, RELEASE_NAME)

print("\nRemoving " + DIST_RELEASE_DIR + "\n")
remove_tree(DIST_RELEASE_DIR)

print("\nFinished")
