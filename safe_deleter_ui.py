import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import mhl_backup_comparison
import re


def make_preset_dict() -> dict:
    preset_dict = {

        "Test": ("", 8),
        "Root": ("", 2),
        "Netflix": ("", 5),
        "Fox Searchlight": ("", 4),
        "Wakefield": (r'_hde|^wav$', 0)
    }

    return preset_dict


class BackupVerifierApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.console_lines = 1

        self.presets = make_preset_dict()

        self.setup_ui()

    def setup_ui(self):

        self.title("Cinelab Film & Digital - Safe Deleter")

        try:
            self.logo_image = tk.PhotoImage(file="CFD-Icon_Standard.png")
            self.tk.call('wm', 'iconphoto', self._w, tk.PhotoImage(file="CFD-Icon_Standard.png"))

        except Exception as exception:
            print("Logo failed to load. Reason:", exception)

        else:
            self.label_logo = tk.Label(self, image=self.logo_image, pady=10)
            self.label_logo.grid(column=0, row=0, columnspan=4, sticky="EW")

        # noinspection PyTypeChecker
        self.columnconfigure(tuple(range(4)), weight=1, minsize=5, pad=10)
        # noinspection PyTypeChecker
        self.rowconfigure(tuple(range(8)), weight=1, pad=5)

        # load
        self.btn_input = tk.Button(self, text="Select folder", command=self.load)
        self.btn_input.grid(column=1, row=1, columnspan=2, padx=20, pady=5)

        # check files
        self.var_files = tk.BooleanVar()
        self.var_files.set(True)
        self.check_files = tk.Checkbutton(self, text="Check files as well as indexes", variable=self.var_files,
                                          onvalue=True, offvalue=False)
        self.check_files.grid(column=1, row=2, columnspan=2, padx=20, pady=5)

        # look for primary and secondary backups
        self.var_primary_secondary = tk.BooleanVar()
        self.var_primary_secondary.set(True)
        self.check_primary_secondary = tk.Checkbutton(self, text="Search for primary and secondary backups",
                                                      variable=self.var_files,
                                                      onvalue=True, offvalue=False)
        self.check_primary_secondary.grid(column=1, row=2, columnspan=2, padx=20, pady=5)

        # folders to search
        self.label_folders = tk.Label(self, text="Source folders to search")
        self.label_folders.grid(column=1, row=3, sticky="E")
        self.entry_folders = tk.Entry(self)
        self.entry_folders.insert(0, "Camera_Media, Sound_Media")
        self.entry_folders.grid(column=2, row=3, sticky="EW")

        # LTO preset
        self.label_lto_preset = tk.Label(self, text="LTO layout type")
        self.label_lto_preset.grid(column=1, row=5, sticky="E")
        lto_preset_list = list(self.presets.keys())
        self.combo_lto_preset = ttk.Combobox(self, values=lto_preset_list, width=20, state="readonly")
        self.combo_lto_preset.current(1)
        self.combo_lto_preset.grid(column=2, row=5, sticky="W")

        # info label
        self.label_info = tk.Label(self, text="Select a day folder to verify", font=('LucidaGrande.ttc', 25))
        self.label_info.grid(column=0, row=10, columnspan=4, padx=20, pady=5)
        self.text_colour = self.label_info.cget("fg")

        # console
        self.text_console = tk.Text(self, width=75, takefocus=0, highlightthickness=0, padx=5, pady=5,
                                    font='LucidaGrande.ttc')
        self.text_console.grid(column=0, row=11, columnspan=4, sticky="NEW", pady=10, padx=10)
        self.text_console['state'] = 'disabled'

    def load(self):

        folder = filedialog.askdirectory()

        self.reset_log()

        if not os.path.isdir(folder):
            self.label_info['text'] = "Invalid folder"
            return

        self.label_info['text'] = os.path.basename(folder)
        self.update()

        folders_to_search = [i.strip() for i in self.entry_folders.get().split(",")]

        bu_root_pattern, trim_top_levels = self.presets[self.combo_lto_preset.get()]

        if bu_root_pattern:
            try:
                re.compile(bu_root_pattern)
            except re.error:
                self.log(f"Not a valid matching pattern: {bu_root_pattern}", 4)
                return
        try:
            my_verifier = mhl_backup_comparison.MHLChecker(folder,
                                                           backup_pattern=bu_root_pattern,
                                                           source_folders=folders_to_search,
                                                           backup_trim=trim_top_levels,
                                                           dual_backups=self.var_primary_secondary.get())

        except mhl_backup_comparison.MHLCheckerException as error:
            self.log(f"Error in verifier: {error}\nEnding - checks did not complete", 4)
            return

        passed = my_verifier.checker_passed
        report = '\n'.join(my_verifier.checker_report)

        if passed:
            self.log(report, 2)

        else:
            self.log(report, 4)

        if passed:
            self.label_info.config(fg="green")
        else:
            self.label_info.config(fg="red")

    def reset_log(self):

        self.label_info.config(fg=self.text_colour)

        self.text_console['state'] = 'normal'
        print("Clearing log")
        self.console_lines = 1
        self.text_console.delete("1.0", "end")
        self.update()
        self.text_console['state'] = 'disabled'

    def log(self, string: str, log_level: int):

        line_count = string.count('\n') + 1

        self.console_lines = self.text_console.get("1.0", 'end').count('\n') + 1
        self.text_console['state'] = 'normal'
        self.text_console.insert(tk.END, "\n" + string)

        if log_level == 0 or log_level == 1:
            self.text_console.tag_add("Normal", f'{self.console_lines}.0', f'{self.console_lines+line_count}.end')

        elif log_level == 2:
            self.text_console.tag_add("Good", f'{self.console_lines}.0', f'{self.console_lines+line_count}.end')
            self.text_console.tag_config("Good", foreground="green")

        elif log_level == 3:
            self.text_console.tag_add("Warning", f'{self.console_lines}.0', f'{self.console_lines+line_count}.end')
            self.text_console.tag_config("Warning", foreground="#ff9200")

        elif log_level == 4:

            self.text_console.tag_add("Fail", f'{self.console_lines}.0', f'{self.console_lines+line_count}.end')
            self.text_console.tag_config("Fail", foreground="red")

        self.text_console.see('end')

        self.text_console['state'] = 'disabled'

        self.update()


if __name__ == '__main__':
    app = BackupVerifierApp()
    app.mainloop()
