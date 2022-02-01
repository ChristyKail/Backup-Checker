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

        backup_names = ["Primary", "Secondary", "Tertiary"]

        for ii, group_list in enumerate(backup_mhl_groups):
            print(group_list)

            group_dict = self.list_of_mhls_to_dict(group_list)
            backup = Backup(os.path.basename(group_list[0]), group_dict, source_index, source_files,
                            len(self.source_mhl_list))
            self.backups.append(backup)

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

    def do_verification(self):

        for backup in self.backups:
            print_colour(backup.backup_name, PrintColours.HEADER)

            backup.quick_check()
            backup.check_files()
            backup.check_index()
            backup.checks_run = True

    def write_report(self):

        passed = True

        # report and log number of MHLs
        mhl_info = f'Backups checked: {len(self.backups)}'
        self.manager.log(mhl_info, "normal")
        if len(self.backups) < 2:
            self.manager.log("Only 1 backup was verified", "warning")

        report_string = mhl_info+'\n'

        for backup in self.backups:

            report_string = report_string+'\t'+backup.backup_name+'\n'
            self.manager.log("\t"+backup.backup_name, "normal")

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

    def __init__(self, name: str, backup_index: {}, source_index: {}, source_files: [], roll_count: int):

        self.backup_name = name

        self.checks_run = False
        self.check_passed = True

        self.backup_index = backup_index
        self.source_index = source_index
        self.source_files = source_files

        self.roll_count = roll_count

        self.missing_vs_index = []
        self.mismatched_size = []

        self.missing_vs_files = []
        self.unindexed_files = []

        self.files_missing_vs_source_index = []

    def quick_check(self):

        check_passed = True

        print(
            f"Files {len(self.source_files)}, source {len(self.source_index) + self.roll_count}, backup {len(self.backup_index)}")

        # check source index vs files
        if len(self.source_files) > len(self.source_index) + self.roll_count:
            print_colour("More files in folder than source index, have some been added incorrectly?", PrintColours.FAIL)
            check_passed = False
        elif len(self.source_files) < len(self.source_index) + self.roll_count:
            print_colour("Fewer files in folder than source index, have some been deleted?", PrintColours.FAIL)
            check_passed = False

        # check index lengths
        if len(self.source_index) + self.roll_count > len(self.backup_index):
            print_colour("More files in source index than backup index, something hasn't been backed up",
                         PrintColours.FAIL)
            check_passed = False

        if not check_passed:
            self.check_passed = False

        return check_passed

    def check_index(self):

        check_passed = True

        for file_name, file_size in self.source_index.items():

            # check if index is missing
            if file_name not in self.backup_index.keys():
                self.missing_vs_index.append(file_name)
                print_colour(f"Index check: {file_name} not in backup index", PrintColours.FAIL)
                check_passed = False

            # check if index is different size
            elif file_size != self.backup_index[file_name]:
                self.mismatched_size.append(file_name)
                print_colour(f"Index check: {file_name} source index wrong size compared backup index",
                             PrintColours.FAIL)
                check_passed = False

        if not check_passed:
            self.check_passed = False
        return check_passed

    def check_files(self):

        check_passed = True
        mhl_count = 0

        # worry about having more files than indexes
        for file_name in self.source_files:

            # check for any files not in source index
            if file_name not in self.source_index.keys():

                if file_name.endswith(".mhl"):
                    mhl_count += 1

                else:
                    self.unindexed_files.append(file_name)
                    print_colour(f"File check: {file_name} not in source index. Did it get indexed properly before "
                                 f"backup?", PrintColours.WARNING)
                    check_passed = False

            # check for any files not in backup index
            if file_name not in self.backup_index.keys():
                self.missing_vs_files.append(file_name)
                print_colour(f"File check: {file_name} not backup index", PrintColours.FAIL)
                check_passed = False

        # worry about having fewer files then in the source index
        for index_file_name in self.source_index.keys():

            if index_file_name not in self.source_files:
                self.files_missing_vs_source_index.append(index_file_name)
                print_colour(f"File check: {file_name} referenced in source index, but not in files. Has it been "
                             f"deleted?", PrintColours.WARNING)

        if mhl_count != self.roll_count:
            print_colour("Roll count doesn't match MHL count", PrintColours.WARNING)
            check_passed = False

        if not check_passed:
            self.check_passed = False
        return check_passed

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

            report_list.append(f'Source indexes missing from backup index: {len(self.missing_vs_index)}\n')
            for line in self.missing_vs_index:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Files missing from backup index: {len(self.missing_vs_files)}\n')
            for line in self.missing_vs_files:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Files with wrong file size on the backup: {len(self.mismatched_size)}\n')
            for line in self.mismatched_size:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Source files that have no source index: {len(self.unindexed_files)}\n')
            for line in self.unindexed_files:
                report_list.append(f"\t{line}\n")

            report_list.append(f'Source indexes that are missing source files: {len(self.files_missing_vs_source_index)}\n')
            for line in self.files_missing_vs_source_index:
                report_list.append(f"\t{line}\n")

            return ''.join(report_list), self.check_passed

        else:

            return 'Checks not yet run', False


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
    my_verifier.do_verification()
    my_verifier.write_report()
