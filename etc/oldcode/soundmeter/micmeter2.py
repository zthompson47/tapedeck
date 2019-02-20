import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import threading
import time

class MicMeter:
    def __init__(self):
        self.alive = True
        self.buff = np.zeros(3 * 44100)
        threading.Thread(target=self.connect).start()

    def connect(self):
        pa = pyaudio.PyAudio()
        mic = pa.open(format=pyaudio.paInt16,
                      channels=1,
                      rate=44100,
                      input=True,
                      stream_callback=self.update_stream,
                      frames_per_buffer=1024)
        while mic.is_active() and self.alive:
            time.sleep(0.1)
        mic.stop_stream()
        mic.close()
        pa.terminate()

    def update_stream(self, in_data, frame_count, time_info, status):
        x = np.fromstring(in_data, dtype=np.int16)
        n = np.float32(x/32768.0)
        self.buff = np.append(self.buff[1024:], n)

    def update_plot(self, frame_number):
        try:
            line.set_ydata(self.buff)
            fig.canvas.draw()
        except KeyboardInterrupt:
            print '------------->> KeyboardInterrupt'
            self.alive = False

def handle_close(event):
    print '------------------------------>>>> close event'

mm = MicMeter()

fig = plt.figure(figsize=(7,7))
fig.canvas.mpl_connect('close_event', handle_close)
ax = fig.add_subplot(111)
ax.set_xlim(0, len(mm.buff))
ax.set_ylim(-1, 1)
ax.set_xticks([])
line, = ax.plot(mm.buff)
fig.canvas.draw()
plt.show()
animation = FuncAnimation(fig, mm.update_plot, interval=20)
