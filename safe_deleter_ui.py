import os
import tkinter as tk
from tkinter import filedialog
import backup_verifier


class App(tk.Tk):

    def __init__(self):
        super().__init__()

        self.console_lines = 1

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
        self.check_files = tk.Checkbutton(self, text="Check files as well as indexes", variable=self.var_files, onvalue=True, offvalue=False)
        self.check_files['state'] = 'disabled'
        self.check_files.grid(column=1, row=2, columnspan=2, padx=20, pady=5)



        # label
        self.label_info = tk.Label(self, text="Select a day folder to verify", font=('LucidaGrande.ttc', 25))
        self.label_info.grid(column=0, row=3, columnspan=4, padx=20, pady=5)
        self.text_colour = self.label_info.cget("fg")

        # console
        self.text_console = tk.Text(self, width=75, takefocus=0, highlightthickness=0, padx=5, pady=5,
                                    font='LucidaGrande.ttc')
        self.text_console.grid(column=0, row=4, columnspan=4, sticky="NEW", pady=10, padx=10)
        self.text_console['state'] = 'disabled'

    def load(self):

        folder = filedialog.askdirectory()

        self.reset_log()

        self.label_info['text'] = os.path.basename(folder)

        try:
            my_verifier = backup_verifier.BackupVerifier(folder, manager=self, source_i_root_pattern=r'_hde|wav$')

        except Exception as error:
            self.log(f"Error occurred when scanning folder: {error}", 4)
            return

        # TODO fix this so we we can toggle it properly
        my_verifier.run_checks(file_checks=False)
        report, passed = my_verifier.write_report()

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

        self.console_lines = self.text_console.get("1.0", 'end').count('\n')+1
        self.text_console['state'] = 'normal'
        self.text_console.insert(tk.END, "\n" + string)

        if log_level == 0 or log_level == 1:
            self.text_console.tag_add("Normal", f'{self.console_lines}.0', f'{self.console_lines}.end')

        elif log_level == 2:
            self.text_console.tag_add("Good", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Good", foreground="green")

        elif log_level == 3:
            self.text_console.tag_add("Warning", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Warning", foreground="#ff9200")

        elif log_level == 4:

            self.text_console.tag_add("Fail", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Fail", foreground="red")

        self.text_console.see('end')

        self.text_console['state'] = 'disabled'

        self.update()


if __name__ == '__main__':
    app = App()
    app.mainloop()
