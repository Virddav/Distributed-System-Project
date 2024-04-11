import sys
import socket
import threading
import time
import hashlib
import random
import select

class Jeton:
    def __init__(self, process_id, nb_process, distributed_ports, display_ports, host, UID):
        self.process_id = process_id # Personnal ID 
        self.nb_process = nb_process # Total number of process
        self.distributed_ports = distributed_ports # Array with all process ports
        self.display_ports = display_ports # Array with all display ports
        self.host = host
        self.UID = UID # Unique Identification of the process
        self.data = [] # Array used to stock temporarly the player message
        self.quit = False # Condition to stop the process

        # Last process will have the first jeton and have of neighbor the first process
        self.participant = False 
        self.join_election = False
        if process_id == nb_process-1:
            self.next_process_id = 0
        else:
            self.next_process_id = process_id + 1 
        if process_id == 0:
            self.start_time = 0 
            self.starting_election = True

        self.nb_moves = 0
        self.nb_messages = 0

        self.lock = threading.Lock()
        self.create_distributed()

    # Function create_distributed: Set up the serveur socket
    def create_distributed(self):
        self.process_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.process_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.process_socket.bind((self.host, self.distributed_ports[self.process_id]))
        self.process_socket.listen(10)
        self.process_socket.setblocking(False)
        print("Serveur "+str(self.process_id)+ " started")
        self.start_election()

    # Function start_jeton: Basic fork accepting all connexion in thread for time improvement
    def start_election(self):
        try:
            while int(self.nb_moves) < int(self.nb_process*10):
                ready_to_read, _, _ = select.select([self.process_socket], [], [], 0.00001)
                if ready_to_read:
                    new_socket, address = self.process_socket.accept()
                    t = threading.Thread(target=self.handle_connection, args=(new_socket,))
                    t.start()
        except KeyboardInterrupt:
            print("Server stopped.")
        finally :
            self.process_socket.close()
            if self.process_id == 0:
                print("serveur closed with " + str(self.nb_messages)+" messages")
                print("serveur closed in " + str(time.time()-self.start_time)+"seconds")
            else:
                print("check process 0 for stats")

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
            if data.decode()[0] == "E":
                election, UID, nb_moves, nb_message = data.decode().split(":")
                if UID == self.UID:
                    if self.join_election:
                        self.enter_critical_section(nb_moves, nb_message)
                    else:
                        self.send_leadership_message(self.UID,nb_moves,nb_message)
                elif not self.join_election or UID > self.UID:
                    self.send_election_message(UID, nb_moves, nb_message)
                elif UID < self.UID:
                    self.send_election_message(self.UID, nb_moves, nb_message)

            elif data.decode()[0] == "L":
                election, UID, nb_moves, nb_message = data.decode().split(":")
                hash_object = hashlib.sha256()
                random_number = random.randint(0, 1000)
                hash_object.update((str(self.process_id)+str(random_number)).encode('utf-8'))
                new_UID = hash_object.hexdigest()

                if self.UID != UID:
                    self.UID = new_UID
                    self.send_leadership_message(UID, nb_moves, nb_message)
                else:
                    self.UID = new_UID
                    self.send_election_message(self.UID, nb_moves, nb_message)   
                    self.participant = True     
            else:
                self.prepare_critical_section(data)
            new_socket.close() # close the socket at the end
    
    # Function prepare_critical_section: Stock the data and wait for the jeton
    #  If it's first received message of the last process send the jeton 
    def prepare_critical_section(self, data):
        if self.process_id == 0 and self.starting_election:
            self.send_election_message(self.UID, 0,0)
            self.starting_election = False
            self.start_time = time.time()
            self.participant = True
        self.data.append(data)
        self.join_election = True
        print("Waiting for election " + str(data))

    # Function enter_critical_section: Send latest received message to all display and close critical section
    def enter_critical_section(self, nb_moves, nb_message):
        print("I am the leader, sending message " + str(self.data[0]))
        for port in self.display_ports:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((self.host, port))
                    s.send(self.data[0])
                except ConnectionRefusedError:
                    print("Couldn't transmit message : " + self.data[0].decode())
                finally:
                    s.close()
        self.close_critical(nb_moves, nb_message)

    # Function close_critical: Remove latest message, send jeton and increase number of move made
    def close_critical(self, nb_moves, nb_message):
        self.data.pop(0)
        self.send_leadership_message(self.UID, int(nb_moves)+1, nb_message) 
        if self.data == []:
            self.join_election = False
        self.participant = False

    # Function send_jeton: Send the jeton to neighbor and check multiple ending condition 
    # nb_message is the number total of jeton transmited, increased by 1 every time 
    # nb_moves is the number total of message sent to display
    def send_election_message(self, UID, nb_moves, nb_message):
        nb_message = int(nb_message)+1 
        self.nb_messages = nb_message
        self.nb_moves = nb_moves
        message = "ELECTION:" + str(UID) + ":" + str(nb_moves) +":"+ str(nb_message)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.host, self.distributed_ports[self.next_process_id]))
                s.send(message.encode())
            except ConnectionRefusedError:
                print("Couldn't transmit message : "+ message)
            finally:
                s.close()
    
    def send_leadership_message(self, UID, nb_moves, nb_message):
        nb_message = int(nb_message)+1 
        self.nb_messages = nb_message
        self.nb_moves = nb_moves
        message = "LEADER:" + str(UID) + ":" + str(nb_moves) +":"+ str(nb_message)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.host, self.distributed_ports[self.next_process_id]))
                s.send(message.encode())
            except ConnectionRefusedError:
                print("Couldn't transmit message : "+ message)
            finally:
                s.close()

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
    host = "localhost"
    hash_object = hashlib.sha256()
    random_number = random.randint(0, 1000)
    hash_object.update((str(num_id)+str(random_number)).encode('utf-8'))
    UID = hash_object.hexdigest()

    print(UID)
    Jeton(num_id, nb_player, distributed_ports, display_ports, host, UID)

if __name__ == "__main__":
    main()
