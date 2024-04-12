import sys
import socket
import numpy as np
import time
import threading
import select

class RicartAgrawala:
    def __init__(self, process_id, nb_process, distributed_ports, display_ports):
        self.process_id = process_id # Personnal ID
        self.nb_process = nb_process # Total number of process
        self.distributed_ports = distributed_ports # Array with all process ports
        self.display_ports = display_ports # Array with all display ports

        self.clock = 0 # Clock increasing at every message occuration 
        self.data = [] # Array used to stock temporarly the player message
        self.request_queue = [] # Array used to stock the clock attached to each player message
        self.list_approval = [] # List of a tuple of reply to keep track of who responded to every request
        self.requesting_critical_section = False 
        self.others_requests = [] # List of all request received from other process

        self.nb_moves = 0 # Number of moves received from player
        self.time_start = 0 # Timer that we start once receiving the first move from player
        self.nb_messages = 0 # Number of message sent by this process 
        self.process_ended = [False]*nb_process # Tuple of boolean keeping track of which process ended 
        self.lock = threading.Lock() # Lock used to block access to ressource management 

        self.create_distributed()

    # Function create_distributed: Set up the serveur socket
    def create_distributed(self):
        process_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        process_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) # Force reuse if the port still on 
        process_socket.bind(('localhost', self.distributed_ports[self.process_id]))
        process_socket.listen(5)
        process_socket.setblocking(False) # Avoid thread to block on accept and so sensure terminaison (join didn't work in my case)
        print("Serveur "+str(self.process_id)+ " started")
        self.ricart(process_socket)

    # Function start_jeton: Fork accepting all connexion in thread for time improvement
    # End when all process terminated
    # The ready_to_read is used to avoid thread from blocking on accept and so recheck constantly the leaving condition
    def ricart(self, process_socket):
        try:
            while not all(ended for ended in self.process_ended):
                ready_to_read, _, _ = select.select([process_socket], [], [], 0.00001)
                if ready_to_read:
                    new_socket, address = process_socket.accept()
                    t = threading.Thread(target=self.handle_connection, args=(new_socket,))
                    t.start()
        except KeyboardInterrupt:
            print("Server stopped.")
        finally :
            process_socket.close()
            print("Time between the first message receive from player on this process and last process closure message received : " + str(time.time()- self.time_start))
            print("Number of message sent by this process : " +  str(self.nb_messages)+"\nmoves = 10*nb_display ; requests = 10*(nb_process-1) ; replies = 10*(nb_process-1) ; ending message = nb_process-1")
            print("Total number of messages who circulated during the game " + str((self.nb_process*10)+(self.nb_messages*self.nb_process))+ "(player message = 10*nb_process)")
    
    # Function handle_connection: Receive and handle the message,
    # If the message is from a player, request for critical section
    # If the message is a reply, update the list of approval and check if you can enter critical section
    # If the message is a request, if the request clock is inferior to self latest request send reply if not stock the request 
    # If the message is a ending message change it in list of ended process, if all process ended print nb_messages and closing timer
    def handle_connection(self, new_socket):
        # Locking the section to make sure other thread don't enter 
        with self.lock:
            data = new_socket.recv(1024)
            if not data:
                return
            if data.decode()[0] == "R":
                message_type, timestamp, sender_id = data.decode().split(":")
                timestamp = int(timestamp)
                sender_id = int(sender_id)
                self.clock = max(self.clock, timestamp) + 1 
                # Handling Request
                if message_type == "REQUEST":
                    if not self.requesting_critical_section:
                        self.send_reply(sender_id)
                    elif (timestamp, sender_id) < self.request_queue[0]:
                        self.send_reply(sender_id)
                    else:
                        self.others_requests.append((timestamp,sender_id))
                # Handling Reply
                elif message_type == "REPLY":
                    for i in range(len(self.list_approval)):
                        if self.list_approval[i][sender_id] != True:
                            self.list_approval[i][sender_id] = True
                            break
                    if all(approval for approval in self.list_approval[0]):
                        self.enter_critical_section()
            # Handling ending process
            elif data.decode()[0] == "E":
                message_type,sender_id = data.decode().split(":")
                self.process_ended[int(sender_id)] = True
            # Handling player message
            else:
                self.request_critical_section(data)
            new_socket.close() # close the socket at the end 

    # Function request_critical_section: Increase clock, stock data and his request associated 
    # Then send request message to all process except themself
    def request_critical_section(self, data):
        self.clock += 1
        self.data.append(data)
        self.request_queue.append((self.clock, self.process_id))
        self.requesting_critical_section = True
        reply_approval = [False] * self.nb_process
        reply_approval[self.process_id] = True
        self.list_approval.append(reply_approval)
        print("Requesting critical section for message " + str(data)+ " with timestamp " + str((self.clock, self.process_id)))
        for i in range(self.nb_process):
            if i != self.process_id:
                self.send_request(i)

    # Function enter_critical_section: Send message to all display and close critical section
    def enter_critical_section(self):
        print("Starting critical section for message " + str(self.data[0]) + " timestamp " + str(self.request_queue[0]))
        for port in self.display_ports:
            self.nb_messages += 1
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect(("localhost", port))
                    s.send(self.data[0])
                except ConnectionRefusedError:
                    print("Couldn't transmit message : " + self.data[0].decode())
                finally:
                    s.close()
        self.nb_moves += 1
        self.close_critical()

    # Function close_critical: Remove latest message and his request associated
    # Then send reply to process waiting for response if they have priority
    def close_critical(self):
        self.data.pop(0)
        self.request_queue.pop(0)
        self.list_approval.pop(0)
        z = 0
        if len(self.request_queue)== 0:
            self.requesting_critical_section = False
            while z < len(self.others_requests):
                self.send_reply(int(self.others_requests[z][1]))
                self.others_requests.pop(z)
        else:
            while z < len(self.others_requests):
                if self.others_requests[z] < self.request_queue[0]:
                    self.send_reply(int(self.others_requests[z][1]))
                    self.others_requests.pop(z)
                else:
                    z+=1
        self.closing_server()

    # Function closing_server: Manage start and ending configuration
    # if his player sent the first move he start the timer
    # if his player ended his 10 moves he send a message to other process to signal ending
    def closing_server(self):
        if self.nb_moves == 1:
            self.time_start = time.time()
        elif self.nb_moves == 10:
            self.process_ended[int(self.process_id)] = True
            for i in range(self.nb_process):
                if i != self.process_id:
                    self.send_message(i,"END:"+str(self.process_id))

        
    # Function send_request: Used to send request to others process
    def send_request(self, send_id):
        message = f"REQUEST:{self.clock}:{self.process_id}"
        self.send_message(send_id, message)

    # Function send_reply: Used to send reply to others process
    def send_reply(self, send_id):
        message = f"REPLY:{self.clock}:{self.process_id}"
        self.send_message(send_id, message)

    # Function send_message: Basic function sending message to process send_id
    def send_message(self, send_id, message):
        self.nb_messages += 1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("localhost", self.distributed_ports[send_id]))
                s.send(message.encode())
            except ConnectionRefusedError:
                print("Couldn't transmit message : " + message)
            finally:
                s.close()

def main():
    if len(sys.argv) < 6:
        print("Usage: nb_player num_id display_port1 display_port2.. distributed_port1 distributed_port2..  \nOnly work for 2 or more players")
        return
    
    # Retrieve argument to build Ricart class
    nb_player = int(sys.argv[1])
    num_id = int(sys.argv[2])
    display_ports = []
    distributed_ports = []
    for i in range(nb_player):
        display_ports.append(int(sys.argv[3+i]))
        distributed_ports.append(int(sys.argv[3+nb_player+i]))

    RicartAgrawala(num_id, nb_player, distributed_ports, display_ports)

if __name__ == "__main__":
    main()