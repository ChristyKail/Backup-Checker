import csv
import os
import re
from datetime import datetime
import ale


class BackupChecker:

    def __init__(self, root_folder, source_folders=None, backup_pattern="", backup_trim=0,
                 dual_backups=True, add_roll_folder=1):

        if not source_folders:
            self.source_folders = ["Camera_Media", "Sound_Media"]
        else:
            self.source_folders = source_folders

        self.checks_run = False
        self.checker_passed = False
        self.checker_report = []

        self.files_scanned = 0

        self.root_folder = root_folder
        self.backup_pattern = backup_pattern
        self.backup_trim = backup_trim
        self.add_parent_folders = add_roll_folder

        self.backup_mhls = self.get_backup_mhls()
        self.source_mhls = self.get_source_mhls()
        self.day_ale = self.get_day_ale()

        self.source_dictionary = self.sources_to_dict()

        self.dual_backups = dual_backups

        self.backup_groups = self.group_mhls()

        self.backups = self.create_backups_from_mhl_groups()

        self.checker_passed = self.run_mhl_checks()

        self.write_report_file()

    def get_source_mhls(self):

        mhl_list = []

        print_colour(f"Scanning folder {os.path.basename(self.root_folder)} for sources", PrintColours.UNDERLINE)

        for this_source_folder in self.source_folders:

            if not os.path.exists(os.path.join(self.root_folder, this_source_folder)):
                message = f"{this_source_folder} folder is not present"
                print_colour(message, PrintColours.WARNING)
                self.checker_report.append(message)

            else:
                for root, dirs, files in os.walk(os.path.join(self.root_folder, this_source_folder)):
                    for file in files:

                        if str(file).endswith(".mhl"):
                            mhl_list.append(os.path.join(root, file))

                        elif str(file) != '.DS_Store':

                            self.files_scanned += 1

        self.checker_report += ['\n'] + [os.path.basename(str(x)) for x in mhl_list]

        if not mhl_list:
            raise BackupCheckerException("No sources found in specified source folders")

        mhl_list.sort()

        return mhl_list

    def get_backup_mhls(self):

        print_colour(f"Scanning folder {os.path.basename(self.root_folder)} for backups", PrintColours.UNDERLINE)

        folder_to_scan = self.get_folder_to_scan()

        mhl_list = [os.path.join(folder_to_scan, file) for file in os.listdir(folder_to_scan) if
                    file.endswith(".mhl")]

        if not mhl_list:
            raise BackupCheckerException("No backups found in specified folder")

        mhl_list.sort()

        return mhl_list

    def get_day_ale(self):

        folder_to_scan = self.get_folder_to_scan()

        for file in os.listdir(folder_to_scan):

            if file.endswith(".ale") or file.endswith(".ALE"):
                file = os.path.join(folder_to_scan, file)

                day_ale = ale.Ale(file)

                return day_ale

        return None
        # raise BackupCheckerException("No day ALE found in the specified folder")

    def sources_to_dict(self):

        dictionary = {}

        mhl: str
        for mhl in self.source_mhls:
            print(f"Loading source {os.path.basename(mhl)}")

            dictionary.update(mhl_to_dict(mhl, add_parent_folders=self.add_parent_folders))

        return dictionary

    def group_mhls(self):

        groups = []

        if not self.dual_backups:
            return [self.backup_mhls]

        if self.backup_mhls[0][-5].isnumeric():

            primary = [f for f in self.backup_mhls if (int(f[-5]) % 2 != 0)]
            secondary = [f for f in self.backup_mhls if (int(f[-5]) % 2 == 0)]

            if len(primary):
                groups.append(primary)

            if len(secondary):
                groups.append(secondary)

        else:
            print("Could not split primary and secondary backups")
            groups = [self.backup_mhls]

        return groups

    def create_backups_from_mhl_groups(self):

        backups = []

        for group in self.backup_groups:
            backup = self.Backup(self.source_dictionary, group, self)
            backups.append(backup)

        return backups

    def run_mhl_checks(self):

        print(f"Starting checks on {os.path.basename(self.root_folder)}")

        if len(self.source_dictionary) != self.files_scanned:
            raise BackupCheckerException(
                f"{len(self.source_dictionary)} files in source index, but {self.files_scanned} "
                f"found during scan")

        checker_passed = True
        checker_report = []

        for backup in self.backups:

            backup.compare_mhls()

            backup_passed = backup.report_backup()

            checker_report = checker_report + ["\n"] + backup.backup_report

            print()

            if backup_passed:
                print_colour('\n'.join(backup.backup_report), PrintColours.OKGREEN)
            else:
                print_colour('\n'.join(backup.backup_report), PrintColours.FAIL)
                checker_passed = False

            print()

            self.checks_run = True

        self.checker_report += checker_report

        return checker_passed

    def write_report_file(self):

        now = datetime.now()
        current_time = now.strftime("%Y%m%d_%H%M%S")

        if not self.checks_run:
            print_colour("Checks not yet run", PrintColours.WARNING)

        if self.checker_passed:
            file_name = f'{os.path.basename(self.root_folder)} - checks PASSED - {current_time}.txt'
            # set_label(self.root_folder, 'green')
        else:
            file_name = f'{os.path.basename(self.root_folder)} - checks FAILED - {current_time}.txt'
            # set_label(self.root_folder, 'red')

        file_path = os.path.join(self.root_folder, file_name)

        with open(file_path, "w") as file_handler:

            file_handler.write("\n".join(self.checker_report))

    def get_folder_to_scan(self):

        if os.path.isdir(os.path.join(self.root_folder, 'Verifier')):

            folder_to_scan = os.path.join(self.root_folder, 'Verifier')
        else:
            folder_to_scan = self.root_folder

        return folder_to_scan

    class Backup:

        def __init__(self, sources: {}, backups: [str], parent, day_ale: ale.Ale = None):

            self.parent = parent

            self.name = " ".join([os.path.basename(x).strip(".mhl") for x in backups])

            self.checked = False
            self.backup_report = []

            self.files_checked = 0

            self.backups = backups
            self.day_ale = day_ale

            self.source_dictionary = sources
            self.backup_dictionary = self.backups_to_dict()

            self.missing_files = []
            self.wrong_files = []

        def backups_to_dict(self):

            dictionary = {}

            for mhl in self.backups:
                print(f"Loading backup {os.path.basename(mhl)}")

                dictionary.update(mhl_to_dict(mhl,
                                              trim_top_levels=self.parent.backup_trim,
                                              root_pattern=self.parent.backup_pattern))

                print_colour(f'LTO preset resulted in path {list(dictionary.keys())[0]}', PrintColours.OKCYAN)

            return dictionary

        def compare_mhls(self):

            errors = 0

            for source_file, source_size in self.source_dictionary.items():

                if not self.files_checked:
                    print(f'Source index example: {source_file}')

                if source_file in self.backup_dictionary.keys():

                    if source_size == self.backup_dictionary[source_file]:
                        pass

                    else:
                        self.wrong_files.append(source_file)

                else:
                    self.missing_files.append(source_file)

                self.files_checked += 1

            self.checked = True

            return errors

        def compare_ale(self):

            if self.day_ale:

                try:

                    data = self.day_ale.dataframe['Source file path']

                except IndexError:

                    raise BackupCheckerException("No valid path column found in ALE")

        def report_backup(self):

            report = [self.name, f'{self.files_checked} files checked']

            if not self.missing_files and not self.wrong_files:

                report.append("Passed")
                passed = True

            else:

                cutoff = 10

                report.append("Failed")
                if len(self.missing_files) <= cutoff:
                    report = report + ["Missing files"] + self.missing_files
                else:
                    report = report + ["Missing files"] + self.missing_files[:cutoff] + \
                             [f"and {len(self.missing_files) - cutoff} more"]

                if len(self.wrong_files) <= cutoff:
                    report = report + ["Mismatched files"] + self.wrong_files
                else:
                    report = report + ["Mismatched files"] + self.wrong_files[:cutoff] + \
                             [f"and {len(self.wrong_files) - cutoff} more"]

                passed = False

            self.backup_report = report

            return passed


class BackupCheckerException(Exception):

    def __init__(self, message="Verifier error"):
        super().__init__(message)


def mhl_to_dict(mhl_file_path: str, add_parent_folders=0, trim_top_levels=0, root_pattern=r''):
    dict_of_files_and_sizes = {}

    with open(mhl_file_path, "r") as file_handler:
        contents = file_handler.readlines()

    for index, line in enumerate(contents):

        line = line.strip()

        if line.startswith('<hashlist'):

            ls = line.split()

            mhl_version = ls[1].replace('version=', '').replace(">", "")

            if mhl_version != '\"1.1\"':
                raise BackupCheckerException(f'This MHL revision ({mhl_version}) is not supported')

        if line.startswith("<file>"):

            # remove the tags from the lines and save them to variables
            file_path = remove_xml_tag(line, "file")
            file_size = remove_xml_tag(contents[index + 1], "size")

            split_file_path = [s for s in os.path.normpath(file_path).split(os.path.sep) if s]

            # add parent folders from the MHL's path
            if add_parent_folders:
                split_mhl_file_path = os.path.normpath(os.path.dirname(mhl_file_path)).split(os.path.sep)
                split_file_path = split_mhl_file_path[-add_parent_folders:] + split_file_path

            # trim off n levels of the top of the path
            else:

                split_file_path = trim_paths(split_file_path, root_pattern=root_pattern,
                                             trim_top_levels=trim_top_levels)

            file_path = os.path.sep + os.path.join(*split_file_path)

            # add this file to the dictionary
            dict_of_files_and_sizes[file_path] = file_size

    return dict_of_files_and_sizes


def trim_paths(path_element_list, root_name='', root_pattern='', trim_top_levels=0):

    if root_name:
        for path_element_index, path_element in enumerate(path_element_list):

            if path_element == root_name:
                path_element_list = path_element_list[path_element_index + 1:]
                break

    elif root_pattern:
        for path_element_index, path_element in enumerate(path_element_list):

            if re.search(root_pattern, path_element):
                path_element_list = path_element_list[path_element_index + 1:]
                break

    if trim_top_levels:

        if trim_top_levels >= len(path_element_list):
            raise BackupCheckerException("Path trimmed to less than 1! Are you using the wrong preset?")

        path_element_list = path_element_list[trim_top_levels:]

    return path_element_list


def remove_xml_tag(string: str, tag_name: str):
    return string.replace(f'<{tag_name}>', "").replace(f'</{tag_name}>', "").strip()


def load_presets(file_path):
    with open(file_path, mode='r') as file_handler:
        reader = csv.reader(file_handler)

        dictionary = {row[0]: [row[1], int(row[2]), int(row[3]), int(row[4]), row[5:]] for row in reader}

    return dictionary


def make_checker_from_preset(root_folder, preset_name, preset_dict):
    preset_list = preset_dict[preset_name]

    my_verifier = BackupChecker(root_folder,
                                backup_pattern=preset_list[0],
                                backup_trim=preset_list[1],
                                dual_backups=preset_list[2],
                                add_roll_folder=preset_list[3],
                                source_folders=[x for x in preset_list[4] if x])

    return my_verifier


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

    debug = True

    if debug:

        this_preset_dict = load_presets('presets.csv')
        make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/0_Known_Good", "Tests", this_preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/1_Missing_Backup_Roll", "Tests", preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/2_Wrong_File_Size", "Tests", preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/TARTAN DAY 24", "Tartan", preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/WS_SD_001", "Winston Sugar", preset_dict)

    else:

        folder = input("Drag day folder here...")
        folder = folder.replace("\\", "")

        this_preset_dict = load_presets('presets.csv')

        for key in this_preset_dict.keys():
            print(key)

        preset = input("Type one of the above presets")

        if preset in list(this_preset_dict.keys()):
            BackupChecker(folder, backup_pattern=this_preset_dict[preset][0], backup_trim=this_preset_dict[preset][1])
