# receiver.py
# Name: Marinelle Joan U. Tambolero
# CMSC 137 - LE5.1 (receiver)

import socket
from crc_module import mod2div

SHARED_KEY = "1001"                                                      # the shared key used for CRC error detection
CRC_BITS = len(SHARED_KEY) - 1                                           # number of CRC bits
HOST = "127.0.0.1"
PORT = 65432                                                              # must match the sender's port

# convert string of bits to text (8 bits = 1 character)
def bits_to_text(bits):
    text = ""
    for i in range(0, len(bits), 8):
        text += chr(int(bits[i:i+8], 2))                                # takes 8 bits at a time, converts to decimal, then to ASCII character
    return text


def combined_votes(votes_by_area, extra_votes=None):
    # add nominee vote counts from every area into one totals dictionary
    totals = {}
    for area_votes in votes_by_area.values():
        for name, count in area_votes.items():
            totals[name] = totals.get(name, 0) + count

    if extra_votes:
        for name, count in extra_votes.items():
            totals[name] = totals.get(name, 0) + count

    return totals


def show_results(votes, eligible_by_area, title="Combined results across areas"):
    total_votes = sum(votes.values())
    total_eligible = sum(eligible_by_area.values())

    print(f"\n----- {title} -----")

    if not votes:
        print("No votes received yet.")
        return

    ranked = sorted(votes.items(), key=lambda item: item[1], reverse=True)
    for rank, (name, count) in enumerate(ranked, start=1):
        percentage = count / total_votes * 100 if total_votes else 0
        print(f"Rank {rank}: {name} with {count} votes ({percentage:.2f}%)")

    print(f"Total votes: {total_votes}")
    print(f"Total eligible voters across areas: {total_eligible}")
    if total_eligible:
        print(f"Voters who voted: {total_votes / total_eligible * 100:.2f}%")

def reject(conn, reason):
    conn.sendall(f"NACK: {reason}\n".encode("utf-8"))
    print(f"[Receiver] Rejected sender: {reason}")

def handle_sender(conn, address, votes_by_area, eligible_by_area):
    # receive one sender's complete area report, then add it to shared totals
    print(f"[Receiver] Connected to: {address}")

    area = None
    eligible = None
    session_votes = {}
    done = False
    error = False

    reader = conn.makefile("r", encoding="utf-8")
    for line in reader:
        bits = line.strip()

        if len(bits) < 8 + CRC_BITS or any(bit not in "01" for bit in bits):
            reject(conn, "Data corrupted")
            error = True
            break

        if "1" in mod2div(bits, SHARED_KEY):
            reject(conn, "Data corrupted")
            error = True
            break

        text = bits_to_text(bits[:-CRC_BITS])
        print(f"[Receiver] Received text: {text}")
        parts = text.split("|")

        try:
            if parts[0] == "AREA" and len(parts) == 2:
                area = parts[1]
                if not area:
                    raise ValueError

            elif parts[0] == "ELIGIBLE" and len(parts) == 2:
                eligible = int(parts[1])
                if eligible < 1:
                    raise ValueError

            elif parts[0] == "VOTE" and len(parts) == 3:
                if area is None or eligible is None:
                    reject(conn, "Area and eligible voter count must come before votes")
                    error = True
                    break

                name = parts[1]
                count = int(parts[2])
                if not name or count < 0:
                    raise ValueError

                # compare this area's previous votes plus this sender's new votes
                # against the eligible count for this area.
                previous_area_votes = votes_by_area.get(area, {})
                proposed_area_total = (
                    sum(previous_area_votes.values())
                    + sum(session_votes.values())
                    + count
                )
                if proposed_area_total > eligible:
                    reject(conn, "Votes exceed eligible voters for this area")
                    error = True
                    break

                session_votes[name] = session_votes.get(name, 0) + count

            elif parts[0] == "DONE" and len(parts) == 1:
                if area is None or eligible is None or not session_votes:
                    reject(conn, "Incomplete report")
                    error = True
                    break
                done = True

            else:
                reject(conn, "Invalid message format")
                error = True
                break

        except ValueError:
            reject(conn, "Invalid area, eligible count, or vote count")
            error = True
            break

        conn.sendall("ACK: Line received\n".encode("utf-8"))

        if parts[0] == "VOTE":
            preview_votes = combined_votes(votes_by_area, session_votes)
            preview_eligible = dict(eligible_by_area)
            preview_eligible[area] = eligible
            show_results(preview_votes, preview_eligible, "Live combined results across areas")

        if done:
            break

    if done and not error:
        area_totals = votes_by_area.setdefault(area, {})
        for name, count in session_votes.items():
            area_totals[name] = area_totals.get(name, 0) + count

        # Keep one eligible-voter count per area, so a repeat report for the
        # same area does not count that area's eligible voters twice.
        eligible_by_area[area] = eligible

        print(f"[Receiver] Area {area} report accepted.")
        show_results(combined_votes(votes_by_area), eligible_by_area)
    elif not error:
        print("[Receiver] Sender disconnected before DONE; this report was discarded.")

    reader.close()

# main function to run the receiver server
def run_receiver():
    votes_by_area = {}
    eligible_by_area = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[Receiver] Listening on {HOST}:{PORT}...")
        print("[Receiver] Start sender.py in another terminal. Press Ctrl+C to stop.")

        try:
            while True:
                conn, address = server_socket.accept()
                with conn:
                    handle_sender(conn, address, votes_by_area, eligible_by_area)
        except KeyboardInterrupt:
            print("\n[Receiver] Server stopped.")


if __name__ == "__main__":
    run_receiver()
