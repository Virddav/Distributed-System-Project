#! /usr/bin/python3

# source ./env/bin/activate

import argparse
import time
import socket
import sys

import curses
from curses import wrapper

import numpy as np
from sprites import chest, vline, hline
from sprites_small import chest_s, vline_s, hline_s

# 0 : chest = 1 point
# 1 : vertical flip
# 2 : horizontal flip
class Board:
    def __init__(self, size=3, nb=2, seed=42, nb_moves=10):
        np.random.seed(seed)
        self.delta = 5
        self.nb_obj = 3
        self.size = size
        self.content = np.random.randint(self.nb_obj, size=(size, size))
        self.timers  = np.random.randint(self.delta, size=(size, size))
        self.nb = nb
        self.players = [(0,0)]*self.nb
        self.scores = [0]*self.nb
        self.logs = []
        self.nb_moves = nb_moves*self.nb

    def move(self, player_id, dx, dy):
        self.logs.append((player_id, dx, dy))
        self.timers = np.maximum(self.timers-1, 0)
        (x,y) = self.players[player_id]
        (x,y) = ((x+dx) % self.size, (y+dy) % self.size)
        self.players[player_id] = (x,y)
        self.scores[player_id] += self.use(x, y)
    
    def use(self, x, y):
        if self.timers[x, y] != 0:
            return 0
        self.timers[x, y] = self.delta
        match self.content[x, y]:
           case 0 :
               return 1
           case 1 :
               self.content = np.flip(self.content, axis=1)
               self.timers = np.flip(self.timers, axis=1)
           case 2 :
               self.content = np.flip(self.content, axis=0)
               self.timers = np.flip(self.timers, axis=0)
        return 0

def put_at(screen, text, x, y):
    for idx, line in enumerate(text.splitlines()):
        screen.addstr(y+idx, x, line)

def display_curses(board, screen):
    dx = dimx + 4
    dy = dimy + 4
    size = board.size
    delta = (dimx - 7) // 2
    for x in range(size):
        for y in range(size):
            sp = sprites[board.content[x,y]]
            put_at(screen, sp, x*dx, y*dy+1)
            put_at(screen, "[%-5s]" % ('='*board.timers[x,y]), x*dx+delta, (y+1)*dy-3)

    for idx, (x, y) in enumerate(board.players):
        put_at(screen, "P%d" % idx, x*dx+idx*3, y*dy)

    put_at(screen, "Scores: "+str(board.scores), 0, size*dy+2)

def tuple_recv(clientsocket):
    data = ''
    while True:
        tmp = clientsocket.recv(1024)
        if tmp == b'':
            break
        data += tmp.decode()
    return [int(str(val)) for val in data.split()]

def main(stdscr):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serversocket:
        serversocket.bind(('', port))
        serversocket.listen(5)
        for _ in range(board.nb_moves):
            stdscr.clear()
            display_curses(board, stdscr)
            stdscr.refresh()

            (clientsocket, address) = serversocket.accept()
            (player_id, x, y) = tuple_recv(clientsocket)
            board.move(player_id, x, y)
        stdscr.clear()
        display_curses(board, stdscr)
        stdscr.refresh()

            
parser = argparse.ArgumentParser(
                    prog='GUI',
                    description='Show one player gameboard',
)

parser.add_argument('-p', '--port', type=int, default=9000)
parser.add_argument('-n', '--nb', type=int, default=1)
parser.add_argument('-m', '--mini', default=False, action='store_true')

args = parser.parse_args()

port=args.port

if args.mini:
    sprites = [chest_s, vline_s, hline_s]
else:
    sprites = [chest, vline, hline]

dimx = sprites[0].index('\n')
dimy = sprites[0].count('\n')+1


board = Board(nb=args.nb)

time_start = time.time()
wrapper(main) # To start main with graphical interface initialization
time_total = time.time() - time_start

print(board.logs)

print(board.scores)

for pos in range(args.nb):
    for (i, _,_) in board.logs:
        if i == pos:
            print("█", end="")
        else:
            print(" ", end="")
    print("")

#print("Temps de jeu : " + str(time_total))
