import socket
import sys
import threading

HOST = "localhost"
PORT = 8080

clients: dict[str, socket.socket] = {}
clients_lock: threading.Lock = threading.Lock()
server_running = True

def print_log(msg: str):
    print(f"[{threading.current_thread().name}] {msg}")

def get_clients() -> str:
    with clients_lock:
        return ", ".join(clients.keys()) if clients else "No users connected"

def shutdown_server(s: socket.socket):
    global server_running
    server_running = False
    with clients_lock:
        for client_socket in list(clients.values()):
            try:
                client_socket.close()
            except Exception as e:
                print_log(f"Error closing client socket: {e}")
    try:
        s.close()
    except Exception as e:
        print_log(f"Error closing server socket: {e}")

def recv_message(client_socket: socket.socket) -> str:
    try:
        msg = client_socket.recv(1024).decode().strip()
        if not msg:
            return None
        print_log(f"Received message: {msg}")
        return msg
    except (ConnectionResetError, BrokenPipeError):
        print_log("Client connection lost")
        return None
    except UnicodeDecodeError:
        print_log("Received invalid message encoding")
        return None
    except Exception as e:
        print_log(f"Error receiving message: {e}")
        return None

def send_message(client_socket: socket.socket, msg: str) -> bool:
    try:
        client_socket.sendall(msg.encode())
        print_log(f"Message sent: {msg}")
        return True
    except (BrokenPipeError, ConnectionResetError):
        print_log("Client disconnected before message could be sent")
        return False
    except Exception as e:
        print_log(f"Error sending message: {e}")
        return False

def notify_clients(msg: str, exclude: str = None):
    for client_username, client_socket in clients.items():
        if client_username == exclude:
            continue
        send_message(client_socket, msg)

def handle_client(client_socket: socket.socket, addr):
    client_username = None
    try:
        client_username = recv_message(client_socket)
        if not client_username:
            send_message(client_socket, "Please provide a username")
            return

        # Validate username
        client_username = client_username.strip()
        if not client_username:
            send_message(client_socket, "Username cannot be empty")
            return
        if client_username.lower() == "/list":
            send_message(client_socket, "Invalid username")
            return

        with clients_lock:
            if client_username in clients:
                send_message(client_socket, "Username already taken")
                return

            clients[client_username] = client_socket
            threading.current_thread().name = f"Client-{client_username}Thread"
            print_log(f"{client_username} connected from {addr}")

        if not send_message(client_socket, 
            f"Welcome {client_username}! Type '/list' for users or 'user:message'"):
            return

        with clients_lock:
            notify_clients(f"User {client_username} has entered the chat.", client_username)
            print(clients)

        while server_running:
            data = recv_message(client_socket)
            if not data:
                break

            if data.lower() == "/list":
                user_list = get_clients()
                send_message(client_socket, f"Active users: {user_list}")
                continue

            if ":" in data:
                target_user, _, message = data.partition(":")
                target_user = target_user.strip()
                message = message.strip()

                with clients_lock:
                    target_socket = clients.get(target_user)

                if target_socket:
                    if not send_message(target_socket, f"{client_username}: {message}"):
                        with clients_lock:
                            if target_user in clients:
                                del clients[target_user]
                                print_log(f"Removed disconnected user {target_user}")
                else:
                    send_message(client_socket, f"User {target_user} not found")
            else:
                send_message(client_socket, "Use '/list' or 'user: message'")

    except Exception as e:
        print_log(f"Error with {client_username}: {e}")
    finally:
        if client_username:
            with clients_lock:
                if client_username in clients:
                    del clients[client_username]
                    print_log(f"{client_username} disconnected")
                    notify_clients(f"User {client_username} has left the chat.", client_username)
        try:
            client_socket.close()
        except Exception as e:
            print_log(f"Error closing client socket: {e}")

def start_server():
    global server_running
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        s.bind((HOST, PORT))
        s.listen()
        print_log(f"Listening on {HOST}:{PORT}")
    except Exception as e:
        print_log(f"Failed to start server: {e}")
        return

    try:
        while server_running:
            try:
                client_socket, addr = s.accept()
                print_log(f"New connection from {addr}")
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                if server_running:
                    print_log(f"Error accepting connection: {e}")
    except KeyboardInterrupt:
        print_log("Shutting down server...")
    finally:
        shutdown_server(s)
        server_running = False

if __name__ == "__main__":
    start_server()
