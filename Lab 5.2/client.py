# Ong_CH_LE5.2_client.py
# Name: Christel Hope S. Ong
# CMSC 137 - LE5.2 (Client)

import socket
import threading
from prompt_toolkit import PromptSession, prompt            # prompt = asterisks + clean typing line
from prompt_toolkit.patch_stdout import patch_stdout        # new messages appear ABOVE what you are typing

# ================= SETTINGS =================
PORT = 65432            # must be the same as the server's port

# Public keys (e, n) of everyone. Public keys are safe to share.
# NEVER write a private key in this file.
PUBLIC_KEYS = {
    "chong": (247, 5963),
    "nelle": (89, 8213),
    "mm": (637, 2479),
}

SOLO_TEST = False      # True = also encrypt a copy for myself, so I can test alone with 2 terminals
                        # (if you made necessary changes, set it back to False before pushing)


# ================= RSA AND MESSAGE FORMAT =================
def encrypt(text, e, n):
    #RSA encrypt: each character's number is raised to e, then mod n (c = m^e mod n)
    return " ".join(str(pow(ord(ch), e, n)) for ch in text)


def decrypt(cipher, d, n):
    #RSA decrypt: each number is raised to d, then mod n (m = c^d mod n), back to text
    return "".join(chr(pow(int(num), d, n)) for num in cipher.split())


def build_line(text, partners, sender):
    #Makes ONE line: who sent it, then an encrypted copy of the text for every partner.
    #Format:  from=sender|name=numbers|name=numbers
    copies = "|".join(f"{name}={encrypt(text, e, n)}" for name, (e, n) in partners.items())
    return f"from={sender}|{copies}"


def find_my_copy(line, my_name):
    #Looks through the line for the copy meant for me. Returns None if there is none
    #(the "from=..." part never matches a recipient name, so it is skipped)
    for part in line.split("|"):
        name, _, cipher = part.partition("=")
        if name == my_name:
            return cipher
    return None


# ================= RECEIVING (runs in its own thread) =================
def receive_messages(client, my_name, d, n):
    #Constantly listens for lines from the server, then decrypts my copy
    reader = client.makefile("r", encoding="utf-8")      # reads one full line at a time
    try:
        for line in reader:
            cipher = find_my_copy(line.strip(), my_name)
            if cipher:
                #print(f"\n [Encrypted] {cipher}")                   # what travelled (unreadable)
                print(f"\n {decrypt(cipher, d, n)}")    # readable text
    except OSError:
        pass
    print("Disconnected from the server. Ctrl + C to exit.")


# ================= MAIN =================
def main():
    # Ask who I am and where the server is (no command-line arguments needed)
    host = input("Server IP (press Enter for 127.0.0.1): ").strip() or "127.0.0.1"
    while True:
        my_name = input(f"Enter your name ({', '.join(PUBLIC_KEYS)}): ").strip().lower()
        if my_name in PUBLIC_KEYS:
            break
        print(f"Unknown name '{my_name}'. Choose from: {', '.join(PUBLIC_KEYS)}")
    nickname = my_name                     # the name is also the nickname shown in messages

    my_e, my_n = PUBLIC_KEYS[my_name]
    # everyone I will encrypt for (all the others; myself too only when testing alone)
    partners = {name: key for name, key in PUBLIC_KEYS.items() if SOLO_TEST or name != my_name}
    limit = min(n for e, n in PUBLIC_KEYS.values())      # a character's number must be below every n

    # Ask for the private key (asterisks) and check it BEFORE connecting:
    # encrypt 65 with my public key, then decrypt it with the typed key. We must get 65 back.
    while True:
        typed = prompt("Enter your private key: ", is_password=True).strip()
        if typed.isascii() and typed.isdigit() and pow(pow(65, my_e, my_n), int(typed), my_n) == 65:
            my_d = int(typed)                  # kept in memory only, never saved anywhere
            break
        print("Wrong private key, try again.")

    # Connect (sir's code)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, PORT))
    except OSError as err:
        print(f"Could not connect to {host}:{PORT} ({err}).")
        return
    print(f"Connected as {my_name}. Type a message and press Enter.")

    session = PromptSession()
    with patch_stdout():                       # lets the thread print without breaking my typing
        threading.Thread(target=receive_messages, args=(client, my_name, my_d, my_n),
                         daemon=True).start()
        while True:
            try:
                text = session.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            full_message = f"{nickname}: {text}"                 # format message with nickname
            if any(ord(ch) >= limit for ch in full_message):
                print("Some characters can't be encrypted (emoji or special symbols). Try again.")
                continue
            try:
                client.sendall((build_line(full_message, partners, my_name) + "\n").encode("utf-8"))
            except OSError:
                break
    client.close()


if __name__ == "__main__":
    main()