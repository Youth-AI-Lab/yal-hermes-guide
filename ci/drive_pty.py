"""Runs a command in a pseudo-terminal, answers prompts in order, prints the screen.

Usage: python3 -I drive_pty.py '<command>' '<expected prompt 1>' '<answer 1>' ...
"""
import os
import pty
import select
import sys
import time

cmd, pairs = sys.argv[1], sys.argv[2:]
pid, fd = pty.fork()
if pid == 0:
    os.execvp("bash", ["bash", "-lc", cmd])
out = b""
deadline = time.time() + 90


def read_some(t=0.5):
    global out
    r, _, _ = select.select([fd], [], [], t)
    if r:
        try:
            out += os.read(fd, 65536)
        except OSError:
            return False
    return True


for i in range(0, len(pairs), 2):
    want, answer = pairs[i].encode(), pairs[i + 1]
    while want not in out and time.time() < deadline:
        if not read_some():
            break
    time.sleep(1.5); read_some(0.2)
    os.write(fd, answer.encode() + b"\r")
while time.time() < deadline:
    if not read_some(1.0):
        break
    if os.waitpid(pid, os.WNOHANG)[0]:
        read_some(0.2)
        break
print(out.decode(errors="replace"))
