import tkinter as tk
from tkinter import filedialog
import mhl_checker


class App(tk.Tk):

    def __init__(self):
        super().__init__()

        self.console_lines = 1

        self.title("Cinelab Film & Digital - Safe Deleter")

        # noinspection PyTypeChecker
        self.columnconfigure(tuple(range(4)), weight=1, minsize=5, pad=10)
        # noinspection PyTypeChecker
        self.rowconfigure(tuple(range(8)), weight=1, pad=5)

        # load
        self.btn_input = tk.Button(self, text="Select", command=self.load)
        self.btn_input.grid(column=1, row=1, sticky="EW", padx=20, pady=5)

        # multiple
        self.var_multi = tk.StringVar()
        self.var_multi.set("False")
        self.check_multi = tk.Checkbutton(self, variable=self.var_multi, onvalue="True", offvalue="False",
                                          text="Multiple")
        self.check_multi.grid(column=2, row=1, sticky="EW")

        # text
        self.text_console = tk.Text(self, width=75)
        self.text_console.insert(tk.END, "Select a folder to verify")
        self.text_console.grid(column=0, row=2, columnspan=4, sticky="NSEW", pady=10)
        self.text_console['state'] = 'disabled'

    def load(self):
        folder = filedialog.askdirectory()

        folder_checker = mhl_checker.IndexChecker(folder, manager=self)

        folder_checker.check_indexes()
        folder_checker.write_report()

    def log(self, string: str, fail: bool):
        self.console_lines += 1

        # self.label_console['text'] = self.label_console['text']+"\n"+string

        self.text_console['state'] = 'normal'

        self.text_console.insert(tk.END, "\n" + string)

        if fail:
            self.text_console.tag_add("Fail", f'{self.console_lines}.0', f'{self.console_lines}.end')
            self.text_console.tag_config("Fail", foreground="#ed3232")

        self.text_console.see('end')

        self.text_console['state'] = 'disabled'


if __name__ == '__main__':
    app = App()
    app.mainloop()
