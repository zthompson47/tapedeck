import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import struct
import threading
import time

pa = pyaudio.PyAudio()
M = 4096
fs = 44100
buff = np.zeros(3 * fs)
alive = True

def record():
    print '--..>> in record thread'
    global buff
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=fs,
                  input=True,
                  frames_per_buffer=M)
    while mic.is_active():
        raw = mic.read(M)
        x = np.fromstring(raw, dtype=np.int16)
        n = np.float32(x/32768.0)
        buff = np.append(buff[M:], n)
    #mic.stop_stream()
    mic.close()
    pa.terminate()

def update(frame_number, line):
    try:
        line.set_ydata(buff)
        fig.canvas.draw()
    #except KeyboardInterrupt:
    except:
        e = sys.exc_info()[0]
        print e

print '--..>> starting record thread'
threading.Thread(target=record).start()
print '--..>> started record thread'

fig = plt.figure(figsize=(7,7))
ax = fig.add_subplot(111)
ax.set_xlim(0, len(buff))
ax.set_ylim(-1, 1)
ax.set_xticks([])
line, = ax.plot(buff)
fig.canvas.draw()
animation = FuncAnimation(fig, update, interval=40)
plt.show()
