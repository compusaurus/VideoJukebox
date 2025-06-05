import tkinter as tk
from tkinter import Menu

def do_nothing():
    print("Menu item clicked")

root = tk.Tk()
root.title("Test Menu Window")
root.geometry("300x200")

menubar = Menu(root)
filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Test Item", command=do_nothing)
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

root.config(menu=menubar)
print("Menu configured for test window.")

root.mainloop()
print("Exited mainloop for test window.")