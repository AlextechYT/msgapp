import os
import socket
import subprocess
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, ttk
from threading import Thread
import requests  # New import for making API calls
import json
import time

BROADCAST_PORT = 5555
BUFFER_SIZE = 1024
THEME_FILE = "theme_settings.json"  # File to store theme settings
API_BASE_URL = "https://api.atdevs.org"  # Base URL for API

# Helper function to get the local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

# Function to broadcast the username on the network
def broadcast_username(username):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    broadcast_message = json.dumps({"username": username})
    while True:
        udp_socket.sendto(broadcast_message.encode(), ('<broadcast>', BROADCAST_PORT))
        time.sleep(5)  # Broadcast every 5 seconds

# Function to listen for other clients on the network
def listen_for_broadcasts(known_users, local_username):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind(('', BROADCAST_PORT))

    while True:
        message, addr = udp_socket.recvfrom(BUFFER_SIZE)
        try:
            data = json.loads(message.decode())
            username = data.get("username")
            if username and username != local_username:
                known_users[username] = addr[0]
                print(f"Discovered user {username} at {addr[0]}")
        except Exception as e:
            print(f"Error decoding broadcast: {e}")

# Register a new user
def register_user(username, password):
    url = f"{API_BASE_URL}/user/register"
    payload = {"username": username, "password": password}
    response = requests.post(url, json=payload)
    return response.status_code == 200  # True if registration was successful

# Get the public key of a user
def get_public_key(username):
    url = f"{API_BASE_URL}/publickey/{username}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Send a message to a user
def send_message_api(from_user, to_user, message):
    url = f"{API_BASE_URL}/message/send"
    payload = {"from": from_user, "to": to_user, "message": message}
    response = requests.post(url, json=payload)
    return response.status_code == 200  # True if message was sent successfully

# Receive messages for a user
def receive_messages(username):
    url = f"{API_BASE_URL}/message/receive/{username}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

# Broadcast a message to all users
def broadcast_message():
    url = f"{API_BASE_URL}/user/broadcast"
    response = requests.get(url)
    return response.status_code == 200  # True if broadcast was successful

# Update user settings
def update_user_settings(username, theme):
    url = f"{API_BASE_URL}/user/settings"
    payload = {"username": username, "theme": theme}
    response = requests.put(url, json=payload)
    return response.status_code == 200  # True if settings were updated

# Start the update checker process
def start_update_checker():
    updater_script = 'client_update.py'
    updater_executable = 'client_update.exe'

    if os.path.exists(updater_script):
        subprocess.Popen(["python", updater_script], shell=True)
    elif os.path.exists(updater_executable):
        subprocess.Popen([updater_executable], shell=True)
    else:
        print("No update script found.")

# Load theme settings from JSON file
def load_theme_settings():
    if os.path.exists(THEME_FILE):
        with open(THEME_FILE, 'r') as f:
            return json.load(f)
    return {"theme": "light"}  # Default theme

# Save theme settings to JSON file
def save_theme_settings(theme):
    with open(THEME_FILE, 'w') as f:
        json.dump({"theme": theme}, f)

# Main messaging app class
class MessagingApp:
    def __init__(self, username):
        self.username = username
        self.known_users = {}  # Discovered users on LAN
        self.theme = load_theme_settings()["theme"]  # Load theme setting
        self.init_gui()
        self.start_broadcast_listener()

    # Initialize GUI
    def init_gui(self):
        self.root = tk.Tk()
        self.root.title(f"Messaging App - {self.username}")

        self.chat_window = scrolledtext.ScrolledText(self.root, width=50, height=20)
        self.chat_window.pack(padx=10, pady=10)
        self.chat_window.config(state=tk.DISABLED)

        self.entry = tk.Entry(self.root, width=40)
        self.entry.pack(side=tk.LEFT, padx=10, pady=10)

        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.register_button = tk.Button(self.root, text="Register", command=self.register)
        self.register_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.settings_button = tk.Button(self.root, text="Update Settings", command=self.update_settings)
        self.settings_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.root.quit()

    # Start a thread to broadcast username and listen for broadcasts
    def start_broadcast_listener(self):
        Thread(target=broadcast_username, args=(self.username,), daemon=True).start()
        Thread(target=listen_for_broadcasts, args=(self.known_users, self.username), daemon=True).start()

    # Send a message
    def send_message(self):
        recipient = simpledialog.askstring("Recipient", "Enter recipient username:")
        if recipient:
            message = self.entry.get()
            self.entry.delete(0, tk.END)

            if recipient in self.known_users:
                # Send message over LAN
                send_lan_message(self.known_users[recipient], self.username, message)
                self.add_message(f"You to {recipient}: {message}")
            else:
                # Send message over the API
                if send_message_api(self.username, recipient, message):
                    self.add_message(f"You to {recipient} (API): {message}")
                else:
                    messagebox.showerror("Error", "Failed to send message via API.")

    def register(self):
        username = simpledialog.askstring("Register", "Enter a username:")
        password = simpledialog.askstring("Register", "Enter a password:", show='*')
        if username and password:
            if register_user(username, password):
                messagebox.showinfo("Success", "Registration successful!")
            else:
                messagebox.showerror("Error", "Registration failed. Username might be taken.")

    def update_settings(self):
        theme = simpledialog.askstring("Update Settings", "Enter new theme:")
        if theme:
            if update_user_settings(self.username, theme):
                messagebox.showinfo("Success", "Settings updated successfully!")
                save_theme_settings(theme)  # Save the new theme
            else:
                messagebox.showerror("Error", "Failed to update settings.")

    # Add a message to the chat window
    def add_message(self, message):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.insert(tk.END, message + "\n")
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.yview(tk.END)

# Run the app
if __name__ == "__main__":
    username = simpledialog.askstring("Username", "Enter your username:")
    if username:
        app = MessagingApp(username)
        app.root.mainloop()
