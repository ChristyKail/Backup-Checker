import sys
import os
import re
from datetime import datetime


class IndexChecker:

    def __init__(self, root_folder: str, folders_to_search=None, manager=None):

        # assume we want to search Camera_Media and Sound_Media if it's not defined
        if folders_to_search is None:
            folders_to_search = ["Camera_Media", "Sound_Media"]

        # set basic class variables

        self.manager = manager
        self.root_folder = root_folder
        self.logger = []
        self.failed_check = False

        self.missing_primary = []
        self.missing_secondary = []

        self.mismatch_primary = []
        self.mismatch_secondary = []

        ######################################################################
        # get a list of MHLs in the root folder - these are the backup indexes
        self.log(f"Checking folder {root_folder}", False)
        backup_mhl_list = [os.path.join(root_folder, file) for file in os.listdir(root_folder) if
                           file.endswith(".mhl")]
        # if no backup MHLs found, raise an error
        if not backup_mhl_list:
            self.log("No backup indexes were found")
            raise ValueError("No backup indexes were found")

        # divide the MHLs into primary  and secondary backups
        self.backup_mhl_list_primary, self.backup_mhl_list_secondary = separate_primary_and_secondary(backup_mhl_list)

        # log the source indexes
        self.log(
            f'{len(self.backup_mhl_list_primary)} primary backups found: {", ".join([os.path.basename(f) for f in self.backup_mhl_list_primary])}',
            False)

        self.log(
            f'{len(self.backup_mhl_list_secondary)} secondary backups found: {", ".join([os.path.basename(f) for f in self.backup_mhl_list_secondary])}',
            False)

        print()
        ########################################################################
        # get a list of MHLs in the media folders - these are the source indexes
        self.source_mhl_list = []
        for folder_to_search in folders_to_search:
            for root, dirs, files in os.walk(os.path.join(root_folder, folder_to_search)):
                for file in files:
                    if file.endswith(".mhl"):
                        self.source_mhl_list.append(os.path.join(root, file))

        # check we found some source indexes, otherwise return
        if self.source_mhl_list:

            self.log(f'{len(self.source_mhl_list)} sources found', False)
            for mhl in self.source_mhl_list:
                self.log(f'Source: {os.path.basename(mhl)}', False)

        else:
            self.log("No source indexes found")
            raise ValueError("No source indexes found")

        print()
        ##################################################
        # make three dicts, primary, secondary, and source
        self.backup_dict_primary = {}
        for mhl in self.backup_mhl_list_primary:
            self.backup_dict_primary.update(mhl_to_dict_fast(mhl))
        backup_primary_file_count = len(self.backup_dict_primary)

        self.backup_dict_secondary = {}
        for mhl in self.backup_mhl_list_secondary:
            self.backup_dict_secondary.update(mhl_to_dict_fast(mhl))
        backup_secondary_file_count = len(self.backup_dict_secondary)

        self.source_dict = {}
        for mhl in self.source_mhl_list:
            self.source_dict.update(mhl_to_dict_fast(mhl))
        source_file_count = len(self.source_dict)

        if len(self.source_dict) + len(self.source_mhl_list) > len(self.backup_dict_primary):
            self.log("More files in source than primary backup!", True)

        if len(self.source_dict) + len(self.source_mhl_list) > len(self.backup_dict_secondary):
            self.log("More files in source than secondary backup!", True)

        print()
        self.log(f"Files in source: {source_file_count} - {source_file_count + len(self.source_mhl_list)} including "
                 f"MHLs!", False)
        self.log(f"Files in primary backup: {backup_primary_file_count}", False)
        self.log(f"Files in secondary backup: {backup_secondary_file_count}", False)
        print()

    def check_indexes(self):
        """perform checks on the three dicts created in init"""

        # check the source against the primary, if available
        if len(self.backup_dict_primary):

            self.missing_primary, self.mismatch_primary = compare_dicts(self.backup_dict_primary, self.source_dict)

            if self.missing_primary:
                self.log("The following files are missing on primary backups:", True)
                self.log("\n".join(self.missing_primary), True)
            if self.mismatch_primary:
                self.log("The following files have the wrong files size on primary backups:", True)
                self.log("\n".join(self.mismatch_primary), True)
        else:
            self.log("No primary backups were checked")

        # check the source against the secondary, if available
        if len(self.backup_dict_secondary):

            self.missing_secondary, self.mismatch_secondary = compare_dicts(self.backup_dict_secondary,
                                                                            self.source_dict)

            if self.missing_secondary:
                self.log("The following files are missing on secondary backups:", True)
                self.log("\n".join(self.missing_secondary), True)
            if self.mismatch_secondary:
                self.log("The following files have the wrong files size on primary backups:", True)
                self.log("\n".join(self.mismatch_secondary), True)
        else:
            self.log("No secondary backups were checked")

        self.log("All MHLs checked", False)

    def log(self, string: str, fail=True):
        """saves a log entry"""

        if self.manager:
            self.manager.log(string, fail)
            self.manager.update()

        if fail:
            self.failed_check = True
            self.logger.append(f'[FAIL] {string}')
            print(BColors.FAIL + string + BColors.ENDC)

        else:
            self.logger.append(f'{string}')
            print(string)

    def write_report(self):
        """writes out a summary of the job to the root folder"""

        if self.failed_check:
            result = "failed"
        else:
            result = "passed"

        report_name = f'{os.path.basename(self.root_folder)} - {result}.txt'

        with open(os.path.join(self.root_folder, report_name), "w") as file_handler:

            file_handler.write(f'{datetime.now()}\n')
            file_handler.write("\n")

            # list all the MHLs
            file_handler.write(f'Primary Backups: {len(self.backup_mhl_list_primary)}\n')
            for line in self.backup_mhl_list_primary:
                file_handler.write(f"\t{os.path.basename(line)}\n")

            file_handler.write(f'Secondary Backups: {len(self.backup_mhl_list_secondary)}\n')
            for line in self.backup_mhl_list_secondary:
                file_handler.write(f"\t{os.path.basename(line)}\n")

            file_handler.write(f'Sources: {len(self.source_mhl_list)}\n')
            for line in self.source_mhl_list:
                file_handler.write(f"\t{os.path.basename(line)}\n")

            file_handler.write("\n")

            # count all the files
            file_handler.write(f'Files in primary backup: {len(self.backup_dict_primary)}\n')
            file_handler.write(f'Files in secondary backup: {len(self.backup_dict_secondary)}\n')
            file_handler.write(f'Files in source: {len(self.source_dict)}\n')

            file_handler.write("\n")

            # list all the missing primary files
            if len(self.backup_mhl_list_primary):

                file_handler.write(f'Files missing from primary backup: {len(self.missing_primary)}\n')
                for line in self.missing_primary:
                    file_handler.write(f"\t{line}\n")

                file_handler.write(f'Files with wrong file size on primary backup: {len(self.mismatch_primary)}\n')
                for line in self.mismatch_primary:
                    file_handler.write(f"\t{line}\n")

            else:
                file_handler.write(f"No primary backups checked\n")
            file_handler.write("\n")

            # list all the missing secondary files
            if len(self.backup_mhl_list_secondary):
                file_handler.write(f'Files missing from secondary backup: {len(self.missing_secondary)}\n')
                for line in self.missing_secondary:
                    file_handler.write(f"\t{line}\n")

                file_handler.write(f'Files with wrong file size on secondary backup: {len(self.mismatch_secondary)}\n')
                for line in self.mismatch_secondary:
                    file_handler.write(f"\t{line}\n")
            else:
                file_handler.write(f"No secondary backups checked\n")
            file_handler.write("\n")

        self.log("Report saved to disk", False)

    def write_out_log(self, directory=""):

        if not directory:
            directory = self.root_folder

        backups_string = " ".join(
            os.path.basename(f)[:6] for f in self.backup_mhl_list_primary + self.backup_mhl_list_secondary)

        if self.failed_check:
            result = "failed"
        else:
            result = "passed"

        file_name = os.path.join(directory, f'MHL check - {backups_string} - {result}.txt')

        with open(file_name, 'w') as file_handler:

            for line in self.logger:
                file_handler.write(line + "\n")


class BColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def separate_primary_and_secondary(mhl_list):
    primary = [f for f in mhl_list if (int(f[-5]) % 2 != 0)]
    secondary = [f for f in mhl_list if (int(f[-5]) % 2 == 0)]

    return primary, secondary


def compare_dicts(backup_dict, source_dict):
    missing = []
    mismatch = []

    for key, value in source_dict.items():

        if key not in backup_dict.keys():
            missing.append(key)

        elif source_dict[key] != backup_dict[key]:
            mismatch.append(key)

    return missing, mismatch


def mhl_to_dict_fast(mhl_file_path: str):
    dict_of_files_and_sizes = {}

    print(f'Loading MHL {os.path.basename(mhl_file_path)} - this might take a second...')

    with open(mhl_file_path, "r") as file_handler:
        contents = file_handler.readlines()

    add_roll_to_path = ""
    volumes_string = ''

    for index, line in enumerate(contents):

        line = line.strip()

        # detect whether this is a YoYotta MHL
        if line.startswith("<username>"):

            if "YoYotta" not in line:
                # get the roll folder name
                add_roll_to_path = os.path.basename(os.path.dirname(mhl_file_path))
            else:
                add_roll_to_path = ""

        elif line.startswith("<file>"):

            # remove the tags from the lines and save them to variables
            file_path = remove_xml_tag(line, "file")
            file_size = remove_xml_tag(contents[index + 1], "size")

            # add the roll folder name if needed
            if add_roll_to_path:
                file_path = os.path.sep + os.path.join(add_roll_to_path, file_path)

            # head trim the path down to below Camera_Media or Sound_Media
            if "Camera_Media" in file_path:
                file_path = file_path.split("Camera_Media")[1]
            elif "Sound_Media" in file_path:
                file_path = file_path.split("Sound_Media")[1]
            elif file_path.startswith("/Volumes/"):
                if not volumes_string:
                    volumes_string = re.findall(r'^/Volumes/\w+', file_path)[0]

                file_path = file_path.replace(volumes_string, "", 1)

            # add this file to the dictionary
            dict_of_files_and_sizes[file_path] = file_size

    return dict_of_files_and_sizes


def remove_xml_tag(string: str, tag_name: str):
    return string.replace(f'<{tag_name}>', "").replace(f'</{tag_name}>', "").strip()


if __name__ == "__main__":

    folders = sys.argv[1:]

    if len(folders) == 0:
        folders = [input("Drop day folder here...")]

    for folder in folders:

        folder = folder.replace("\\", "").strip()

        if not os.path.isdir(folder):
            print(f'{folder} is not a valid folder')
            continue

        else:
            try:
                folder_checker = IndexChecker(folder)

            except ValueError as error:

                print(folder + str(error))
                continue

            folder_checker.check_indexes()
            folder_checker.write_report()
