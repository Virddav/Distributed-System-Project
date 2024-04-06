import sys
import socket
import numpy as np

def handle_player_connection(player_socket,ports,player_move):
    data = player_socket.recv(1024)
    if not data:
        return
    print("Received:", data.decode())
    if(player_move[int(data.decode()[0])] < 10):
        player_move[int(data.decode()[0])] += 1
        for port in ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect(("localhost", port))
                    s.send(data)
                except ConnectionRefusedError:
                    print("Couldn't transmit message : "+ data.decode())
                finally:
                    player_socket.close()


def main():
    if len(sys.argv) < 4:
        print("Usage: server.py local_port port1 port2")
        return

    # Where to receive message
    local_port = int(sys.argv[1])
    # Where to send message
    display_ports = [int(port) for port in sys.argv[2:]]

    # Set up socket for receiving player messages
    player_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    player_server_socket.bind(('localhost', local_port))
    player_server_socket.settimeout(80)
    player_server_socket.listen(5)

    print("Server started. Waiting for players moves...")

    # To make sure players don't move more than 10 times
    player_move = np.zeros(len(display_ports))
    try:
        while True:
            player_socket, address = player_server_socket.accept()
            handle_player_connection(player_socket,display_ports,player_move)
    except KeyboardInterrupt:
        print("Server stopped.")
    except socket.timeout:
        print("Serveur TimeOut")
    finally :
        player_socket.close()
        print(player_move)
    player_server_socket.close()

if __name__ == "__main__":
    main()