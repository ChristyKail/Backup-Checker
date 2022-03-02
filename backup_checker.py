import csv
import os
import re
from datetime import datetime
import sys

import ale


class BackupChecker:

    def __init__(self, root_folder, source_folders=None, backup_pattern="", backup_trim=0,
                 dual_backups=True, add_roll_folder=1, manager=None, require_ale=False):

        if not source_folders:
            self.source_folders = ["Camera_Media", "Sound_Media"]
        else:
            self.source_folders = source_folders

        self.logger = Logger(manager=manager)
        self.error_lock_triggered = False

        self.files_scanned = 0

        self.root_folder = root_folder
        self.backup_pattern = backup_pattern
        self.backup_trim = backup_trim
        self.add_parent_folders = add_roll_folder

        self.require_ale = require_ale

        self.dual_backups = dual_backups
        self.backup_mhls = self.get_backup_mhls()
        self.backup_groups = self.group_mhls()

        self.source_mhls = self.get_source_mhls()
        self.delivery_ale = self.get_delivery_ale()

        self.source_dictionary = self.sources_to_dict()
        self.ale_clips = self.ale_to_clip_list()

        self.backups = self.create_backups_from_mhl_groups()

        self.run_backup_checks()

        self.write_report_file()

    def get_source_mhls(self):

        mhl_list = []

        self.logger.log("Source MHLs:", report=True)
        for this_source_folder in self.source_folders:

            if not os.path.exists(os.path.join(self.root_folder, this_source_folder)):
                message = f"[WARNING] {this_source_folder} folder not found"
                self.logger.warning(message, report=True)

            else:
                for root, dirs, files in os.walk(os.path.join(self.root_folder, this_source_folder)):
                    for file in files:

                        if str(file).endswith(".mhl"):
                            self.logger.log(file, report=True)
                            mhl_list.append(os.path.join(root, file))

                        elif str(file) != '.DS_Store':

                            self.files_scanned += 1

        if not mhl_list:
            raise BackupCheckerException("No sources found in specified source folders")

        mhl_list.sort()

        return mhl_list

    def get_backup_mhls(self):

        folder_to_scan = self.get_folder_to_scan()

        mhl_list = [os.path.join(folder_to_scan, file) for file in os.listdir(folder_to_scan) if
                    file.endswith(".mhl")]

        if not mhl_list:
            raise BackupCheckerException("No backups found in specified folder")

        mhl_list.sort()

        return mhl_list

    def get_delivery_ale(self):

        folder_to_scan = self.get_folder_to_scan()

        for file in os.listdir(folder_to_scan):

            if file.endswith(".ale") or file.endswith(".ALE"):
                file = os.path.join(folder_to_scan, file)

                day_ale = ale.Ale(file)

                return day_ale

        if self.require_ale:
            self.logger.warning("[WARNING] No delivery ALE found", report=True)

        return None

    def sources_to_dict(self):

        dictionary = {}

        mhl: str
        for mhl in self.source_mhls:
            self.logger.log(f"Loading source {os.path.basename(mhl)}")

            dictionary.update(mhl_to_dict(mhl, add_parent_folders=self.add_parent_folders))

        return dictionary

    def ale_to_clip_list(self):

        if not self.delivery_ale:
            return None

        columns = ["Display name", "Display Name"]
        data = []

        for column in columns:

            if column in self.delivery_ale.dataframe.columns:
                data = list(self.delivery_ale.dataframe[column])
                break

        return data

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
            self.logger.warning("[WARNING] Could not split primary and secondary backups", report=True)
            groups = [self.backup_mhls]

        if len(groups) < 2:
            self.logger.warning('[WARNING] Only one backup MHL found', report=True)

        groups.sort()

        return groups

    def create_backups_from_mhl_groups(self):

        backups = []

        for group in self.backup_groups:
            backup = self.Backup(self.source_dictionary, group, self, self.ale_clips)
            backups.append(backup)

        return backups

    def run_backup_checks(self):

        if len(self.source_dictionary) != self.files_scanned:
            self.logger.error('\nScanned file count does not match index count!', True)

        for backup in self.backups:
            backup.compare_mhls()
            backup.compare_clip_list()
            backup.report_backup()

    def write_report_file(self):

        if 'unittest' in sys.modules.keys():
            self.logger.log("Running in test mode, file report will not be written")
            return

        now = datetime.now()
        current_time = now.strftime("%Y%m%d_%H%M%S")

        if self.error_lock_triggered and self.logger.alert_level != 4:
            raise BackupCheckerException("Critical internal error! Error lock has been triggered, but the logger is "
                                         "not reporting an error")

        if self.logger.alert_level >= 4:
            result = 'FAILED'

        elif self.logger.alert_level >= 3:
            result = 'WARNING'

        elif self.logger.alert_level >= 2:
            result = 'PASSED'

        else:
            result = 'UNKNOWN'

        file_name = f'{os.path.basename(self.root_folder)} - checks {result} - {current_time}.txt'

        file_path = os.path.join(self.root_folder, file_name)

        with open(file_path, "w") as file_handler:

            file_handler.write("\n".join(self.logger.log_report))

    def get_folder_to_scan(self):

        if os.path.isdir(os.path.join(self.root_folder, 'Verifier')):

            folder_to_scan = os.path.join(self.root_folder, 'Verifier')
        else:
            folder_to_scan = self.root_folder

        return folder_to_scan

    def lock_error(self):

        self.error_lock_triggered = True

    class Backup:

        def __init__(self, sources: {}, backups: [str], parent, ale_clips):

            self.parent = parent

            self.name = " ".join([os.path.basename(x).strip(".mhl") for x in backups])

            self.checked = False
            self.backup_report = []

            self.files_checked = 0
            self.ale_clips_checked = 0

            self.backups = backups
            self.ale_clips = ale_clips

            self.source_dictionary = sources
            self.backup_dictionary = self.backups_to_dict()

            self.missing_files = []
            self.wrong_files = []
            self.missing_delivery = []

        def backups_to_dict(self):

            dictionary = {}

            for mhl in self.backups:
                self.parent.logger.log(f'\nLoading backup {self.name}')

                dictionary.update(mhl_to_dict(mhl,
                                              trim_top_levels=self.parent.backup_trim,
                                              root_pattern=self.parent.backup_pattern))

                self.parent.logger.log(f'Normalised backup path: {list(dictionary.keys())[0]}')

            return dictionary

        def compare_mhls(self):

            errors = 0

            for source_file, source_size in self.source_dictionary.items():

                if source_file in self.backup_dictionary.keys():

                    if source_size == self.backup_dictionary[source_file]:
                        pass

                    else:
                        self.wrong_files.append(source_file)
                        self.parent.lock_error()

                else:
                    self.missing_files.append(source_file)
                    self.parent.lock_error()

                self.files_checked += 1

            self.checked = True

            return errors

        def compare_clip_list(self):

            backup_file_base = [os.path.basename(x) for x in self.backup_dictionary.keys()]

            if self.ale_clips is None:
                return

            for clip in self.ale_clips:

                self.ale_clips_checked += 1

                if clip.endswith('ari') or clip.endswith('arx') or clip.endswith('dpx') or clip.endswith("dng"):
                    frame_number = re.search(r'(?<=(\[))\d{7,8}', clip).group(0)
                    entry_file = re.sub(r'\[\d{7,8}-\d{7,8}]', frame_number, clip)
                else:
                    entry_file = clip

                if entry_file in backup_file_base:
                    pass

                else:
                    self.parent.lock_error()
                    self.missing_delivery.append(clip)

        def report_backup(self):

            self.parent.logger.log(f'\n{self.name}', True)
            self.parent.logger.log(f'{self.files_checked} files checked', report=True)
            self.parent.logger.log(f'{self.ale_clips_checked} ALE clips checked', True)

            self.report_check_list(self.missing_files, "Missing source indexes")
            self.report_check_list(self.wrong_files, "Incorrect source indexes")
            self.report_check_list(self.missing_delivery, "Missing ALE clips")

        def report_check_list(self, check_list, check_list_name):

            if len(check_list):
                self.parent.logger.error(check_list_name, report=True)
                cutoff_count = 5
                cutoff = False
                for index, value in enumerate(check_list):

                    self.parent.logger.error(f'\t{value}', report=True, supress_log=cutoff)

                    if index >= cutoff_count + 1:
                        cutoff = True
                if cutoff:
                    self.parent.logger.error(f'\t...and {len(check_list) - cutoff_count} more')

                return False

            else:
                self.parent.logger.passed(f'{check_list_name} - None', report=True)
                return True


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
        next(reader)

        dictionary = {row[0]: [row[1], int(row[2]), int(row[3]), int(row[4]), row[5:8], int(row[9])] for row in reader}

    return dictionary


def make_checker_from_preset(root_folder, preset_name, preset_dict, manager=None):
    preset_list = preset_dict[preset_name]

    my_verifier = BackupChecker(root_folder,
                                backup_pattern=preset_list[0],
                                backup_trim=preset_list[1],
                                dual_backups=preset_list[2],
                                add_roll_folder=preset_list[3],
                                source_folders=[x for x in preset_list[4] if x],
                                require_ale=bool(int(preset_list[5])),
                                manager=manager)

    return my_verifier


class Logger:

    # alert levels
    # 0 - Verbose
    # 1 - Normal
    # 2 - Pass
    # 3 - Warning
    # 4 - Fail

    def __init__(self, manager=None):

        self.alert_level = 1

        self.log_report = []

        self.manager = manager

    def log(self, message, report=False, supress_log=False):

        self.do_log(message, 1, PrintColours.NORMAL, report, supress_log)

    def passed(self, message, report=False, supress_log=False):

        self.do_log(message, 2, PrintColours.OKGREEN, report, supress_log)

    def warning(self, message, report=False, supress_log=False):

        self.do_log(message, 3, PrintColours.WARNING, report, supress_log)

    def error(self, message, report=False, supress_log=False):

        self.do_log(message, 4, PrintColours.FAIL, report, supress_log)

    def do_log(self, message, alert_level, colour, report, supress_log):

        self.set_alert_level(alert_level)

        if report:
            self.log_report.append(message)

        if not supress_log:

            if 'unittest' in sys.modules.keys():
                return

            print_colour(message, colour)
            if self.manager:
                self.manager.log(message, alert_level)

    def set_alert_level(self, level):

        if level > self.alert_level:
            self.alert_level = level


class PrintColours:
    NORMAL = ''
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
        make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/1_Missing_Backup_Roll", "Tests",
                                 this_preset_dict)
        make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/2_Wrong_File_Size", "Tests",
                                 this_preset_dict)
        make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/3_Missing_Folder", "Tests",
                                 this_preset_dict)
        make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/4_Missing_ALE", "Tests", this_preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/TARTAN DAY 24", "Tartan", this_preset_dict)
        # make_checker_from_preset("/Volumes/CK_SSD/Sample footage/Test backups/WS_SD_001", "Winston Sugar", this_preset_dict)

    else:

        folder = input("Drag day folder here...")
        folder = folder.replace("\\", "")

        this_preset_dict = load_presets('presets.csv')

        for key in this_preset_dict.keys():
            print(key)

        preset = input("Type one of the above presets")

        if preset in list(this_preset_dict.keys()):
            BackupChecker(folder, backup_pattern=this_preset_dict[preset][0], backup_trim=this_preset_dict[preset][1])
