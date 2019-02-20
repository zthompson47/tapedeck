import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import threading

M = 1024
fs = 44100
buff = np.zeros(3 * fs)

def handle_close(event):
    print '------------------------------>>>> close event'

fig = plt.figure(figsize=(7,7))
fig.canvas.mpl_connect('close_event', handle_close)
ax = fig.add_subplot(111)
ax.set_xlim(0, len(buff))
ax.set_ylim(-1, 1)
ax.set_xticks([])
line, = ax.plot(buff)
fig.canvas.draw()

pa = pyaudio.PyAudio()

def stream():
    global buff, mic, pa
    while True:
        raw = mic.read(M)
        x = np.fromstring(raw, dtype=np.int16)
        xn = np.float32(x/32768.0)
        buff = np.append(buff[M:], xn)

def record():
    global mic
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=fs,
                  input=True,
                  frames_per_buffer=M)
    threading.Thread(target=stream).start()

threading.Thread(target=record).start()

def update(frame_number):
    global fig, line, mic, pa
    try:
        line.set_ydata(buff)
        fig.canvas.draw()
    except KeyboardInterrupt:
        print '------------->> keybii'
        #mic.stop_stream()
        #mic.close()
        #pa.terminate()
        #import sys
        #sys.exit()

animation = FuncAnimation(fig, update, interval=20)
plt.show()
