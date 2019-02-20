import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import threading
import time
import sys

alive = True
buff = np.zeros(3 * 44100)
pa = pyaudio.PyAudio()
print('--.> created pa')

def update_stream(in_data, frame_count, time_info, status):
    #print '--.> in update_stream'
    global buff
    #print '--.> in update_stream-buff'
    x = np.fromstring(in_data, dtype=np.int16)
    n = np.float32(x/32768.0)
    buff = np.append(buff[1024:], n)
    #print '--.> in update_stream-end'
    return (None, pyaudio.paContinue)

def open_mic():
    print('--.> in open_mic')
    global alive
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=44100,
                  input=True,
                  stream_callback=update_stream,
                  frames_per_buffer=1024)
    print('--.> created mic')
    while mic.is_active() and alive:
        time.sleep(0.3)
    print('--.> after sleep')
    mic.stop_stream()
    mic.close()
    pa.terminate()
    print('--.> after cleanup')

def update_plot(frame_number):
    global buff, alive, fig
    try:
        if alive:
            line.set_ydata(buff)
            fig.canvas.draw()
            return line
        else:
            import sys
            sys.exit()
            print('not alive...........')
    except KeyboardInterrupt:
        print('------------->> KeyboardInterrupt')
        alive = False

def handle_close(event):
    print('------------------------------>>>> close event')

print('--.> before therad')
t = threading.Thread(target=open_mic)
t.daemon = True
t.start()
print('--.> after therad')

print('--.> before fig')
fig = plt.figure()
fig.canvas.mpl_connect('close_event', handle_close)
ax = fig.add_subplot(111)
ax.set_xlim(0, len(buff))
ax.set_ylim(-1, 1)
ax.set_xticks([])
line, = ax.plot(buff)
fig.canvas.draw()

print('--.> after fig')
animation = FuncAnimation(fig, update_plot, interval=20)
print('--.> after animateion')
try:
    plt.show()
    t.join()
except:
    sys.exit()
print('--.> end')
