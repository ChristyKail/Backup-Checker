import sys
import os
import re
from datetime import datetime


class BackupChecker:

    def __init__(self, root_folder: str, folders_to_search=None, manager=None):

        # assume we want to search Camera_Media and Sound_Media if it's not defined
        if folders_to_search is None:
            folders_to_search = ["Camera_Media", "Sound_Media"]

        # set basic class variables
        self.manager = manager
        self.root_folder = root_folder
        self.folders_to_search = folders_to_search
        self.logger = []
        self.failed_check = False

        self.missing_primary = []
        self.missing_secondary = []

        self.mismatch_primary = []
        self.mismatch_secondary = []

        # search for the backup indexes, and the source indexes
        self.backup_mhl_list_primary, self.backup_mhl_list_secondary = self.get_backup_indexes(root_folder)
        self.source_mhl_list = self.get_source_indexes(root_folder)

        # parse the found MHLs into
        self.backup_dict_primary = self.add_mhls_to_dict(self.backup_mhl_list_primary)
        self.backup_dict_secondary = self.add_mhls_to_dict(self.backup_mhl_list_secondary)
        self.source_dict = self.add_mhls_to_dict(self.source_mhl_list)

        self.basic_checks()

    def basic_checks(self):

        """check basic things, such as whether there are fewer files in the backup than the source """

        check_passed = True

        source_file_count = len(self.source_dict)

        if self.backup_dict_primary:
            if (len(self.source_dict) + len(self.source_mhl_list)) > len(self.backup_dict_primary):
                self.log("More files in source than primary backup!", "fail")
                check_passed = False
        else:
            self.log("No primary backups to check!", "warning")

        if self.backup_dict_secondary:
            if (len(self.source_dict) + len(self.source_mhl_list)) > len(self.backup_dict_secondary):
                self.log("More files in source than secondary backup!", "fail")
                fcheck_passed = False
        else:
            self.log("No secondary backups to check!", "warning")

        print()
        self.log(f"Files in source: {source_file_count} - {source_file_count + len(self.source_mhl_list)} including "
                 f"MHLs!")
        self.log(f"Files in primary backup: {len(self.backup_dict_primary)}")
        self.log(f"Files in secondary backup: {len(self.backup_dict_secondary)}")

        if check_passed:
            self.log(f"Basic checks complete", "good")
        else:
            self.log(f"Basic checks complete", "fail")

        return check_passed

    def check_indexes(self):
        """perform checks on the three dicts created in init"""

        check_passed = True

        # check the source against the primary, if available
        if len(self.backup_dict_primary):

            self.missing_primary, self.mismatch_primary = compare_dicts(self.backup_dict_primary, self.source_dict)

            if self.missing_primary:
                self.log("The following files are missing on primary backups:", 'fail')
                self.log("\n".join(self.missing_primary), 'fail')
                check_passed = False
            if self.mismatch_primary:
                self.log("The following files have the wrong files size on primary backups:", 'fail')
                self.log("\n".join(self.mismatch_primary), 'fail')
                check_passed = False
        else:
            self.log("No primary backups were checked", 'warning')

        # check the source against the secondary, if available
        if len(self.backup_dict_secondary):

            self.missing_secondary, self.mismatch_secondary = compare_dicts(self.backup_dict_secondary,
                                                                            self.source_dict)

            if self.missing_secondary:
                self.log("The following files are missing on secondary backups:", 'fail')
                self.log("\n".join(self.missing_secondary), 'fila')
                check_passed = False
            if self.mismatch_secondary:
                self.log("The following files have the wrong files size on primary backups:", 'fail')
                self.log("\n".join(self.mismatch_secondary), 'fail')
                check_passed = False
        else:
            self.log("No secondary backups were checked")

        if check_passed:
            self.log(f"Index checks complete", "good")
        else:
            self.log(f"Index checks complete", "fail")

        return check_passed

    def check_files(self):

        """checks actual source files against dictionary"""

        files_in_source_storage = []

        for folder_to_search in self.folders_to_search:

            for root, dirs, files in os.walk(os.path.join(self.root_folder, folder_to_search)):

                for file in files:

                    file = trim_path_relative(os.path.join(root, file), self.folders_to_search)

                    if file.endswith(".DS_Store"):
                        print(f'Skipped {file}')

                    else:
                        files_in_source_storage.append(file)

        print(f'Files in source storage {len(files_in_source_storage)}, files in primary backup {len(self.backup_dict_primary)}')

        if len(self.backup_dict_primary):

            for file in files_in_source_storage:

                if file not in self.backup_dict_primary:
                    self.log(f"{file} has not been indexed in primary backup!", "fail")

        if len(self.backup_dict_secondary):

            for file in files_in_source_storage:

                if file not in self.backup_dict_secondary:
                    self.log(f"{file} has not been indexed in secondary backup!", "fail")

        self.log(f"File checks complete", "good")

    def add_mhls_to_dict(self, mhl_list):

        print()

        dictionary = {}

        for mhl in mhl_list:
            self.log(f'Loading MHL {os.path.basename(mhl)} - this might take a second...')
            dictionary.update(mhl_to_dict_fast(mhl))

        return dictionary

    def get_backup_indexes(self, root_folder):

        # get a list of MHLs in the root folder - these are the backup indexes
        self.log(f"Checking folder {root_folder}")
        backup_mhl_list = [os.path.join(root_folder, file) for file in os.listdir(root_folder) if
                           file.endswith(".mhl")]
        # if no backup MHLs found, raise an error
        if not backup_mhl_list:
            self.log("No backup indexes were found")
            raise ValueError("No backup indexes were found")

        # divide the MHLs into primary  and secondary backups
        backup_mhl_list_primary, backup_mhl_list_secondary = separate_primary_and_secondary(backup_mhl_list)

        # log the source indexes
        self.log(
            f'{len(backup_mhl_list_primary)} primary backups found: {", ".join([os.path.basename(f) for f in backup_mhl_list_primary])}')

        self.log(
            f'{len(backup_mhl_list_secondary)} secondary backups found: {", ".join([os.path.basename(f) for f in backup_mhl_list_secondary])}')

        return backup_mhl_list_primary, backup_mhl_list_secondary

    def get_source_indexes(self, root_folder):

        source_mhl_list = []

        for folder_to_search in self.folders_to_search:

            if not os.path.exists(os.path.join(root_folder, folder_to_search)):
                self.log(f'{folder_to_search} not found', 'warning')

            else:
                for root, dirs, files in os.walk(os.path.join(root_folder, folder_to_search)):
                    for file in files:
                        if str(file).endswith("mhl"):
                            source_mhl_list.append(os.path.join(root, file))

        # check we found some source indexes, otherwise return
        if source_mhl_list:

            self.log(f'{len(source_mhl_list)} sources found')
            for mhl in source_mhl_list:
                self.log(f'Source: {os.path.basename(mhl)}')

        else:
            self.log("No source indexes found")
            raise ValueError("No source indexes found")

        return source_mhl_list

    def log(self, string: str, log_type="normal"):

        """saves a log entry"""

        if self.manager:
            self.manager.log(string, log_type)
            self.manager.update()

        self.logger.append(f'[{log_type.upper()}] {string}')

        if log_type == "normal":
            print(string)
            pass

        elif log_type == "good":
            print(BColors.OKGREEN + string + BColors.ENDC)
            pass

        elif log_type == "warning":
            print(BColors.WARNING + string + BColors.ENDC)
            pass

        elif log_type == "fail":
            print(BColors.FAIL + string + BColors.ENDC)
            self.failed_check = True

        else:
            self.failed_check = True
            print(BColors.FAIL + string + BColors.ENDC)
            raise ValueError("Unknown log type!")

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

        self.log("Report saved to disk", 'good')

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

            file_path = trim_path_relative(file_path, ['Camera_Media', 'Sound_Media'])

            if file_path.startswith("/Volumes/"):
                if not volumes_string:
                    volumes_string = re.findall(r'^/Volumes/\w+', file_path)[0]

                file_path = file_path.replace(volumes_string, "", 1)

            # add this file to the dictionary
            dict_of_files_and_sizes[file_path] = file_size

    return dict_of_files_and_sizes


def remove_xml_tag(string: str, tag_name: str):
    return string.replace(f'<{tag_name}>', "").replace(f'</{tag_name}>', "").strip()


def trim_path_relative(file_path: str, possible_roots: list):

    for possible_root in possible_roots:

        if possible_root in file_path:
            file_path = file_path.split(possible_root)[1]
            break

    return file_path


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
                folder_checker = BackupChecker(folder)

            except ValueError as error:
                print(folder + str(error))
                continue

            folder_checker.check_indexes()
            folder_checker.write_report()