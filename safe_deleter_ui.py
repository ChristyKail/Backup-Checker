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

        self.last_folder = ''

        self.setup_ui()

    # noinspection PyAttributeOutsideInit
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

        folder = filedialog.askdirectory(initialdir=self.last_folder)

        self.last_folder = os.path.dirname(folder)

        self.reset_log()

        if not os.path.isdir(folder):
            self.label_info['text'] = "Invalid folder"
            return

        self.label_info['text'] = os.path.basename(folder)
        self.update()

        try:

            my_verifier = mhl_backup_comparison.make_checker_from_preset(folder,
                                                                         self.combo_lto_preset.get(),
                                                                         self.presets,
                                                                         manager=self)

        except mhl_backup_comparison.BackupCheckerException as error:
            self.log(f"Error in verifier: {error}\nEnding - checks did not complete", 4)
            return

        if my_verifier.logger.alert_level >= 4 or my_verifier.error_lock_triggered:
            self.label_info.config(fg="red")
        elif my_verifier.logger.alert_level >= 3:
            self.label_info.config(fg="orange")
        elif my_verifier.logger.alert_level >= 2:
            self.label_info.config(fg="green")
        else:
            self.label_info.config(fg="white")

        self.log("[Checks complete]", 1)

    def reset_log(self):

        self.label_info.config(fg=self.text_colour)

        self.text_console['state'] = 'normal'
        print("Clearing log")
        self.console_lines = 1
        self.text_console.delete("1.0", "end")
        self.update()
        self.text_console['state'] = 'disabled'

    def log(self, string: str, log_level: int):

        self.console_lines = self.text_console.get("1.0", 'end').count('\n') + 1
        self.text_console['state'] = 'normal'
        self.text_console.insert(tk.END, f"\n{string}", (str(log_level),))

        self.text_console.tag_config("0", foreground="grey")
        self.text_console.tag_config("1", foreground="grey")
        self.text_console.tag_config("2", foreground="green")
        self.text_console.tag_config("3", foreground="#ff9200")
        self.text_console.tag_config("4", foreground="red")

        self.text_console.see('end')

        self.text_console['state'] = 'disabled'

        self.update()


if __name__ == '__main__':
    app = BackupVerifierApp()
    app.mainloop()
