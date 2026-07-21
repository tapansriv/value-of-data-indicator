# How to use TMUX to run experiments on chameleon/remote nodes

On iterm, you can use `CMD + d` to split the window vertically and open a new
terminal in the second window. You can use `CMD + Shift + d` or `CMD + D` to do
the same but split the window horizontally and open a new terminal in the lower
window. 


Now, if you open an iterm window, ssh onto a node, and then use one of those
commands to split the window, the new terminal opened will be on your local
machine, not SSHed. 

However, if you ssh, then run `tmux -CC`, this will create a new TMUX window.
You can then use the two commands above to split windows that will all be on
that remote machine. When you're done, you go back to the iterm window that you
ran `tmux -CC` on, and just hit escape. This will close the tmux window, but
will not exit those sessions!! So any commands you ran on the TMUX windows will
keep running. 

You can then exit the SSH window, pack up your bag, move around, whatever. When
you're ready to check, you open a new iterm window, ssh back in, and run `tmux
-CC a` to attach the window you created earlier. This will open back up , and
you can see progress. 

This means that you can start an experiment and detach from the view but ensure
that the program keeps running. If you ran it on just an ssh'ed terminal window,
when the SSH tunnel broke if you moved or time out, the program would end. 
