import unittest

import numpy as np
from matplotlib.ticker import FuncFormatter
import matplotlib.pyplot as plt
from myhdl import \
        Signal, ResetSignal, intbv, modbv, enum, concat, \
        instance, always, always_comb, always_seq, \
        delay, now, Simulation, StopSimulation, traceSignals

from dsp import *

SYSCLK_DURATION = int(1e9 / 20e6)

def load_quadrature_short_samples(filename, **options):
    import struct
    struct_fmt = 'hh'
    struct_len = struct.calcsize(struct_fmt)
    struct_unpack = struct.Struct(struct_fmt).unpack_from
    si = []
    sq = []
    with open(filename) as fs:
        if 'offset' in options:
            i = 0
            while i < options['offset']:
                data = fs.read(struct_len)
                i = i + 1
        while (len(si) < options['numsamples']) if 'numsamples' in options else True:
            data = fs.read(struct_len)
            if not data: break
            s = struct_unpack(data)
            si.append(s[0])
            sq.append(s[1])
    final_i = np.array(si, dtype=np.int16)
    final_q = np.array(sq, dtype=np.int16)
    return final_i, final_q

def frequency_response_chirp(tstart, tstop, sample_rate):
    t = np.arange(tstart, tstop, 1./sample_rate)
    y = signal.chirp(t)#, f0=0, f1=sample_rate/2., t1=tstop) + 1j * signal.chirp(t, f0=0, f1=sample_rate/2., t1=tstop, phi=-90)
    return t, y

def figure_continuous_complex(title, axes, f_parent, t, c):
    f = f_parent.add_subplot(axes, title=title)
    plt.plot(t, c.real, 'b-', label='real', figure=f)
    plt.plot(t, c.imag, 'r-', label='imag', figure=f)
    plt.axis([t[0], t[-1], -1, 1], figure=f)
    #plt.legend()
    return f

def figure_discrete_quadrature(title, axes, f_parent, signature, n, i, q):
    min_without_nan = lambda x: min([i for i in x if i is not np.nan])
    max_without_nan = lambda x: max([i for i in x if i is not np.nan])
    percent = float(max_without_nan(i) - min_without_nan(i)) / float(signature.max - signature.min) * 100.0
    t = title + ' (%.2f)' % percent

    f = f_parent.add_subplot(*axes, title=t)
    ax1 = plt.gca()
    ax1.set_autoscale_on(False)
    plt.axis([n[0], n[-1], min_without_nan(i), max_without_nan(i)])
    plt.xlabel('Sample')
    plt.ylabel('Magnitude')
    plt.stem(n, i, linefmt='b-', markerfmt='b.', basefmt='b|')
    ax2 = f.axes.twinx()
    plt.stem(n, q, linefmt='r-', markerfmt='r.', basefmt='r|')
    plt.axis([n[0], n[-1], min_without_nan(q), max_without_nan(q)])
    return f

def figure_binary_offset(title, axes, f_parent, signature, n, i):
    f = f_parent.add_subplot(*axes, title=title)
    plt.stem(n, i, linefmt='b-', markerfmt='b.', basefmt='b|')
    plt.axis([n[0], n[-1], signature.min, signature.max],
        figure=f)
    plt.xlabel('Time')
    plt.ylabel('Magnitude')
    return f

def figure_fft_power(title, axes, f_parent, frq, Y):
    f = f_parent.add_subplot(*axes, title=title)
    plt.ticklabel_format(style='sci', axis='x', scilimits=(0,3))
    ax1 = plt.gca()
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: ('%.1f')%(x/1e6)))
    plt.xlabel('Freq (MHz)')
    plt.ylabel('Power (???)')
    #amplitude_Y = 20*np.log10(np.abs(Y))
    power_Y = np.abs(Y)**2
    phase_Y = np.angle(Y)
    plt.plot(frq, power_Y, 'b')
    return f

def figure_fft_phase(title, axes, f_parent, frq, Y):
    f = f_parent.add_subplot(*axes, title=title)
    plt.ticklabel_format(style='sci', axis='x', scilimits=(0,3))
    ax1 = plt.gca()
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: ('%.1f')%(x/1e6)))
    plt.xlabel('Freq (MHz)')
    plt.ylabel('Phase (radians)')
    phase_Y = np.angle(Y)
    plt.plot(frq, phase_Y, 'g')

    y_tick = np.arange(-np.pi, np.pi, np.pi)
    y_label = [r"$-\pi$", r"$0$", r"$+\pi$"]
    ax1.set_yticks(y_tick*np.pi)
    ax1.set_yticklabels(y_label)

    return f

class DSPSim(object):
    def __init__(self, in_sign, out_sign):
        self.clock = Signal(bool(0))
        self.clearn = ResetSignal(1, 0, async=False)
        self.input = in_sign
        self.output = out_sign
        self.recording = []
        self.results_i = []
        self.results_q = []

    def consume(self):
        if self.output.valid:
            self.results_i.append(int(self.output.myhdl(self.output.i)))
            self.results_q.append(int(self.output.myhdl(self.output.q)))

    def produce(self, i_sample, q_sample, interp=1):
        self.input.i.next = i_sample
        self.input.q.next = q_sample
        self.input.valid.next = True

        self.clock.next = 1
        yield delay(SYSCLK_DURATION // 2)
        self.clock.next = 0
        self.consume()
        yield delay(SYSCLK_DURATION // 2)

        self.input.i.next = 0
        self.input.q.next = 0
        self.input.valid.next = False

        for i in range(interp-1):
            self.clock.next = 1
            yield delay(SYSCLK_DURATION // 2)
            self.clock.next = 0
            self.consume()
            yield delay(SYSCLK_DURATION // 2)


    def delay(self, count):
        for i in range(count):
            self.clock.next = 1
            yield delay(SYSCLK_DURATION // 2)
            self.clock.next = 0
            yield delay(SYSCLK_DURATION // 2)

    def simulate_quadrature(self, in_i, in_q, dspflow, **kwargs):
        interp = kwargs.get('interp', 1)
        @instance
        def stimulus():
            self.t = 0

            self.clearn.next = self.clearn.active
            yield self.delay(1)
            self.clearn.next = not self.clearn.active

            while self.t < len(in_i):
                yield self.produce(self.input.myhdl(in_i[self.t]),
                        self.input.myhdl(in_q[self.t]), interp)
                self.t = self.t + 1
            self.input.valid.next = False
            yield self.delay(1)
            while self.output.valid:
                self.consume()
                yield self.delay(1)
            raise StopSimulation

        # Show the input
        #f_chain_in = figure_discrete_quadrature("chain in", 223, f, self.input, in_n, in_i, in_q)

        traced = traceSignals(dspflow)

        recordings = [s.record(self.clearn, self.clock) for s in self.recording]

        s = Simulation(stimulus, recordings, traced)
        s.run()

        final_i, final_q = (np.array(self.results_i, dtype=self.output.numpy_dtype()),
                np.array(self.results_q, dtype=self.output.numpy_dtype()))
        assert len(final_i) == len(final_q)
        final_n = np.arange(final_i.shape[0])

        #f_chain_out = figure_discrete_quadrature("chain out", 224, f, self.output, final_n, final_i, final_q)
        return final_i, final_q

    def simulate(self, in_c, dspflow, **kwargs):
        # n, for the DSP is an a-range over the sample size
        in_n = np.arange(in_c.shape[0])
        # Convert the input to two signed shorts
        in_i = np.array((self.input.max-1) * in_c.real, dtype=self.input.numpy_dtype())
        in_q = np.array((self.input.max-1) * in_c.imag, dtype=self.input.numpy_dtype())

        final_i, final_q = self.simulate_quadrature(in_i, in_q, dspflow, **kwargs)

        out_c = (final_i / (self.output.max-1.0)) + 1.0j * (final_q / (self.output.max-1.0))

        return out_c



    def record(self, sign):
        self.recording.append(sign)

    def plot_chain(self, name):
        f_parent = plt.figure(name)
        plt.title(name)

        n = 1
        while n*n < len(self.recording):
            n = n + 1
        axes = [(n, n, i) for i in range (1, n * n + 1)]
        axes.reverse()

        for r in self.recording:
            n = np.arange(len(r.samples_i))
            f = figure_discrete_quadrature(r.name, axes.pop(), f_parent, r, n, 
                    r.samples_i, r.samples_q)


class TestOffsetCorrector(unittest.TestCase):
    def test_offset_corrector(self):
        correct_i = Signal(intbv(1, min=-2**9, max=2**9))
        correct_q = Signal(intbv(-1, min=-2**9, max=2**9))

        in_sign = Signature("in", True, bits=10)
        out_sign = Signature("out", True, bits=10)

        s = DSPSim(in_sign=in_sign, out_sign=out_sign)
        def test_offset_corrector():
            offset_corrector_0 = offset_corrector(s.clearn, s.clock,
                correct_i, correct_q,
                s.input, s.output)
            return offset_corrector_0

        in_t = np.arange(0, 10)
        in_i = np.zeros((10,))
        in_q = np.zeros((10,))
        
        out_i, out_q = s.simulate_quadrature(in_i, in_q, test_offset_corrector)
        out_t = np.arange(0, out_i.shape[0])
        
        assert in_t.shape == out_t.shape

        for i in range(out_t.shape[0]):
            assert out_i[i] == int(in_i[i]) + correct_i
            assert out_q[i] == int(in_q[i]) + correct_q

        f = plt.figure("test_offset_corrector")
        plt.title("test_offset_corrector")

        f_in = figure_discrete_quadrature("in", (2, 1, 1), f, in_sign, in_t, in_i, in_q)
        f_out = figure_discrete_quadrature("out", (2, 1, 2), f, out_sign, out_t, out_i, out_q)
        plt.savefig("test_offset_corrector.png")

class TestBinaryOffseter(unittest.TestCase):
    def test_binary_offseter(self):
        in_sign = Signature("in", True, bits=4)
        out_sign = Signature("out", False, bits=4)

        s = DSPSim(in_sign=in_sign, out_sign=out_sign)
        def test_binary_offseter():
            binary_offseter_0 = binary_offseter(s.clearn, s.clock,
                s.input, s.output)
            return binary_offseter_0

        in_i = np.arange(-2**3, 2**3 - 1)
        in_q = np.arange(-2**3, 2**3 - 1)
        in_t = np.arange(0, len(in_i))
        
        out_i, out_q = s.simulate_quadrature(in_i, in_q, test_binary_offseter)
        out_t = np.arange(0, out_i.shape[0])
        
        assert in_t.shape == out_t.shape

        for i in range(out_t.shape[0]):
            assert out_i[i] == int(in_i[i]) + 2**3
            assert out_q[i] == int(in_q[i]) + 2**3

        f = plt.figure("test_binary_offseter")
        plt.title("test_binary_offseter")

        f_in = figure_discrete_quadrature("in", (2, 1, 1), f, in_sign, in_t, in_i, in_q)
        f_out = figure_discrete_quadrature("out", (2, 1, 2), f, out_sign, out_t, out_i, out_q)
        plt.savefig("test_binary_offseter.png")

if __name__ == '__main__':
    unittest.main()