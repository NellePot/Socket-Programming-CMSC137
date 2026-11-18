import socket
import sys
import threading

# Reads ONE key press without showing it (needed for the *).
# Windows uses msvcrt; Mac/Linux use termios. No extra install needed.
try:
    import msvcrt

    def get_key():
        return msvcrt.getwch()
except ImportError:
    import termios
    import tty

    def get_key():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)                     # raw mode: one key at a time, nothing echoed
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ================= SETTINGS =================
PORT = 65432            # must be the same as the server's port
                        # host can be typed in the terminal
PUBLIC_KEYS = {
    "chong": (247, 5963),
    "nelle": (89, 8213),
    "mm": (637, 2479),
}

SOLO_TEST = False      # True = also encrypt a copy for myself, so I can test alone with 2 terminals with MY private key


# ================= RSA AND MESSAGE FORMAT =================
def encrypt(text, e, n):
    #RSA encrypt: each character's number is raised to e, then mod n (c = m^e mod n)
    return " ".join(str(pow(ord(ch), e, n)) for ch in text)


def decrypt(cipher, d, n):
    #RSA decrypt: each number is raised to d, then mod n (m = c^d mod n), back to text
    return "".join(chr(pow(int(num), d, n)) for num in cipher.split())


def build_line(text, partners):
    #Makes ONE line holding an encrypted copy of the text for every partner
    #Format:  name=numbers|name=numbers
    return "|".join(f"{name}={encrypt(text, e, n)}" for name, (e, n) in partners.items())


def find_my_copy(line, my_name):
    #Looks through the line for the copy meant for me. Returns None if there is none
    for part in line.split("|"):
        name, _, cipher = part.partition("=")
        if name == my_name:
            return cipher
    return None


def ask_private_key():
    #Asks for the private key and shows * for every digit typed
    print("Enter your private key: ", end="", flush=True)
    digits = ""
    while True:
        key = get_key()
        if key in ("\r", "\n"):                  # Enter = done
            break
        if key == "\x03":                        # Ctrl+C
            raise KeyboardInterrupt
        if key in ("\b", "\x7f"):                # Backspace = remove the last digit
            if digits:
                digits = digits[:-1]
                print("\b \b", end="", flush=True)
        elif key.isdigit():
            digits += key
            print("*", end="", flush=True)       # show * instead of the digit
    print()
    return digits


# ================= RECEIVING (runs in its own thread) =================
def receive_messages(client, my_name, d, n):
    #Constantly listens for lines from the server, then decrypts my copy
    reader = client.makefile("r", encoding="utf-8")      # reads one full line at a time
    try:
        for line in reader:
            cipher = find_my_copy(line.strip(), my_name)
            if cipher:
             #   print(f"\n [Encrypted] {cipher}")                   # what travelled (unreadable)
                print(f"\n{decrypt(cipher, d, n)}")    # readable text
            else:
                print(f"[Notice] A message arrived with no copy for '{my_name}'. "
                      "Each laptop must use its OWN name.")
    except OSError:
        pass
    print("Disconnected from the server. Press Enter to exit.")


# ================= MAIN =================
def main():
    # Who am I, and where is the server?
    # Name and server IP: typed after the file name, or asked here (for the Run button)
    if len(sys.argv) > 1:
        my_name = sys.argv[1].lower()
    else:
        my_name = input(f"\nYour name ({'/'.join(PUBLIC_KEYS)}): ").strip().lower()
    if len(sys.argv) > 2:
        host = sys.argv[2]
    else:
        host = input("Server IP (just press Enter if the server is on this laptop): ").strip() or "127.0.0.1"
    if my_name not in PUBLIC_KEYS:
        sys.exit(f"Unknown name '{my_name}'. Choose from: {', '.join(PUBLIC_KEYS)}")

    my_e, my_n = PUBLIC_KEYS[my_name]
    # everyone I will encrypt for (all the others; myself too only when testing alone)
    partners = {name: key for name, key in PUBLIC_KEYS.items() if SOLO_TEST or name != my_name}
    limit = min(n for e, n in PUBLIC_KEYS.values())      # a character's number must be below every n

    nickname = input("Choose your nickname: ")

    # Ask for the private key (asterisks) and check it BEFORE connecting:
    # encrypt 65 with my public key, then decrypt it with the typed key. We must get 65 back.
    while True:
        typed = ask_private_key()
        if typed.isascii() and typed.isdigit() and pow(pow(65, my_e, my_n), int(typed), my_n) == 65:
            my_d = int(typed)                  # kept in memory only, never saved anywhere
            break
        print("Wrong private key, try again.")

    # Connect (sir's code)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, PORT))
    print(f"\nConnected as '{my_name}'. Type a message and press Enter. Ctrl+C to quit.\n")

    threading.Thread(target=receive_messages, args=(client, my_name, my_d, my_n),
                     daemon=True).start()
    while True:
        try:
            text = input("").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        full_message = f"{nickname}: {text}\n"                 # format message with nickname
        if any(ord(ch) >= limit for ch in full_message):
            print("\nSome characters can't be encrypted (emoji or special symbols). Try again.")
            continue
        try:
            client.sendall((build_line(full_message, partners) + "\n").encode("utf-8"))
        except OSError:
            break
    client.close()


if __name__ == "__main__":
    main()