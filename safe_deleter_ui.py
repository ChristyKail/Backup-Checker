import os
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import mhl_backup_comparison


class BackupVerifierApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.console_lines = 1

        self.presets = mhl_backup_comparison.load_presets('presets.csv')

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

        try:

            my_verifier = mhl_backup_comparison.make_checker_from_preset(folder, self.combo_lto_preset.get(), self.presets)

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
