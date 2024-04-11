import sys
import socket
import numpy as np
import threading
import time

class Jeton:
    def __init__(self, process_id, nb_process, distributed_ports, display_ports):
        self.process_id = process_id # Personnal ID 
        self.nb_process = nb_process # Total number of process
        self.distributed_ports = distributed_ports # Array with all process ports
        self.display_ports = display_ports # Array with all display ports

        self.data = [] # Array used to stock temporarly the player message
        self.waiting_jeton = False 
        self.quit = False # Condition to stop the process

        # Last process will have the first jeton and have of neighbor the first process
        self.starting_jeton = False 
        if process_id == nb_process-1:
            self.next_process_id = 0
        else:
            self.next_process_id = process_id + 1 
        if process_id == 0:
            self.starting_jeton = True
            self.start_time = 0 

        self.lock = threading.Lock()
        self.create_distributed()

    # Function create_distributed: Set up the serveur socket
    def create_distributed(self):
        self.process_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.process_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.process_socket.bind(('localhost', self.distributed_ports[self.process_id]))
        self.process_socket.listen(10)
        print("Serveur "+str(self.process_id)+ " started")
        self.start_jeton()

    # Function start_jeton: Basic fork accepting all connexion in thread for time improvement
    def start_jeton(self):
        try:
            while not self.quit:
                new_socket, address = self.process_socket.accept()
                t = threading.Thread(target=self.handle_connection, args=(new_socket,))
                t.start()
                t.join()        
        except KeyboardInterrupt:
            print("Server stopped.")
        finally :
            self.process_socket.close()

    # Function handle_connection: Receive message, 
    # if the message is a jeton send it if nothing to do 
    # or send to display your latest message
    # if it's not a jeton prepare critical section
    def handle_connection(self, new_socket):
        # Locking the section to make sure other thread don't enter 
        with self.lock:
            data = new_socket.recv(1024)
            if not data:
                return
            if data.decode()[0] == "J":
                jeton, nb_moves, nb_message = data.decode().split(":")
                if not self.waiting_jeton:
                    self.send_jeton(nb_moves, nb_message)
                else:
                    self.enter_critical_section(nb_moves, nb_message)
            else:
                self.prepare_critical_section(data)
            new_socket.close() # close the socket at the end
    
    # Function prepare_critical_section: Stock the data and wait for the jeton
    # If it's first received message of the last process send the jeton 
    def prepare_critical_section(self, data):
        if self.process_id == 0 and self.starting_jeton:
            self.send_jeton(0,0)
            self.starting_jeton = False
            self.start_time = time.time()
        self.data.append(data)
        self.waiting_jeton = True
        print("Waiting for jeton " + str(data))

    # Function enter_critical_section: Send latest received message to all display and close critical section
    def enter_critical_section(self, nb_moves, nb_message):
        print("Jeton received sending message " + str(self.data[0]))
        for port in self.display_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect(("localhost", port))
                    s.send(self.data[0])
                except ConnectionRefusedError:
                    print("Couldn't transmit message : " + self.data[0].decode())
                finally:
                    s.close()
        self.close_critical(nb_moves, nb_message)

    # Function close_critical: Remove latest message, send jeton and increase number of move made
    def close_critical(self, nb_moves, nb_message):
        self.data.pop(0)
        self.send_jeton(int(nb_moves)+1, nb_message) 
        if self.data == []:
            self.waiting_jeton = False

    # Function send_jeton: Send the jeton to neighbor and check multiple ending condition 
    # nb_message is the number total of jeton transmited, increased by 1 every time 
    # nb_moves is the number total of message sent to display
    def send_jeton(self, nb_moves, nb_message):
        nb_message = int(nb_message)+1 
        message = "JETON:" + str(nb_moves) +":"+ str(nb_message)
        # Checking if the game has ended and we are the last process on 
        if int(nb_moves)  < self.nb_process-1 + (self.nb_process*10):
            # Checking if the game has ended, if yes we send last jeton and end the process using self.quit
            if int(nb_moves) >= self.nb_process * 10:
                print("Serveur ended")
                if self.process_id == 0:
                    print("The game lasted : " + str(time.time()-self.start_time)+ " second")
                    print("Serveur ended with jeton sent equal to " + str(int(nb_message)))
                else:
                    print("See game duration and number of message transmitted in process 0")
                self.quit = True 
                message = "JETON:" + str(int(nb_moves)+1) +":"+ str(nb_message)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.connect(("localhost", self.distributed_ports[self.next_process_id]))
                        s.send(message.encode())
                    except ConnectionRefusedError:
                        print("Couldn't transmit message : "+ message)
                    finally:
                        s.close()
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.connect(("localhost", self.distributed_ports[self.next_process_id]))
                        s.send(message.encode())
                    except ConnectionRefusedError:
                        print("Couldn't transmit message : "+ message)
                    finally:
                        s.close()
        else:
            if self.process_id == 0:
                print("The game lasted : " + str(time.time()-self.start_time) + " second")
                print("Serveur ended with jeton sent equal to " + str(int(nb_message)))
            else:
                print("Server ended")
                print("See game duration and number of messages transmitted in process 0")
            self.quit = True

def main():
    if len(sys.argv) < 6:
        print("Usage: nb_player num_id display_port1 display_port2.. distributed_port1 distributed_port2.. \nOnly work for 2 or more players")
        return

    # Retrieve argument to build Jeton class
    nb_player = int(sys.argv[1])
    num_id = int(sys.argv[2])
    display_ports = []
    distributed_ports = []
    for i in range(nb_player):
        display_ports.append(int(sys.argv[3+i]))
        distributed_ports.append(int(sys.argv[3+nb_player+i]))

    Jeton(num_id, nb_player, distributed_ports, display_ports)

if __name__ == "__main__":
    main()
