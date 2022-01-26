import os
import re
from time import time

import xmltodict
import mac_colors


class IndexChecker:

    def __init__(self, root_folder: str, folders_to_search=None):

        # assume we want to search Camera_Media and Sound_Media if it's not defined
        if folders_to_search is None:
            folders_to_search = ["Camera_Media", "Sound_Media"]

        self.logger = ""
        self.failed_check = False

        # get a list of MHLs in the root folder - these are the backup indexes
        backup_mhl_list = [os.path.join(root_folder, file) for file in os.listdir(root_folder) if
                           is_file_an_index(file) == "mhl"]

        if not backup_mhl_list:
            print("No backup index was found")
            return

        # divide the MHLs into primary  and secondary backups
        self.backup_mhl_list_primary = [f for f in backup_mhl_list if (int(f[-5]) % 2 != 0)]
        self.backup_mhl_list_secondary = [f for f in backup_mhl_list if (int(f[-5]) % 2 == 0)]

        # get a list of MHLs in the media folders - these are the source indexes
        self.source_mhl_list = []
        for folder_to_search in folders_to_search:

            for root, dirs, files in os.walk(os.path.join(root_folder, folder_to_search)):
                for file in files:
                    if file.endswith(".mhl"):
                        self.source_mhl_list.append(os.path.join(root, file))

        # check we found some source indexes, otherwise return
        if self.source_mhl_list:

            print(f"Source indexes - {len(self.source_mhl_list)}")
            for mhl in self.source_mhl_list:
                print(os.path.basename(mhl))

        else:
            print("No source indexes were found")
            return

        # make three dicts, primary, secondary, and source
        self.backup_dict_primary = {}
        for mhl in self.backup_mhl_list_primary:
            self.backup_dict_primary.update(mhl_to_dict_fast(mhl))

        self.backup_dict_secondary = {}
        for mhl in self.backup_mhl_list_secondary:
            self.backup_dict_secondary.update(mhl_to_dict_fast(mhl))

        self.source_dict = {}
        for mhl in self.source_mhl_list:
            self.source_dict.update(mhl_to_dict_fast(mhl))

        self.add_to_log(f"Files in source: {len(self.source_dict)} - {len(self.source_dict)+len(self.source_mhl_list)} including MHLs!")
        self.add_to_log(f"Files in primary backup: {len(self.backup_dict_primary)}")
        self.add_to_log(f"Files in secondary backup: {len(self.backup_dict_secondary)}")

        # check the source against the primary, if available
        if len(self.backup_dict_primary):

            missing_primary, mismatch_primary = compare_dicts(self.backup_dict_primary, self.source_dict)

            if missing_primary:
                self.add_to_log("The following files are missing on primary backups:")
                self.add_to_log("\n".join(missing_primary))
            if mismatch_primary:
                self.add_to_log("The following files have the wrong files size on primary backups:")
                self.add_to_log("\n".join(mismatch_primary))
        else:
            self.add_to_log("No primary backups were checked")

        if len(self.backup_dict_secondary):

            missing_secondary, mismatch_secondary = compare_dicts(self.backup_dict_secondary, self.source_dict)

            if missing_secondary:
                self.add_to_log("The following files are missing on secondary backups:")
                self.add_to_log("\n".join(missing_secondary))
            if mismatch_secondary:
                self.add_to_log("The following files have the wrong files size on primary backups:")
                self.add_to_log("\n".join(mismatch_secondary))
        else:
            self.add_to_log("No secondary backups were checked")

        self.write_out_log(root_folder)

    def add_to_log(self, string: str, fail=True):

        if fail:
            self.failed_check = True

        self.logger = self.logger + "\n" + string
        print(string)

    def write_out_log(self, directory):

        backups_string = " ".join(
            os.path.basename(f)[:6] for f in self.backup_mhl_list_primary + self.backup_mhl_list_secondary)

        if self.failed_check:
            result = "failed"
        else:
            result = "passed"

        file_name = os.path.join(directory, f'MHL check - {backups_string} - {result}.txt')

        with open(file_name, 'w') as file_handler:

            file_handler.write(self.logger)

        if self.failed_check:
            mac_colors.red(file_name)
        else:
            mac_colors.green(file_name)


def compare_dicts(backup_dict, source_dict):
    missing = []
    mismatch = []

    for key, value in source_dict.items():

        if key not in backup_dict.keys():
            missing.append(key)

        elif source_dict[key] != backup_dict[key]:
            mismatch.append(key)

    return missing, mismatch


def extract_files_from_index(filename):
    """returns a list of files from any index format"""

    with open(filename, 'r') as file_handler:

        # read every line of text into a string list
        text_lines = file_handler.readlines()

        #
        if filename.lower().endswith('.mhl'):
            file_list = [line.replace("<file>", "").replace(r"</file>", "").strip() for line in text_lines if
                         line.strip().startswith("<file>")]

        elif filename.lower().endswith('.md5'):
            file_list = [line.split()[1] for line in text_lines if line.strip()]

        elif filename.lower().endswith('.toc'):
            file_list = [line for line in text_lines]

        else:

            print("Unknown index file format")
            # raise ArgumentError("Unknown index file format")
            return []

    return file_list


def is_file_an_index(file: str):
    if file.lower().endswith(".mhl"):

        index_type = "mhl"

    elif file.lower().endswith(".md5"):

        index_type = "md5"

    elif file.lower().endswith(".toc"):

        index_type = "toc"

    else:

        index_type = False

    return index_type


def mhl_to_dict(mhl_file_path: str):
    dict_of_files_and_sizes = {}

    with open(mhl_file_path, "r") as file_handler:
        contents = file_handler.read()

        xml = xmltodict.parse(contents)

    if xml["hashlist"]["hash"][0]['file'].strip().startswith(r"/Volumes"):
        remove_volume = True
    else:
        remove_volume = False

    if xml["hashlist"]["creatorinfo"]["username"] != "YoYotta":
        add_roll_to_path = os.path.basename(os.path.dirname(mhl_file_path))
    else:
        add_roll_to_path = False

    for hash_item in xml["hashlist"]["hash"]:

        file_path = hash_item["file"]

        # remove volume information
        if remove_volume:
            elements = file_path.split(os.sep)
            del elements[:3]
            file_path = os.sep.join(elements)
            file_path = os.path.sep + file_path
        elif add_roll_to_path:
            file_path = os.path.join(add_roll_to_path, file_path)
            file_path = os.path.sep + file_path

        # head trim the path down to below Camera_Media or Sound_Media

        if "Camera_Media" in file_path:
            file_path = file_path.split("Camera_Media")[1]
        elif "Sound_Media" in file_path:
            file_path = file_path.split("Sound_Media")[1]

        dict_of_files_and_sizes[file_path] = hash_item["size"]

    return dict_of_files_and_sizes


def mhl_to_dict_fast(mhl_file_path: str):
    dict_of_files_and_sizes = {}

    print(f'Loading MHL {os.path.basename(mhl_file_path)} - this might take a second...')

    with open(mhl_file_path, "r") as file_handler:
        contents = file_handler.readlines()

    add_roll_to_path = ""

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

            # add this file to the dictionary
            dict_of_files_and_sizes[file_path] = file_size

    return dict_of_files_and_sizes


def remove_xml_tag(string: str, tag_name: str):
    return string.replace(f'<{tag_name}>', "").replace(f'</{tag_name}>', "").strip()


if __name__ == "__main__":

    folder_input = ''
    # folder_input = input("Drag root folder")
    # folder_input = folder_input.replace("\ ", " ").strip()

    if not folder_input:
        folder_input = "/Users/christykail/Cinelab_dev/Safe-Deleter/TARTAN MHLs"

    start_time = time()
    index_checker = IndexChecker(folder_input)
    print(f'Done in {time() - start_time}')
