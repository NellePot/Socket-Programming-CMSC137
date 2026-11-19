# receiver.py
# Name: Marinelle Joan U. Tambolero
# CMSC 137 - LE5.1 (receiver)

import socket
import threading
from crc_module import mod2div

SHARED_KEY = "1001"                                                      # the shared key used for CRC error detection
CRC_BITS = len(SHARED_KEY) - 1                                           # number of CRC bits
HOST = "127.0.0.1"
PORT = 65432                                                              # must match the sender's port

# convert string of bits to text (8 bits = 1 character)
def bits_to_text(bits):
    return "".join(chr(int(bits[i:i + 8], 2)) for i in range(0, len(bits), 8))

def combined_votes(votes_by_area):
    # add nominee vote counts from every area into one totals dictionary
    totals = {}
    for area_votes in votes_by_area.values():
        for name, count in area_votes.items():
            totals[name] = totals.get(name, 0) + count
    return totals

def live_votes(votes_by_area, pending_by_area):
    # include completed reports and valid vote lines from active senders
    totals = combined_votes(votes_by_area)
    for area_votes in pending_by_area.values():
        for name, count in area_votes.items():
            totals[name] = totals.get(name, 0) + count
    return totals

def show_results(votes, eligible_by_area, title):
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

def add_area_to_eligibles(eligible_by_area, active_eligibles):
    # count each area once, including areas with a report still in progress
    result = dict(eligible_by_area)
    for area, senders in active_eligibles.items():
        if area not in result and senders:
            result[area] = next(iter(senders.values()))
    return result

def remove_pending(area, session_votes, session_id, pending_by_area, active_eligibles):
    # release this sender's uncommitted votes and area registration
    if area is not None and area in pending_by_area:
        area_pending = pending_by_area[area]
        for name, count in session_votes.items():
            remaining = area_pending.get(name, 0) - count
            if remaining > 0:
                area_pending[name] = remaining
            else:
                area_pending.pop(name, None)
        if not area_pending:
            pending_by_area.pop(area, None)

    if area is not None and area in active_eligibles:
        active_eligibles[area].pop(session_id, None)
        if not active_eligibles[area]:
            active_eligibles.pop(area, None)

def handle_sender(conn, address, votes_by_area, eligible_by_area,
                  pending_by_area, active_eligibles, state_lock, output_lock):
    # handle one sender in its own thread; accepted votes appear immediately
    session_id = object()
    area = None
    eligible = None
    session_votes = {}
    done = False
    error = False

    with output_lock:
        print(f"[Receiver] Connected to: {address}")

    reader = conn.makefile("r", encoding="utf-8")
    try:
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
            parts = text.split("|")
            with output_lock:
                print(f"[Receiver] Received text from {address}: {text}")

            try:
                if parts[0] == "AREA" and len(parts) == 2:
                    area = parts[1]
                    if not area:
                        raise ValueError

                elif parts[0] == "ELIGIBLE" and len(parts) == 2:
                    if area is None:
                        reject(conn, "Area code must come before eligible voters")
                        error = True
                        break

                    eligible = int(parts[1])
                    if eligible < 1:
                        raise ValueError

                    with state_lock:
                        known_eligible = eligible_by_area.get(area)
                        active_values = set(active_eligibles.get(area, {}).values())
                        if ((known_eligible is not None and known_eligible != eligible)
                                or (active_values and active_values != {eligible})):
                            reject(conn, "Eligible voter count does not match this area")
                            error = True
                            break
                        active_eligibles.setdefault(area, {})[session_id] = eligible

                elif parts[0] == "VOTE" and len(parts) == 3:
                    if area is None or eligible is None:
                        reject(conn, "Area and eligible voter count must come before votes")
                        error = True
                        break

                    name = parts[1]
                    count = int(parts[2])
                    if not name or count < 0:
                        raise ValueError

                    with state_lock:
                        committed = votes_by_area.get(area, {})
                        pending = pending_by_area.get(area, {})
                        proposed_total = sum(committed.values()) + sum(pending.values()) + count
                        if proposed_total > eligible:
                            reject(conn, "Votes exceed eligible voters for this area")
                            error = True
                            break

                        session_votes[name] = session_votes.get(name, 0) + count
                        pending_by_area.setdefault(area, {})[name] = pending.get(name, 0) + count
                        votes_snapshot = live_votes(votes_by_area, pending_by_area)
                        eligible_snapshot = add_area_to_eligibles(eligible_by_area, active_eligibles)

                    with output_lock:
                        show_results(votes_snapshot, eligible_snapshot,
                                     "Live combined results across areas")

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
            if done:
                break

    except (ConnectionError, OSError) as exc:
        with output_lock:
            print(f"[Receiver] Connection problem with {address}: {exc}")
        error = True
    finally:
        reader.close()
        conn.close()

    with state_lock:
        if done and not error:
            remove_pending(area, session_votes, session_id, pending_by_area, active_eligibles)
            area_totals = votes_by_area.setdefault(area, {})
            for name, count in session_votes.items():
                area_totals[name] = area_totals.get(name, 0) + count
            eligible_by_area[area] = eligible
            votes_snapshot = live_votes(votes_by_area, pending_by_area)
            eligible_snapshot = add_area_to_eligibles(eligible_by_area, active_eligibles)
        else:
            remove_pending(area, session_votes, session_id, pending_by_area, active_eligibles)
            votes_snapshot = live_votes(votes_by_area, pending_by_area)
            eligible_snapshot = add_area_to_eligibles(eligible_by_area, active_eligibles)

    with output_lock:
        if done and not error:
            print(f"[Receiver] Area {area} report accepted.")
            show_results(votes_snapshot, eligible_snapshot, "Combined results across areas")
        elif not error:
            print(f"[Receiver] {address} disconnected before DONE; its unfinished report was discarded.")


# main function to run the receiver server
def run_receiver():
    votes_by_area = {}
    eligible_by_area = {}
    pending_by_area = {}
    active_eligibles = {}
    state_lock = threading.Lock()
    output_lock = threading.Lock()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[Receiver] Listening on {HOST}:{PORT}...")
        print("[Receiver] Start one or more sender.py programs. Press Ctrl+C to stop.")

        try:
            while True:
                conn, address = server_socket.accept()
                thread = threading.Thread(
                    target=handle_sender,
                    args=(conn, address, votes_by_area, eligible_by_area,
                          pending_by_area, active_eligibles, state_lock, output_lock),
                    daemon=True,
                )
                thread.start()
        except KeyboardInterrupt:
            print("\n[Receiver] Server stopped.")


if __name__ == "__main__":
    run_receiver()
