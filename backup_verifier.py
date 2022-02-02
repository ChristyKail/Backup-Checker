import datetime
import os
import re
from datetime import datetime


class BackupVerifier:

    def __init__(self, root_folder: str, folders_to_search=None, manager=None):
        if folders_to_search is None:
            folders_to_search = ["Camera_Media", "Sound_Media"]

        self.manager = manager
        self.root_folder = root_folder
        self.folders_to_search = folders_to_search
        self.logger = []
        self.backups = []

        # get files list

        source_files = self.get_source_files(root_folder, folders_to_search)

        # get source index
        self.source_mhl_list = self.get_source_indexes(root_folder)
        source_index = self.list_of_mhls_to_dict(self.source_mhl_list)

        # get backup MHLs, group them,  and make a backup object from each group
        backup_mhl_list = self.get_backup_indexes(root_folder)
        backup_mhl_groups = separate_primary_and_secondary(backup_mhl_list)

        for ii, group_list in enumerate(backup_mhl_groups):
            print(group_list)

            group_dict = self.list_of_mhls_to_dict(group_list)

            mhls = [trim_path_relative(m, self.folders_to_search) for m in self.source_mhl_list]
            print(mhls)
            b = Backup(os.path.basename(group_list[0]), group_dict, source_index, source_files, mhls)
            self.backups.append(b)

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

    def get_backup_indexes(self, root_folder):
        self.log(f"Checking folder {root_folder}")
        backup_mhl_list = [os.path.join(root_folder, file) for file in os.listdir(root_folder) if
                           file.endswith(".mhl")]

        return backup_mhl_list

    def get_source_files(self, root_folder, folders_to_search):

        file_list = []

        for folder_to_search in folders_to_search:
            for root, dirs, files in os.walk(os.path.join(root_folder, folder_to_search)):
                for file in files:

                    file = trim_path_relative(os.path.join(str(root), str(file)), folders_to_search)

                    if file.endswith(".DS_Store"):
                        print(f'Skipped {file}')

                    else:
                        file_list.append(file)

        return file_list

    def list_of_mhls_to_dict(self, mhl_list: []):
        dictionary = {}

        for mhl in mhl_list:
            self.log(f'Loading MHL {os.path.basename(mhl)} - this might take a second...')
            dictionary.update(mhl_to_dict_fast(mhl))

        return dictionary

    def log(self, log_message: str, log_type="normal"):
        print(f'[{log_type}] {log_message}')
        self.logger.append(f'[{log_type}] {log_message}')
        if self.manager:
            self.manager.log(log_message, log_type)

    def do_verification_but_better(self):

        for backup in self.backups:
            print()
            print(backup.backup_name)

            backup.quick_check()

            backup.source_i_vs_backup_i()
            backup.source_f_vs_backup_i()

            backup.source_f_vs_source_i()
            backup.source_i_vs_source_f()

            backup.checks_run = True

    def write_report(self):

        passed = True

        # report and log number of MHLs
        mhl_info = f'Backups checked: {len(self.backups)}'
        self.manager.log(mhl_info, "normal")
        if len(self.backups) < 2:
            self.manager.log("Only 1 backup was verified", "warning")

        report_string = mhl_info + '\n'

        for backup in self.backups:
            report_string = report_string + '\t' + backup.backup_name + '\n'
            self.manager.log("\t" + backup.backup_name, "normal")

        # report and log each backup report
        for backup in self.backups:
            this_report, this_result = backup.report(self)
            report_string = report_string + this_report + "\n\n"
            if not this_result:
                passed = False

            if self.manager:
                if passed:
                    self.manager.log(this_report, 'good')
                else:
                    self.manager.log(this_report, 'fail')

        now = datetime.now()
        current_time = now.strftime("%Y%m%d_%H%M%S")

        if passed:
            report_name = f'{os.path.basename(self.root_folder)} PASSED {current_time}.txt'
        else:
            report_name = f'{os.path.basename(self.root_folder)} FAILED {current_time}.txt'

        report_path = os.path.join(self.root_folder, report_name)

        with open(report_path, 'w') as file_handler:

            file_handler.write(report_string)

        return report_string, passed


class Backup:

    def __init__(self, name: str, backup_index: {}, source_index: {}, source_files: [], source_mhls: []):

        self.backup_name = name

        self.checks_run = False
        self.check_passed = True

        self.backup_index = backup_index
        self.source_index = source_index
        self.source_files = source_files

        self.source_mhls = source_mhls

        self.source_i_missing_in_backup_i = []
        self.source_i_wrong_in_backup_i = []
        self.source_f_missing_in_backup_i = []

        self.source_f_missing_in_source_i = []
        self.source_i_missing_in_source_f = []

    def report(self, verifier: BackupVerifier):

        if self.checks_run:

            report_list = []

            if self.check_passed:
                report_list.append(f'{self.backup_name} PASSED {datetime.now()}')
            else:
                report_list.append(f'{self.backup_name} FAILED {datetime.now()}')

            report_list.append("\n")

            # list all the MHLs
            report_list.append(f'Sources: {len(verifier.source_mhl_list)}\n')
            for line in verifier.source_mhl_list:
                report_list.append(f"\t{os.path.basename(line)}\n")

            report_list.append("\n")

            # list all the missing primary files

            report_list.append(f'Source indexes missing from backup index: {len(self.source_i_missing_in_backup_i)}\n')
            for line in self.source_i_missing_in_backup_i:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Files missing from backup index: {len(self.source_f_missing_in_backup_i)}\n')
            for line in self.source_f_missing_in_backup_i:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Files with wrong file size on the backup: {len(self.source_i_wrong_in_backup_i)}\n')
            for line in self.source_i_wrong_in_backup_i:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Files not in source index: {len(self.source_f_missing_in_source_i)}\n')
            for line in self.source_f_missing_in_source_i:
                report_list.append(f"\t{line}\n")

            report_list.append(
                f'Source indexes that are missing source files: {len(self.source_i_missing_in_source_f)}\n')
            for line in self.source_i_missing_in_source_f:
                report_list.append(f"\t{line}\n")

            return ''.join(report_list), self.check_passed

        else:

            return 'Checks not yet run', False

    def quick_check(self):

        """do a quick check of counts to see if everything matches"""

        check_passed = True

        roll_count = len(self.source_mhls)

        print(f"Existing files {len(self.source_files)}")
        print(f"Source indexes {len(self.source_index) + roll_count}")
        print(f"Backup indexes {len(self.backup_index)}")

        # check source index vs files
        if len(self.source_files) > len(self.source_index) + roll_count:
            print_colour("More files in folder than source index, have some been added incorrectly?", PrintColours.FAIL)
            check_passed = False

        elif len(self.source_files) < len(self.source_index) + roll_count:
            print_colour("Fewer files in folder than source index, have some been deleted?", PrintColours.FAIL)
            check_passed = False

        # check index lengths
        if len(self.source_index) + roll_count > len(self.backup_index):
            print_colour("More files in source index than backup index, something hasn't been backed up",
                         PrintColours.FAIL)
            check_passed = False

        if not check_passed:
            self.check_passed = False

        return check_passed

    def source_i_vs_backup_i(self):
        """check if every source index is in the backup index"""
        print('check if every source index is in the backup index')
        for source_i in self.source_index.keys():
            if source_i not in self.backup_index.keys():
                self.source_i_missing_in_backup_i.append(source_i)
                print(f'{source_i} index not in backup!')
                self.check_passed = False

    def source_f_vs_backup_i(self):
        """check if every existing file is in the backup index"""
        print('check if every existing file is in the backup index')
        for source_f in self.source_files:
            if source_f not in self.backup_index.keys():
                self.source_f_missing_in_backup_i.append(source_f)
                print(f'{source_f} file not in backup!')
                self.check_passed = False

    def source_f_vs_source_i(self):
        """check if every existing file is in the source index - have any files been added without a source index?"""
        print('check if every existing file is in the source index - have any files been added without a source index?')

        mhl_count = 0
        for source_f in self.source_files:

            if source_f in self.source_mhls:
                mhl_count += 1
                continue

            if source_f not in self.source_index.keys():
                self.source_f_missing_in_source_i.append(source_f)
                print(f'{source_f} file not in source index!')
                self.check_passed = False

        print(f'Skipped {mhl_count} source MHLs, which won\'t be in themselves obviously!')

    def source_i_vs_source_f(self):
        """check if every source index is in the existing files - have any files been deleted since offload?"""
        print('check if every source index is in the existing files - have any files been deleted since offload?')
        for source_i in self.source_index.keys():
            if source_i not in self.source_files:
                self.source_i_missing_in_source_f.append(source_i)
                print(f'{source_i} index not in source files!')
                self.check_passed = False


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


def trim_path_relative(file_path: str, possible_roots: list) -> str:
    for possible_root in possible_roots:

        if possible_root in file_path:
            file_path = file_path.split(possible_root)[1]
            break

    return file_path


def separate_primary_and_secondary(mhl_list):
    groups = []

    primary = [f for f in mhl_list if (int(f[-5]) % 2 != 0)]
    secondary = [f for f in mhl_list if (int(f[-5]) % 2 == 0)]

    if len(primary):
        groups.append(primary)

    if len(secondary):
        groups.append(secondary)

    return groups


class PrintColours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_colour(message, print_type):
    print(print_type + message + PrintColours.ENDC)


if __name__ == '__main__':
    my_verifier = BackupVerifier("/Users/christykail/Sample footage/Test backups/Day 001")
    my_verifier.do_verification_but_better()
