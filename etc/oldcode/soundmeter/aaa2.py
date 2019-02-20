import numpy as np
import matplotlib.pyplot as plt
import pyaudio
import struct
import audioop

M = 1024
fs = 44100
seconds = 3

pa = pyaudio.PyAudio()
stream = pa.open(format=pyaudio.paInt16,
                 channels=1,
                 rate=fs,
                 input=True,
                 frames_per_buffer=M)
x = stream.read(M)
out = []
for i in range(fs/M*seconds):
    raw = stream.read(M)
    x = np.array(struct.unpack("%dh"%(len(raw)/2), raw))
    n = np.float32(x/32768.0)
    out.append(audioop.rms(n, 1))

fig = plt.figure(figsize=(7,7))
ax = fig.add_subplot(111)
ax.plot(out)
plt.show()

stream.stop_stream()
stream.close()
pa.terminate()
