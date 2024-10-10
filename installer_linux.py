import os
import platform
import requests
import struct
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import subprocess

# Constants for GitHub URLs
BASE_URL = "https://github.com/AlextechYT/msgapp/raw/main/"
FILES = ["client_run.py", "client_update.py"]  # Files to download

def download_file(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        with open(save_path, 'wb') as file:
            file.write(response.content)
    except Exception as e:
        show_error(f"Failed to download {url}: {str(e)}")

def install_files(install_directory, file_type, icon_path, create_shortcut_flag):
    install_path = Path(install_directory)
    install_path.mkdir(parents=True, exist_ok=True)

    # Download the required files
    for file_name in FILES:
        if file_type == 'exe' and file_name == "client_run.py":
            file_name = "client_run.exe"
        elif file_type == 'exe' and file_name == "client_update.py":
            file_name = "client_update.exe"

        file_url = f"{BASE_URL}{file_name}"
        print(f"Downloading {file_name}...")
        download_file(file_url, install_path / file_name)
        print(f"{file_name} downloaded successfully!")

    # Write the selected theme to a file
    write_theme_to_file(install_path)

    # Create a desktop shortcut only for client_run if the flag is set
    if create_shortcut_flag:
        shortcut_target = install_path / ("client_run.exe" if file_type == 'exe' else "client_run.py")
        create_shortcut(shortcut_target, icon_path)

    # After installing files, check if Wine is installed and create bootloader for Linux
    if platform.system() == "Linux" and is_wine_installed():
        create_wine_bootloader(install_path)

    messagebox.showinfo("Success", "Installation completed successfully!")

def write_theme_to_file(install_path):
    theme = "dark" if var_dark_mode.get() else "light"
    theme_file_path = install_path / "theme.txt"
    with open(theme_file_path, 'w') as theme_file:
        theme_file.write(theme)
    print(f"Theme '{theme}' written to {theme_file_path}")

def create_shortcut(target, icon_path):
    desktop = Path(os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop"))
    shortcut_path = desktop / f"{target.stem}.lnk"  # Use the file name without extension

    # Manually create a .lnk file
    with open(shortcut_path, "wb") as shortcut_file:
        shortcut_data = bytearray()
        
        # Populate shortcut header
        shortcut_data += b"\x4c\x00\x00\x00"  # Header size (0x4c)
        shortcut_data += b"\x01\x00\x00\x00"  # Link version (1.0)
        shortcut_data += b"\x00\x00\x00\x00"  # Flags
        shortcut_data += b"\x00\x00\x00\x00"  # File attributes
        shortcut_data += b"\x00\x00\x00\x00"  # Creation time
        shortcut_data += b"\x00\x00\x00\x00"  # Access time
        shortcut_data += b"\x00\x00\x00\x00"  # Write time
        shortcut_data += struct.pack("<L", len(str(target)))  # Target path length
        shortcut_data += str(target).encode('utf-16le') + b"\x00\x00"  # Target path
        shortcut_data += struct.pack("<L", len(str(icon_path)))  # Icon path length
        shortcut_data += str(icon_path).encode('utf-16le') + b"\x00\x00"  # Icon path
        
        shortcut_file.write(shortcut_data)

    print(f"Desktop shortcut created at: {shortcut_path}")

def show_error(message):
    messagebox.showerror("Error", message)

def browse_directory():
    directory = filedialog.askdirectory()
    if directory:
        entry_directory.delete(0, tk.END)  # Clear existing text
        entry_directory.insert(0, directory)  # Insert selected directory

def browse_icon():
    icon_path = filedialog.askopenfilename(filetypes=[("Icon files", "*.ico")])
    if icon_path:
        entry_icon.delete(0, tk.END)  # Clear existing text
        entry_icon.insert(0, icon_path)  # Insert selected icon path

def on_install():
    install_directory = entry_directory.get()
    file_type = var_file_type.get()
    icon_path = entry_icon.get()
    create_shortcut_flag = var_create_shortcut.get()  # Get the value of the checkbox

    if not install_directory:
        show_error("Please select an installation directory.")
        return
    if not os.path.exists(install_directory):
        show_error("Installation directory does not exist.")
        return

    # Check if running on Linux and warn the user
    if platform.system() == "Linux":
        messagebox.showwarning("Linux Detected", "MsgApp may not work properly on Linux.")
        result = messagebox.askyesno("Wine Installation", "Would you like to automatically install Wine to run .exe files?")
        if result:
            install_wine()

    install_files(install_directory, file_type, icon_path, create_shortcut_flag)

def install_wine():
    try:
        # Use subprocess to run the Wine installation command (assuming Ubuntu/Debian)
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "wine"], check=True)
        messagebox.showinfo("Wine Installation", "Wine has been successfully installed.")
    except Exception as e:
        show_error(f"Failed to install Wine: {str(e)}")

def is_wine_installed():
    try:
        # Check if Wine is installed by running "wine --version"
        result = subprocess.run(["wine", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        wine_version = result.stdout.decode().strip()
        print(f"Wine is installed: {wine_version}")
        return True
    except subprocess.CalledProcessError:
        return False

def create_wine_bootloader(install_path):
    bootloader_path = install_path / "client_bootloader.sh"
    with open(bootloader_path, 'w') as bootloader_file:
        bootloader_file.write("#!/bin/bash\n")
        bootloader_file.write("wine client_run.exe\n")
    
    # Make the script executable
    os.chmod(bootloader_path, 0o755)
    print(f"Wine bootloader created at: {bootloader_path}")

def toggle_theme():
    if var_dark_mode.get():
        root.config(bg="black")
        label_directory.config(bg="black", fg="white")
        label_file_type.config(bg="black", fg="white")
        label_icon.config(bg="black", fg="white")
        for widget in frame_directory.winfo_children():
            widget.config(bg="black", fg="white")
        for widget in frame_file_type.winfo_children():
            widget.config(bg="black", fg="white")
        for widget in frame_icon.winfo_children():
            widget.config(bg="black", fg="white")
        button_install.config(bg="gray", fg="white")
    else:
        root.config(bg="white")
        label_directory.config(bg="white", fg="black")
        label_file_type.config(bg="white", fg="black")
        label_icon.config(bg="white", fg="black")
        for widget in frame_directory.winfo_children():
            widget.config(bg="white", fg="black")
        for widget in frame_file_type.winfo_children():
            widget.config(bg="white", fg="black")
        for widget in frame_icon.winfo_children():
            widget.config(bg="white", fg="black")
        button_install.config(bg="lightgray", fg="black")

# Create the GUI
root = tk.Tk()
root.title("MsgApp Installer")

# Dark mode toggle
var_dark_mode = tk.BooleanVar(value=False)  # Default to light mode
checkbox_dark_mode = tk.Checkbutton(root, text="Enable Dark Mode", variable=var_dark_mode, command=toggle_theme)
checkbox_dark_mode.pack(pady=10)

# Installation directory
frame_directory = tk.Frame(root)
frame_directory.pack(pady=10)

label_directory = tk.Label(frame_directory, text="Installation Directory:")
label_directory.pack(side=tk.LEFT)

entry_directory = tk.Entry(frame_directory, width=40)
entry_directory.pack(side=tk.LEFT)

button_browse = tk.Button(frame_directory, text="Browse", command=browse_directory)
button_browse.pack(side=tk.LEFT)

# File type selection
frame_file_type = tk.Frame(root)
frame_file_type.pack(pady=10)

label_file_type = tk.Label(frame_file_type, text="Select File Type:")
label_file_type.pack(side=tk.LEFT)

var_file_type = tk.StringVar(value="exe")  # Default to exe
radio_exe = tk.Radiobutton(frame_file_type, text="EXE", variable=var_file_type, value="exe")
radio_exe.pack(side=tk.LEFT)

radio_py = tk.Radiobutton(frame_file_type, text="PY", variable=var_file_type, value="py")
radio_py.pack(side=tk.LEFT)

# Icon selection
frame_icon = tk.Frame(root)
frame_icon.pack(pady=10)

label_icon = tk.Label(frame_icon, text="Select Icon:")
label_icon.pack(side=tk.LEFT)

entry_icon = tk.Entry(frame_icon, width=40)
entry_icon.pack(side=tk.LEFT)

button_browse_icon = tk.Button(frame_icon, text="Browse", command=browse_icon)
button_browse_icon.pack(side=tk.LEFT)

# Create desktop shortcut checkbox
var_create_shortcut = tk.BooleanVar()
checkbox_shortcut = tk.Checkbutton(root, text="Create Desktop Shortcut", variable=var_create_shortcut)
checkbox_shortcut.pack(pady=10)

# Install button
button_install = tk.Button(root, text="Install", command=on_install)
button_install.pack(pady=20)

toggle_theme()  # Initialize with the correct theme

root.mainloop()
