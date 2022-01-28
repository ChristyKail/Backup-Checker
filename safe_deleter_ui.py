import os
import tkinter as tk
from tkinter import filedialog
import mhl_checker


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

        # label
        self.label_info = tk.Label(self, text="Select a day folder to verify", font=('LucidaGrande.ttc', 25))
        self.label_info.grid(column=0, row=2, columnspan=4, padx=20, pady=5)
        self.text_colour = self.label_info.cget("fg")

        # console
        self.text_console = tk.Text(self, width=75, takefocus=0, highlightthickness=0, padx=5, pady=5, font='LucidaGrande.ttc')
        self.text_console.grid(column=0, row=3, columnspan=4, sticky="NEW", pady=10, padx=10)
        self.text_console['state'] = 'disabled'

    def load(self):

        folder = filedialog.askdirectory()

        self.reset_log()

        self.label_info['text'] = os.path.basename(folder)

        try:
            folder_checker = mhl_checker.BackupChecker(folder, manager=self)

        except Exception as error:
            self.log(f"Error occurred when scanning folder: {error}", 'fail')
            return

        passed = folder_checker.check_indexes()
        folder_checker.write_report()

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

    def log(self, string: str, log_type: str):

        self.console_lines += 1
        self.text_console['state'] = 'normal'
        self.text_console.insert(tk.END, "\n" + string)

        if log_type == "normal":
            self.text_console.tag_add("Normal", f'{self.console_lines}.0', f'{self.console_lines}.end')

        elif log_type == "good":
            self.text_console.tag_add("Good", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Good", foreground="green")

        elif log_type == "warning":
            self.text_console.tag_add("Warning", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Warning", foreground="#ff9200")

        elif log_type == "fail":

            self.text_console.tag_add("Fail", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Fail", foreground="red")

        self.text_console.see('end')

        self.text_console['state'] = 'disabled'

        self.update()


if __name__ == '__main__':
    app = App()
    app.mainloop()
