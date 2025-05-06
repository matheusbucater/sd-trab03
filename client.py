import threading
import socket
import sys

HOST = "localhost"
PORT = 8080

def create_client_socket() -> socket.socket:
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def client_connect(client_socket: socket.socket, username: str) -> bool:
    try:
        client_socket.sendall(username.encode())
        data = client_socket.recv(1024).decode()
        print(f"\n{data}")
        return "Welcome" in data
    except ConnectionRefusedError:
        print("Connection refused - server might be down")
        return False
    except (BrokenPipeError, ConnectionResetError):
        print("Connection lost during login")
        return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def client_send_message(client_socket: socket.socket, msg: str) -> bool:
    try:
        if msg.lower() == '/quit':
            client_socket.sendall(msg.encode())
            return False
        client_socket.sendall(msg.encode())
        return True
    except (BrokenPipeError, ConnectionResetError):
        print("\nConnection to server lost")
        return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def client_recv_message(client_socket: socket.socket):
    while True:
        try:
            msg = client_socket.recv(1024).decode()
            if not msg:
                print("\nConnection closed by server")
                break
            print(f"\n{msg}", end="\n> ")
        except (ConnectionResetError, BrokenPipeError):
            print("\nConnection to server lost")
            break
        except UnicodeDecodeError:
            print("\nReceived malformed message")
        except Exception as e:
            print(f"\nError receiving message: {e}")
            break
    client_socket.close()
    sys.exit(0)

if __name__ == "__main__":
    try:
        s = create_client_socket()
        s.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Could not connect to server - make sure it's running")
        sys.exit(1)
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

    while True:
        try:
            username = input("Enter username: ").strip()
            if not username:
                print("Username cannot be empty")
                continue
            if client_connect(s, username):
                break
            else:
                s.close()
                s = create_client_socket()
                s.connect((HOST, PORT))
        except KeyboardInterrupt:
            s.close()
            print("\nCancelled by user")
            sys.exit(0)

    rcv_thread = threading.Thread(target=client_recv_message, args=(s,), daemon=True)
    rcv_thread.start()

    try:
        while True:
            try:
                message = input("> ").strip()
                if not message:
                    continue
                if not client_send_message(s, message):
                    break
                if message.lower() == '/quit':
                    print("Disconnecting...")
                    break
            except KeyboardInterrupt:
                print("\nUse '/quit' to exit properly")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        s.close()
    print("Connection closed")
