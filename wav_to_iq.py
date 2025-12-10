#!/usr/bin/env python3
# fsk_encoder.py

from gnuradio import gr
from gnuradio import blocks
from gnuradio import digital
from gnuradio import filter
from gnuradio.filter import window
import numpy as np

# --- Flowgraph Parameters ---
sample_rate = 44100
iq_sample_rate = sample_rate * 2
symbol_rate = sample_rate
sensitivity = 1.0
low_pass_freq = 20000
transition_width = 1000

# --- File Paths ---
input_wav_file = "/Users/tempdeltavalue/Desktop/jammer_exp/Bach_C_minor_Passacaglia_Variation_2.wav"
output_iq_file = "/Users/tempdeltavalue/Desktop/jammer_exp/fsk_iq.bin"

class WavToFSKEncoder(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "Wav To FSK Encoder")

        self.wav_source = blocks.wavfile_source(input_wav_file, False)
        self.fsk_mod = digital.gfsk_mod(
            samples_per_symbol=int(iq_sample_rate / symbol_rate),
            sensitivity=sensitivity,
            bt=0.5
        )
        self.lpf = filter.fir_filter_ccf(
            1,
            filter.firdes.low_pass(
                1,
                iq_sample_rate,
                low_pass_freq,
                transition_width,
                window.WIN_HAMMING  # Corrected constant location
            )
        )
        self.file_sink = blocks.file_sink(gr.sizeof_gr_complex, output_iq_file, False)
        self.connect(self.wav_source, self.fsk_mod)
        self.connect(self.fsk_mod, self.lpf)
        self.connect(self.lpf, self.file_sink)

if __name__ == '__main__':
    tb = WavToFSKEncoder()
    print("Running FSK Encoder...")
    tb.run()
    print("FSK Encoding complete. Output file:", output_iq_file)