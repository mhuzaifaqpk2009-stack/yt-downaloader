import tkinter as tk
from main import RoundedEntry

root = tk.Tk()
root.withdraw()
frame = tk.Frame(root)
frame.pack()
re = RoundedEntry(frame, textvariable=None, font=("Segoe UI Variable", 12), bg="#fff", fg="#000", width=400, height=40)
re.pack()
# Test insert/delete/get
try:
    re.delete(0, tk.END)
    print('delete OK')
    re.insert(0, '  Paste YouTube URL here...')
    print('insert OK')
    val = re.get()
    print('get returned:', repr(val))
except Exception as e:
    print('Exception:', type(e), e)
finally:
    root.destroy()
