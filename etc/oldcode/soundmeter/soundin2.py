import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
import struct
import audioop

class AudioMeter:
    def __init__(self, M=1024, fs=44100, buff_length=3):
        self.M = M
        self.fs = fs
        self.buff = np.zeros(buff_length * fs)
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=fs,
                                   input=True,
                                   stream_callback=self.callback,
                                   frames_per_buffer=M)
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlim(0, len(self.buff))
        self.ax.set_ylim(-1, 1)
        self.ax.set_xticks([])
        self.line, = self.ax.plot(self.buff)
        self.fig.canvas.draw()
        plt.show()

    def callback(self, in_data, frame_count, time_info, status):
        x = np.fromstring(in_data, dtype=np.int16)
        n = np.float32(x/32768.0)
        self.buff = np.append(self.buff[self.M:], n)
        #out.append(audioop.rms(n, 1))

    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    def update(self, frame_number):
        try:
            self.line.set_ydata(self.buff)
            self.fig.canvas.draw()
        #except KeyboardInterrupt:
        except:
            import sys
            e = sys.exc_info()[0]
            print e

am = AudioMeter()
animation = FuncAnimation(am.fig, am.update, interval=20)
#plt.show()
