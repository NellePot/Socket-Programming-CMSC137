# client.py
# Name: CHRISTEL HOPE ONG
# CMSC 141 - LE5.2 (RSA chat client)
#
# Based on sir's client.py (chat client with a receive thread and a write thread).
# Added: private key prompt with asterisks, RSA encryption of outgoing
# messages, and RSA decryption of incoming messages.
#
# HOW THE CHAT WORKS: client -> server -> client
#   The server only relays the messages, so it only ever sees unreadable numbers.
#   Encrypt with the PARTNER's public key, decrypt with MY private key.
#
# HOW TO USE THIS FILE (each member):
#   1. Set MY_NAME below to your own name from PUBLIC_KEYS.
#   2. Set HOST to the IP of the laptop running server.py.
#   3. Run: python client.py   (the server must already be running)
 
import socket
import threading
import msvcrt          # Windows only: lets us read one key press at a time
 
# ================= SETTINGS (edit these) =================
HOST = '127.0.0.1'     # IP of the laptop running server.py (same laptop = 127.0.0.1)
PORT = 55555           # must be the same as the server's port
 
MY_NAME = "chong" # <-- CHANGE THIS to your own name: "chong", "nelle", or "mm"
 
# Public keys (e, n) of everyone. Public keys are safe to share.
# NEVER write a private key in this file.
PUBLIC_KEYS = {
    "chong": (247, 5963),
    "nelle": (89, 8213),
    "mm": (637, 2479),
}
 
MY_E, MY_N = PUBLIC_KEYS[MY_NAME]                       # my own public key
PARTNERS = {name: key for name, key in PUBLIC_KEYS.items() if name != MY_NAME}
 
# For SOLO TEST ONLY (testing alone with two terminals):
    # uncomment the next line, and re-comment it before pushing to GitHub
#PARTNERS[MY_NAME] = PUBLIC_KEYS[MY_NAME]
 
 
# ================= RSA AND KEY PROMPT =================
def ask_private_key():
    """Asks for the private key and shows * for every digit typed."""
    while msvcrt.kbhit():                      # throw away leftover key presses (like an old Enter)
        msvcrt.getwch()
    print("Enter your private key: ", end="", flush=True)
    digits = ""
    while True:
        key = msvcrt.getwch()                  # read one key without showing it
        if key in ("\r", "\n"):                # Enter = done
            break
        if key == "\b":                        # Backspace = remove the last digit
            if digits:
                digits = digits[:-1]
                print("\b \b", end="", flush=True)
        elif key.isdigit():
            digits += key
            print("*", end="", flush=True)     # show * instead of the digit
    print()
    return digits
 
 
def encrypt(text, e, n):
    """RSA encrypt: each character's number is raised to e, then mod n (c = m^e mod n)."""
    return " ".join(str(pow(ord(ch), e, n)) for ch in text)
 
 
def decrypt(cipher, d, n):
    """RSA decrypt: each number is raised to d, then mod n (m = c^d mod n), back to text."""
    return "".join(chr(pow(int(num), d, n)) for num in cipher.split())
 
 
# ================= BEFORE CONNECTING =================
nickname = input("Choose your nickname: ")
 
# Pick who we are chatting with; their public key is used to encrypt our messages
partner = ""
while partner not in PARTNERS:
    partner = input(f"Who are you chatting with? ({'/'.join(PARTNERS)}): ").lower()
PARTNER_E, PARTNER_N = PARTNERS[partner]
 
# Ask for the private key (asterisks) and check it before connecting:
# encrypt 65 with my public key, then decrypt it with the typed key. We must get 65 back.
while True:
    typed = ask_private_key()
    if typed and pow(pow(65, MY_E, MY_N), int(typed), MY_N) == 65:
        MY_D = int(typed)                      # kept in memory only, never saved anywhere
        break
    print("Wrong private key, try again.")
 
# ================= CONNECT (sir's code - revised) =================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
 
 
def receive_messages():
    """Constantly listens for messages from the server, then decrypts them."""
    reader = client.makefile('r', encoding='utf-8')    # reads one full line at a time, received and decode data from server
    while True:
        try:
            line = reader.readline()
            if not line:                               # server closed the connection
                break
            print(f"[Encrypted] {line.strip()}")                  # what travelled (unreadable)
            print(f"[Decrypted] {decrypt(line, MY_D, MY_N)}")     # readable text
        except Exception:
            break
    print("An error occurred! Disconnecting...")
    client.close()
 
 
def write_messages():
    """Constantly waits for user input, encrypts it, and sends it."""
    while True:
        try:
            user_input = input("")
            full_message = f"{nickname}: {user_input}"                 #format mssg with nickname           
            encrypted = encrypt(full_message, PARTNER_E, PARTNER_N)    # encrypt for the partner
            print(f"[Sent encrypted] {encrypted}")
            client.send((encrypted + "\n").encode('utf-8'))            # "\n" marks the end
        except Exception:
            client.close()
            break
 
 
# Start thread for receiving messages 
receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()
 
# Start thread for sending messages 
write_thread = threading.Thread(target=write_messages)
write_thread.start()
 