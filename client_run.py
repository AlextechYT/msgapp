import os
import socket
import subprocess
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, ttk
from threading import Thread
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import json
import time

BROADCAST_PORT = 5555
BUFFER_SIZE = 1024
THEME_FILE = "theme_settings.json"  # File to store theme settings

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

# Generate RSA key pair
def generate_rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key

# Encrypt a message using a public key (RSA)
def encrypt_message_rsa(public_key, message):
    encrypted = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode()

# Decrypt a message using a private key (RSA)
def decrypt_message_rsa(private_key, encrypted_message):
    encrypted_message = base64.b64decode(encrypted_message)
    decrypted = private_key.decrypt(
        encrypted_message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return decrypted.decode()

# Generate AES key for symmetric encryption
def generate_aes_key():
    return os.urandom(32)  # 256-bit key

# Encrypt a message using AES
def encrypt_message_aes(aes_key, message):
    iv = os.urandom(16)  # 128-bit IV
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(message.encode()) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode()

# Decrypt a message using AES
def decrypt_message_aes(aes_key, encrypted_message):
    encrypted_message = base64.b64decode(encrypted_message)
    iv = encrypted_message[:16]
    ciphertext = encrypted_message[16:]
    cipher = Cipher(algorithms.AES(aes_key), modes.CFB(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

# Share public keys and establish session key (E2EE)
def establish_session_key(my_private_key, other_public_key):
    aes_key = generate_aes_key()
    encrypted_aes_key = encrypt_message_rsa(other_public_key, base64.b64encode(aes_key).decode())
    return aes_key, encrypted_aes_key

# Send message directly to a user on the LAN
def send_lan_message(recipient_ip, username, encrypted_message):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            payload = json.dumps({
                "from": username,
                "message": encrypted_message
            })
            sock.sendto(payload.encode(), (recipient_ip, BROADCAST_PORT))
            print("LAN message sent.")
    except Exception as e:
        print(f"Error sending LAN message: {e}")

# Start the update checker process
def start_update_checker():
    # Check for both .py and .exe files
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
        self.private_key, self.public_key = generate_rsa_key_pair()
        self.contacts = {}  # Stores session keys for each contact
        self.known_users = {}  # Discovered users on LAN
        self.theme = load_theme_settings()["theme"]  # Load theme setting
        self.init_gui()
        self.start_broadcast_listener()

    # Initialize GUI
    def init_gui(self):
        self.root = tk.Tk()
        self.root.title(f"Messaging App - {self.username}")

        # Initialize the chat window first
        self.chat_window = scrolledtext.ScrolledText(self.root, width=50, height=20)
        self.chat_window.pack(padx=10, pady=10)
        self.chat_window.config(state=tk.DISABLED)

        self.entry = tk.Entry(self.root, width=40)
        self.entry.pack(side=tk.LEFT, padx=10, pady=10)

        self.send_button = tk.Button(self.root, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Dark/Light mode toggle
        self.toggle_button = tk.Button(self.root, text="Toggle Dark/Light Mode", command=self.toggle_theme)
        self.toggle_button.pack(pady=10)

        # Set the theme based on the stored setting after initializing all GUI components
        self.update_theme()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.root.quit()

    # Start a thread to broadcast username and listen for broadcasts
    def start_broadcast_listener(self):
        Thread(target=broadcast_username, args=(self.username,), daemon=True).start()
        Thread(target=listen_for_broadcasts, args=(self.known_users, self.username), daemon=True).start()

    # Add a message to the chat window
    def add_message(self, message):
        self.chat_window.config(state=tk.NORMAL)
        self.chat_window.insert(tk.END, message + "\n")
        self.chat_window.config(state=tk.DISABLED)
        self.chat_window.yview(tk.END)

    # Retrieve or establish session key for a recipient
    def get_session_key(self, recipient):
        if recipient in self.contacts:
            return self.contacts[recipient], None
        else:
            # Fetch recipient's public key from the server (not implemented)
            recipient_public_key = self.public_key  # For now, using self's public key for testing
            aes_key, encrypted_aes_key = establish_session_key(self.private_key, recipient_public_key)
            self.contacts[recipient] = aes_key
            return aes_key, encrypted_aes_key

    # Send a message
    def send_message(self):
        recipient = simpledialog.askstring("Recipient", "Enter recipient username:")
        if recipient:
            message = self.entry.get()
            self.entry.delete(0, tk.END)

            if recipient in self.known_users:
                # Send message over LAN (LAN message)
                aes_key, encrypted_aes_key = self.get_session_key(recipient)
                encrypted_message = encrypt_message_aes(aes_key, message)
                send_lan_message(self.known_users[recipient], self.username, encrypted_message)
                self.add_message(f"You to {recipient}: {message}")
            else:
                messagebox.showwarning("Warning", f"{recipient} not found in known users.")

    # Toggle theme between light and dark
    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        save_theme_settings(self.theme)
        self.update_theme()

    # Update GUI theme
    def update_theme(self):
        if self.theme == "dark":
            self.root.config(bg="black")
            self.chat_window.config(bg="gray", fg="white")
            self.entry.config(bg="darkgray", fg="white")
            self.send_button.config(bg="gray", fg="white")
            self.toggle_button.config(bg="gray", fg="white")
        else:
            self.root.config(bg="white")
            self.chat_window.config(bg="white", fg="black")
            self.entry.config(bg="white", fg="black")
            self.send_button.config(bg="lightgray", fg="black")
            self.toggle_button.config(bg="lightgray", fg="black")

# Run the app
if __name__ == "__main__":
    username = simpledialog.askstring("Username", "Enter your username:")
    if username:
        app = MessagingApp(username)
        app.root.mainloop()
