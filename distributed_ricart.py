import sys
import socket
import numpy as np
import threading

class RicartAgrawala:
    def __init__(self, process_id, display_ports, nb_process, distributed_ports):
        self.process_id = process_id 
        self.nb_process = nb_process
        self.distributed_ports = distributed_ports
        self.display_ports = display_ports
        self.clock = 0
        self.requesting_critical_section = False
        self.list_approval = []
        self.request_queue = []
        self.others_requests = []
        self.data = []
        self.lock = threading.Lock()
        self.create_distributed()

    # Function create_distributed: Set up the serveur socket
    def create_distributed(self):
        process_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        process_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        process_socket.bind(('localhost', self.distributed_ports[self.process_id]))
        process_socket.listen(5)
        print("Serveur "+str(self.process_id)+ " started")
        self.ricart(process_socket)

    # Function start_jeton: Basic fork accepting all connexion in thread for time improvement
    def ricart(self, process_socket):
        try:
            while True:
                new_socket, address = process_socket.accept()
                threading.Thread(target=self.handle_connection, args=(new_socket,)).start()
        except KeyboardInterrupt:
            print("Server stopped.")
        finally :
            process_socket.close()

    # Function handle_connection: Receive and handle the message,
    # If the message is from a player request critical section, if not update self clock
    # If the message is a reply, update the list of approval and check if you can enter critical section
    # If the message is a request, if the request clock is inferior to self latest request send reply if not stock the request 
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
                if message_type == "REQUEST":
                    if not self.requesting_critical_section:
                        self.send_reply(sender_id)
                    elif (timestamp, sender_id) < self.request_queue[0]:
                        self.send_reply(sender_id)
                    else:
                        self.others_requests.append((timestamp,sender_id))
                elif message_type == "REPLY":
                    for i in range(len(self.list_approval)):
                        if self.list_approval[i][sender_id] != True:
                            self.list_approval[i][sender_id] = True
                            break
                    if all(approval for approval in self.list_approval[0]):
                        self.enter_critical_section()
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
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect(("localhost", port))
                    s.send(self.data[0])
                except ConnectionRefusedError:
                    print("Couldn't transmit message : " + self.data[0].decode())
                finally:
                    s.close()
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
        #print(str(message)) #-- decommente here 
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("localhost", self.distributed_ports[send_id]))
                s.send(message.encode())
            except ConnectionRefusedError:
                print("Couldn't transmit message : "+ message)
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

    RicartAgrawala(num_id, display_ports, nb_player, distributed_ports)

if __name__ == "__main__":
    main()