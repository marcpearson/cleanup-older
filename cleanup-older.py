#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import os
import time
import datetime
import argparse


class Cleanup_older:

    def __init__(self):

        # List of files to be erase
        self.files = []

        # List of symbolic links to be erase
        self.symbolic_links = []

        # List of folder to be erase
        self.folders = []

        # List of subfolders to skip
        self.skipped = []

        # Do it recursive
        self.recursive = False

        # Dry run or not
        self.delete = False

        # Delete empty folder
        self.delete_empty_folder = False

        # Delete symbolic link
        self.delete_symbolic_link = False

        # Possible recovered space
        self.recovered_space = 0

        # Error_msg list set to none for default
        self.error_msg = None

        # Arguments passed validating
        if not self.validate_arguments():
            print("\n%s\n" % (self.error_msg))
            self.show_usage()
        else:
            self.crawl_directory(self.folder_path)

            if self.delete:
                self.do_deletion()
            else:
                self.show_content()

            if self.skipped:
                print("These has been skipped:")

                for f in self.skipped:
                    print(f)

                print("\n")

    def validate_arguments(self):

        self.parser = argparse.ArgumentParser(
            prog='Cleanup_older',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''Examples:

cleanup_older /path/to/folder 2014-09-30 -r

        Display files older than 2014-09-30 in path/to/folder and subfolders \n \n

cleanup_older path/to/folder 2014-09-30 -r --delete

        Delete files older than 2014-09-30 in path/to/folder and subfolders \n \n

cleanup_older path/to/folder 2014-09-30 -r -d -x mysubfolder

        Delete files older than 2014-09-30 in path/to/folder and subfolders but skip mysubfolder \n \n

cleanup_older path/to/folder 2014-09-30 -r -e -s -d

        Delete files older than 2014-09-30 in path/to/folder and subfolders and delete empty subfolders and symbolic links
        '''
        )

        self.parser.add_argument('folder', help='full path to folder')
        self.parser.add_argument('date', help='older than date of type YYYY-MM-DD')
        self.parser.add_argument('-d', '--delete', help="proceed with deletion", action='store_true')
        self.parser.add_argument('-r', '--recursive', help='process folder recursively', action='store_true')
        self.parser.add_argument('-e', '--delete-empty-folder', help='delete empty folder', action='store_true')
        self.parser.add_argument('-s', '--delete-symbolic-link', help='delete symbolic link', action='store_true')
        self.parser.add_argument('-x', '--skip', nargs='*', help='subfolder, file or symbolic link to skip', metavar="name")

        args = self.parser.parse_args()

        # set variables from parsed arguments
        self.delete = args.delete
        self.recursive = args.recursive
        self.skipped = args.skip
        self.delete_empty_folder = args.delete_empty_folder
        self.delete_symbolic_link = args.delete_symbolic_link

        # Validating arguments
        try:
            self.date = args.date.split('-')
            newDate = datetime.datetime(int(self.date[0]), int(self.date[1]), int(self.date[2]))
        except ValueError:
            self.error_msg = "ERROR:  Second argument must be a date of type YYYY-MM-DD"
            return False

        # Check if the first argument is a valid folder path
        if not os.path.isdir(args.folder):
            self.error_msg = "ERROR: The folder \"" + sys.argv[1] + "\" didn't exists"
            return False
        else:
            self.folder_path = args.folder

        return True

    def crawl_directory(self, path):
        # Get folders and files

        maxdate = time.mktime(time.struct_time((int(self.date[0]), int(self.date[1]), int(self.date[2]), 0, 0, 0, 0, 0, 0), {}))

        file_counter = 0  # Store number of files in the current directory
        file_to_delete = 0  # Store number of files that will be deleted from the current directory
        try:
            for f in os.listdir(path):

                # Skip f if is set in skipped
                if self.skipped and f in self.skipped:
                    continue

                # Building full path to file (or folder)
                current_path = os.path.join(path, f)

                if os.path.isdir(current_path):
                    # it's a directory
                    if self.recursive:
                        self.crawl_directory(current_path)

                elif os.path.islink(current_path):
                    # It's a symbolic link
                    if not self.delete_symbolic_link:
                        continue
                    else:
                        file_counter += 1
                        file_to_delete += 1
                        # Add to list of files to be deleted
                        self.symbolic_links.append([current_path, " (Symbolic link)"])
                else:
                    # It's a file

                    # Update counter
                    file_counter += 1

                    # Get last modification time in tuple
                    struct_stamp = time.localtime(os.path.getmtime(current_path))
                    # Convert it to unix time stamp from epoch
                    unixtime_stamp = time.mktime(struct_stamp)
                    # Formatting for readable display
                    last_modification = time.strftime("%d-%m-%Y", struct_stamp)

                    # Check is older then date pass in argument
                    if unixtime_stamp <= maxdate:
                        # Update counter
                        file_to_delete += 1

                        # Get file size
                        fsize = os.path.getsize(current_path)
                        self.recovered_space += fsize

                        # Add to list of files to be deleted
                        self.files.append([current_path, "(" + last_modification + " :: " + str(fsize / 1024) + " KB)"])

            if file_to_delete == file_counter and path != self.folder_path:
                self.folders.append(path)
        except OSError as e:
            if e.errno == 13:
                print("Can't access the specified folder, permission denied!")

            sys.exit()

    def show_content(self):
        # Dump files list to be deleted
        print("Files to be deleted\n")
        for f in self.files:
            print(' '.join(f))

        if self.delete_symbolic_link:
            print("\nSymbolic links to be deleted\n")
            for f in self.symbolic_links:
                print(' '.join(f))

        if self.delete_empty_folder:
            print("\nFolders to be deleted\n")
            for f in self.folders:
                print(f)

        print("\n%d file(s) will be deleted" % (len(self.files)))

        if self.delete_symbolic_link:
            print("%d symbolic link(s) will be deleted" % (len(self.symbolic_links)))

        if self.delete_empty_folder:
            print("%d folder(s) will be deleted" % (len(self.folders)))

        print("Approximately %0.1f MB will be recovered\n\n" % (float(self.recovered_space / 1048576.0)))

    def delete_empty_folders(self):
        # Delete all empty folder
        total = 0
        print("\n\nDeleting empty folders, please wait ...\n")

        for d in self.folders:
            try:
                print("Deleting folder %s ..." % (d), end=' ')
                os.rmdir(d)
                total += 1
                print("OK")
            except OSError as e:
                if e.errno == 66:
                    print("folder not empty, can't delete")

        return total

    def delete_symbolic_links(self):
        # Delete symbolic links
        total = 0
        print("\n\nDeleting symbolic links, please wait ...\n")

        for s in self.symbolic_links:
            print("Deleting symbolic link %s ... " % (s[0]), end=' ')
            os.remove(s[0])
            total += 1
            print("OK")

        return total

    def do_deletion(self):
        # Delete files to old
        total = 0
        total_deleted_folders = 0
        total_deleted_symbolic_links = 0

        print("Deleting files, please wait ...\n")

        for f in self.files:
            print("Deleting file %s ... " % (f[0]), end=' ')
            os.remove(f[0])
            total += 1
            print("OK")

        # Deleting symbolic links
        if self.delete_symbolic_link:
            total_deleted_symbolic_links = self.delete_symbolic_links()

        # Deleting empty folders
        if self.delete_empty_folder:
            total_deleted_folders = self.delete_empty_folders()

        print("\n%s file(s), %s symbolic link(s) and %s folder(s) has been deleted\n\n" % (total, total_deleted_symbolic_links, total_deleted_folders))

Cleanup_older()
