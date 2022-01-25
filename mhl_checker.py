import os
import xmltodict
import time


class IndexChecker:

    def __init__(self, root_folder: str, folders_to_search=None):

        # assume we want to search Camera_Media and Sound_Media if it's not defined
        if folders_to_search is None:
            folders_to_search = ["Camera_Media", "Sounds_Media"]

        # get a list of MHLs in the root folder - these are the backup indexes
        self.backup_mhl_list = [os.path.join(root_folder, file) for file in os.listdir(root_folder) if
                                is_file_an_index(file) == "mhl"]

        self.backup_mhl_list_primary = [f for f in self.backup_mhl_list if (int(f[-5]) % 2 != 0)]
        self.backup_mhl_list_secondary = [f for f in self.backup_mhl_list if (int(f[-5]) % 2 == 0)]

        print(f"Primary backups: {' '.join(self.backup_mhl_list_primary)}")
        print(f"Secondary backups: {' '.join(self.backup_mhl_list_secondary)}")

        if not self.backup_mhl_list:
            print("No backup index was found")
            return
        else:
            print(self.backup_mhl_list)

        self.source_mhl_list = []
        # get a list of MHLs in the media folders
        for folder_to_search in folders_to_search:
            for root, dirs, files in os.walk(os.path.join(root_folder, folder_to_search)):
                for file in files:
                    if file.endswith(".mhl"):
                        self.source_mhl_list.append(os.path.join(root, file))

        if not self.source_mhl_list:
            print("No source indexes were found")
            return
        else:
            print(self.source_mhl_list)

        start_time = time.time()

        backup_dict = {}
        for backup_mhl in self.backup_mhl_list:
            backup_dict.update(mhl_to_dict(backup_mhl))

        source_dict = {}
        for source_mhl in self.source_mhl_list:
            source_dict.update(mhl_to_dict(source_mhl))

        print(f'Parsed MHLs in {time.time() - start_time} seconds')

        counter = 0
        for key, value in source_dict.items():

            if key not in backup_dict.keys():

                print(f"Aggggggggg! {key} is not on tape!")
            else:

                if source_dict[key] != backup_dict[key]:
                    print(f"{key} is {source_dict[key]} bytes from the source, but {backup_dict[key]} bytes on tape!")

                counter += 1

        print(f'Out of {len(source_dict)} files, {counter} have been backed up')
        print(f'Checked in {time.time() - start_time} seconds')


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


def mhl_to_dict(file_path: str):
    dict_of_files_and_sizes = {}

    with open(file_path, "r") as file_handler:
        contents = file_handler.read()

        xml = xmltodict.parse(contents)

    if xml["hashlist"]["hash"][0]['file'].strip().startswith(r"/Volumes"):
        remove_volume = True
    else:
        remove_volume = False

    if xml["hashlist"]["creatorinfo"]["username"] != "YoYotta":
        add_roll_to_path = os.path.basename(os.path.dirname(file_path))
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


if __name__ == "__main__":

    folder_input = input("Drag root folder")

    folder_input = folder_input.replace("\ ", " ")

    index_checker = IndexChecker(folder_input)
