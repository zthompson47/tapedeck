import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import pyaudio
#from multiprocessing import Process, Pipe

M = 4096*2

def run_mic(input_pipe):
    print '------..>> in run_mic'
    pa = pyaudio.PyAudio()
    print '------..>> created pa'
    mic = pa.open(format=pyaudio.paInt16,
                  channels=1,
                  rate=44100,
                  input=True,
                  frames_per_buffer=M)
    print '------..>> created mic'
    while True:
        raw = mic.read(M)
        print '-....sending/.........%d....' % len(raw)
        input_pipe.send(raw)
    mic.stop_stream()
    mic.close()
    pa.terminate()

if __name__ == '__main__':
    import billiard
    from billiard import Process, Pipe
    billiard.forking_enable(False)

    output_pipe, input_pipe = Pipe()
    mic = Process(target=run_mic, args=(input_pipe,))
    mic.start()

    buff = np.zeros(3 * 44100)
    fig = plt.figure(figsize=(7,7))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, len(buff))
    ax.set_ylim(-1, 1)
    ax.set_xticks([])
    line, = ax.plot(buff)
    fig.canvas.draw()

    def update(frame_number, output_pipe):
        global buff
        print 'update.............'
        #try:
        raw = output_pipe.recv()
        print 'received update~~~~.............'
        if raw != '':
            x = np.fromstring(raw, dtype=np.int16)
            n = np.float32(x/32768.0)
            buff = np.append(buff[M:], n)
            line.set_ydata(buff)
            fig.canvas.draw()
        else:
            import sys
            sys.exit()
        #except: #KeyboardInterrupt
        #    import sys
        #    e = sys.exc_info()[0]
        #    print e
    print '------.> Here'
    animation = FuncAnimation(fig, update, fargs=(output_pipe,), interval=20)
    plt.show()
    print '------.> Her after animee'
    print '------.> tHere after shoe'
