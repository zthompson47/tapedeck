import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
from scipy.fftpack import rfft
import pyaudio
import essentia.standard as ess

N = 2048 # adjust to vary time resolution, but too low will crash
fs = 44100
eps = np.finfo(float).eps

pa = pyaudio.PyAudio()

fig = plt.figure(figsize=(11,7))

# time domain
buff = np.zeros(3*fs)
ax1 = fig.add_subplot(511)
ax1.set_ylim(-0.2, 0.2)
ax1.set_xticks([]) # no ticks seems to run faster
(line_buff,) = ax1.plot(buff)

# frequency domain, magnitude & log(magnitude)
bfft = np.zeros(N)
mag = np.zeros(N)
ax2 = fig.add_subplot(512)
ax2.set_xlim(0, len(bfft)/4)
ax2.set_ylim(-100, 100)
ax2.set_xticks([])
(line_bfft,) = ax2.plot(bfft)
ax22 = ax2.twinx()
ax22.set_xlim(0, len(mag)/4)
ax22.set_ylim(0, 40)
ax22.set_xticks([])
(line_mag,) = ax22.plot(mag, 'g')

# energy, rms, loudness from lecture 9T1
# I did log scale to make the plots more visible.
energy = np.zeros(N)
rms = np.zeros(N)
spl = np.zeros(N)
ax3 = fig.add_subplot(513)
ax3.set_xlim(0, len(rms))
ax3.set_ylim(-20, 0)
ax3.set_xticks([])
(line_rms,) = ax3.plot(np.log(rms+eps), 'r')
(line_energy,) = ax3.plot(np.log(energy+eps), 'b')
(line_spl,) = ax3.plot(np.log(spl+eps), 'c')

# spectral centroid from lecture 9T1
centroid = np.zeros(N)
ax4 = fig.add_subplot(514)
ax4.set_xlim(0, len(centroid))
ax4.set_ylim(0, 14000)
ax4.set_xticks([])
(line_centroid,) = ax4.plot(centroid)

# mfcc
_mfcc = ess.MFCC(numberCoefficients=12, inputSize=N)
mfcc = np.zeros((N, 12))+eps
ax5 = fig.add_subplot(515)
ax5.set_xlim(-N, N)
ax5.set_ylim(0, 11)
ax5.set_xticks([])
#print (np.arange(N)/fs).shape, np.arange(12).shape, mfcc.shape
line_mfcc = ax5.contour(np.arange(N)/fs, np.arange(12), np.transpose(mfcc))

fig.canvas.draw()

# record microphone in a thread and use global variables to set shared plot data
def record():
    global mic, buff, bfft, centroid, energy, rms, spl, mfcc, mag

    # open microphone as input stream with pyaudio
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=fs,
                  input=True,
                  frames_per_buffer=N)

    # read input stream
    while mic.is_active():
        raw = mic.read(N)

        # unpack audio data from string format and normalize
        x = np.fromstring(raw, dtype=np.int16)
        n = np.float32(x/32768.0)
        buff = np.append(buff[N:], n)

        # fft
        mag = np.abs(rfft(n))
        bfft = 20*np.log10(mag + eps)

        # centroid
        y_val = np.arange(N)*(float(fs)/2)/float(N)
        _centroid = np.sum(y_val*mag)/np.sum(mag)
        centroid = np.append(centroid[1:], _centroid)

        # energy
        _e = np.sum(mag**2)
        _r = (_e/(N**2))**0.5
        _s = _e**0.666

        # scale to approximately normal (estimated from test runs)
        _e /= 40000
        _r /= 0.4
        _s /= 6000
        energy = np.append(energy[1:], _e)
        rms = np.append(rms[1:], _r)
        spl = np.append(spl[1:], _s)

        _mfcc_bands, _mfcc_coefficients = _mfcc(mag.tolist())
        #print mfcc[1:].shape, _mfcc_coefficients.shape
        mfcc = np.append(mfcc[1:], (_mfcc_coefficients,), axis=0)
        #print '=====.>>>', mfcc.shape

# callback function for FuncAnimation, update plots and redraw
def update_plot(frame_number):
    global line_mfcc
    line_buff.set_ydata(buff)
    line_mag.set_ydata(mag)
    line_bfft.set_ydata(bfft)
    line_rms.set_ydata(np.log(rms+eps))
    line_energy.set_ydata(np.log(energy+eps))
    line_spl.set_ydata(np.log(spl+eps))
    line_centroid.set_ydata(centroid)

    line_mfcc = ax5.contour(np.arange(N)/fs, np.arange(12), np.transpose(mfcc))

    fig.canvas.draw()

def freq_to_mel(freq):
    return 2595.0 * np.log10(1.0 + freq/700.0)

# open microphone input thread
t = threading.Thread(target=record)
t.daemon = True
t.start()

# start main animation loop
# interval in milliseconds affects performance - too low will crash
animation = FuncAnimation(fig, update_plot, interval=100)
plt.show()
