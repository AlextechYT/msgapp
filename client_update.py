# client_update.py

import requests
import os
import sys
import hashlib
import asyncio
import tkinter as tk

# Configuration
REPO_OWNER = 'AlextechYT'            # GitHub username
REPO_NAME = 'msgapp'                 # Repository name
FILE_NAME_PY = 'client_run.py'       # The Python file to check for updates
FILE_NAME_EXE = 'client_run.exe'     # The executable file to check for updates
LOCAL_FILE_PY = os.path.join(os.getcwd(), FILE_NAME_PY)
LOCAL_FILE_EXE = os.path.join(os.getcwd(), FILE_NAME_EXE)

class UpdaterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Updater")
        
        # Status label for updates
        self.status_label = tk.Label(self.root, text="Checking for updates...", padx=20, pady=20)
        self.status_label.pack()
        
        # Error label for displaying errors
        self.error_label = tk.Label(self.root, text="", fg="red", padx=20, pady=20)  
        self.error_label.pack()

        self.root.geometry("400x150")  # Width x Height
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.root.quit()

    def show_error(self, message):
        self.error_label.config(text=message)

    def update_status(self, message):
        self.status_label.config(text=message)

    def run(self):
        self.root.mainloop()

# Get the download URL for the file
async def get_download_url(gui):
    url = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_NAME_PY}'
    gui.update_status("Fetching download URL...")
    response = await loop.run_in_executor(None, requests.get, url)
    if response.status_code == 200:
        content = response.json()
        gui.update_status("Download URL fetched successfully.")
        return content['download_url']  # Get the raw URL for downloading
    else:
        gui.show_error(f"Error fetching download URL: {response.status_code}")  # Show response code in GUI
    return None

# Download the updated file
async def download_file(download_url, gui):
    gui.update_status("Downloading the update...")
    response = await loop.run_in_executor(None, requests.get, download_url)
    if response.status_code == 200:
        with open(FILE_NAME_PY, 'wb') as f:
            f.write(response.content)
        gui.update_status("Update downloaded successfully.")
        return True
    else:
        gui.show_error(f"Error downloading file: {response.status_code}")  # Show response code in GUI
    return False

# Calculate SHA-256 hash of a file
def calculate_hash(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    return None

# Verify the downloaded file using SHA-256
async def verify_update(gui):
    gui.update_status("Verifying update...")
    # Get the hash of the current local file
    local_hash = calculate_hash(LOCAL_FILE_PY) if os.path.exists(LOCAL_FILE_PY) else None
    
    # Get the hash of the server file
    download_url = await get_download_url(gui)
    if download_url:
        response = await loop.run_in_executor(None, requests.get, download_url)
        if response.status_code == 200:
            server_file_hash = hashlib.sha256(response.content).hexdigest()
            print(f"Local file hash: {local_hash}")
            print(f"Server file hash: {server_file_hash}")

            # Compare hashes
            if local_hash != server_file_hash:
                gui.update_status("Update needed. Downloading...")
                return True  # Indicates an update is needed
        else:
            gui.show_error(f"Error verifying update: {response.status_code}")  # Show response code in GUI
    return False  # No update needed

# Restart the main client
def restart_client():
    print("Starting client...")
    if os.path.exists(LOCAL_FILE_EXE):
        os.execv(os.path.abspath(LOCAL_FILE_EXE), ['client_run.exe'])
    else:
        os.execv(sys.executable, ['python'] + [FILE_NAME_PY])

async def update_loop(gui):
    while True:
        print("Checking for updates...")
        gui.update_status("Checking for updates...")
        
        if await verify_update(gui):
            download_url = await get_download_url(gui)
            if download_url:
                if await download_file(download_url, gui):
                    print("Update installed.")
                    gui.update_status("Update installed. Restarting client...")
                    restart_client()
                else:
                    print("Failed to download the update.")
                    gui.update_status("Failed to download the update.")
        else:
            print("No updates needed. Starting client.")
            gui.update_status("No updates needed. Starting client.")
            restart_client()

        await asyncio.sleep(60)  # Wait before checking again

if __name__ == '__main__':
    gui = UpdaterGUI()

    # Create a new event loop and set it as the current one
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Start the update loop in a separate task
    loop.create_task(update_loop(gui))
    
    # Run the GUI in the main thread
    gui.run()

    # Start the event loop
    loop.run_forever()
