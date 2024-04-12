# Distributed-System-Project
Implementation of Ricart and Agrawala mutual exclusion, basic jeton algorithm and Chang and Roberts election algorithm

Riccart and Aggrawala mutual exclusion is basic, sending a request to others process each time they receive a message from player, when they received reply from all process they enter critical section and do deliver one message to display. For priority comparaison I used a sequential clock comparaison with priority depending on the process id in case of same clock. For enclosure I use a new kind of message, ending message who inform other process that he has terminated his task, when all terminated they all closes.

Jeton algorithm is simple, sending the jeton to process + 1 except for the last who send it to process 0, if a process has something to do they do one task and pass the jeton, if they have nothing they just pass the jeton. When all moves are made process send the jeton one last time and closes until the last who just close.

Chang and roberts election algorithm adaptation to our game:
 - Process 0 start election when he receive message from player
 - If a process has nothing to do he doesn't participate in the election
 - The previous leader participate in all election even if he has nothing to do
 - If no one has anything to do the leader keep launching new election and stay in the leader
 - If the number of moves is equal to nb_process * 10 each process terminate