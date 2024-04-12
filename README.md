# Distributed-System-Project
Implementation of Ricart and Agrawala mutual exclusion, basic jeton algorithm and Chang and Roberts election algorithm

Riccart and Aggrawala mutual exclusion is basic, sending a request to others process each time they receive a message from player, when they received reply from all process they enter critical section and do deliver one message to display. For priority comparaison I used a sequential clock comparaison with priority depending on the process id in case of same clock. For enclosure I use a new kind of message, ending message who inform other process that he has terminated his task, when all terminated they all closes.

Jeton algorithm is simple, sending the jeton to process + 1 except for the last who send it to process 0, if a process has something to do they do one task and pass the jeton, if they have nothing they just pass the jeton. When all moves are made process send the jeton one last time and closes until the last who just close.


