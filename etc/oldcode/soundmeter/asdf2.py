import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import struct
import audioop
import threading

M = 1024
fs = 44100
buff = np.zeros(3 * fs)

fig = plt.figure(figsize=(7,7))
ax = fig.add_subplot(111)
ax.set_xlim(0, len(buff))
ax.set_ylim(-1, 1)
ax.set_xticks([])
line, = ax.plot(buff)
fig.canvas.draw()

pa = pyaudio.PyAudio()

running = True

def record():
    global mic
    print '---.>> before mic'
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=fs,
                  input=True,
                  frames_per_buffer=M)
    print '---.>> before streaming lop'
    while running and mic.is_active():
        raw = mic.read(M)
        x = np.fromstring(raw, dtype=np.int16)
        n = np.float32(x/32768.0)
        buff = np.append(buff[M:], n)
        #out.append(audioop.rms(n, 1))
    print '---.>> after streaming lop'
    mic.stop_stream()
    print '---.>> after micstop strem'
    mic.close()
    print '---.>> after micstop close'
    pa.terminate()
    print '---.>> after pa term'

t = threading.Thread(target=record)
t.daemon = True
t.start()

def update(frame_number):
    global line, mic, pa, running
    try:
        if running:
            line.set_ydata(buff)
            fig.canvas.draw()
    #except KeyboardInterrupt:
    except:
        import sys
        e = sys.exc_info()[0]
        print e
        running = False

print '---.>> before animation'
animation = FuncAnimation(fig, update, interval=100)
print '---.>> after animation'
plt.show()
#t.join()
print '---.>> END'