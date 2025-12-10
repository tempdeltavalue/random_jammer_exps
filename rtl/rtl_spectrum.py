import numpy as np
import matplotlib.pyplot as plt
from rtlsdr import RtlSdr
import scipy.signal as signal
from scipy.fft import fft, fftshift
import time
import string 

# --- SDR Configuration ---
sdr_center_freq = 433e6       # Frequency (Hz) where the LoRa module transmits
sdr_sample_rate = 2.048e6     # SDR sample rate (samples per second)
sdr_gain = 40                 # SDR Gain (dB) - adjust for best reception
PACKET_CHUNK_SIZE = 2**15      # ЗБІЛЬШЕНО: Розмір блоку вибірок для постійного прослуховування (32768 вибірок)

# --- FSK Parameters (MUST EXACTLY MATCH ARDUINO TRANSMITTER) ---
fsk_bit_rate_bps = 48000.5      # Bit rate (in bits/s) from Arduino sketch
fsk_freq_dev_hz = 50000       # Frequency deviation (in Hz) from Arduino sketch

# Calculate "mark" and "space" frequencies for FSK demodulation
f_mark = fsk_freq_dev_hz      # Frequency for '1'
f_space = -fsk_freq_dev_hz    # Frequency for '0'

# Expected string (for verification)
EXPECTED_STRING = "Hello humans from InQuatro! " 

# --- Packet Detection Thresholds ---
SIGNAL_ENERGY_THRESHOLD = 0.6 # Minimum average power to consider a packet detected

# --- TWEAKABLE RANGE FOR AUTOMATIC start_offset_bits SEARCH ---
START_OFFSET_BITS_CANDIDATES = range(150, 250, 1) # Test from 150 to 249, step 1 bit.
# --- END TWEAK ---

# --- Function to capture samples from RTL-SDR ---
def capture_chunk(sdr_obj, chunk_size):
    try:
        samples = sdr_obj.read_samples(chunk_size)
        return samples
    except Exception as e:
        return None

# --- Function to update the Spectrum plot dynamically ---
def update_spectrum_plot(ax, samples, sample_rate, title="Packet Spectrum"):
    ax.clear() 
    N = len(samples)
    yf = fft(samples * np.hanning(N))
    xf = fftshift(np.fft.fftfreq(N, 1 / sample_rate))
    
    ax.plot(xf / 1e3, 20 * np.log10(np.abs(fftshift(yf))))
    ax.set_xlabel("Frequency relative to carrier (kHz)")
    ax.set_ylabel("Amplitude (dB)")
    ax.set_title(title)
    ax.grid(True)
    ax.set_ylim(-100, 0) 
    ax.set_xlim(-sample_rate/2e3, sample_rate/2e3)

# --- Function to update the Instantaneous Frequency plot dynamically ---
def update_instantaneous_frequency_plot(ax, samples, sample_rate, bit_rate, freq_dev, mark_freq, space_freq, title="Instantaneous Frequency after FSK Demodulation"):
    ax.clear()
    phase = np.unwrap(np.arctan2(samples.imag, samples.real))
    instantaneous_frequency = np.diff(phase) * (sample_rate / (2 * np.pi))
    
    nyquist = 0.5 * sample_rate
    cutoff_norm = (bit_rate * 2) / nyquist 
    b, a = signal.butter(5, cutoff_norm, btype='low')
    filtered_frequency = signal.lfilter(b, a, instantaneous_frequency)
    
    time_axis = np.arange(len(filtered_frequency)) / sample_rate
    ax.plot(time_axis, filtered_frequency)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Instantaneous Frequency (Hz)")
    ax.set_title(title)
    ax.axhline(mark_freq, color='green', linestyle='--', label=f'Mark Freq ({mark_freq} Hz)')
    ax.axhline(space_freq, color='red', linestyle='--', label=f'Space Freq ({space_freq} Hz)')
    ax.legend()
    ax.grid(True)
    ax.set_ylim(space_freq * 1.5, mark_freq * 1.5)


# --- Function for FSK Demodulation and Decoding ---
def fsk_demodulate_and_decode(samples, sample_rate, bit_rate, freq_dev, mark_freq, space_freq, start_offset_bits_param, target_string_length):
    if len(samples) < 2:
        return None
        
    phase = np.unwrap(np.arctan2(samples.imag, samples.real))
    instantaneous_frequency = np.diff(phase) * (sample_rate / (2 * np.pi))
    
    nyquist = 0.5 * sample_rate
    cutoff_norm = (bit_rate * 2) / nyquist 
    b, a = signal.butter(5, cutoff_norm, btype='low')
    filtered_frequency = signal.lfilter(b, a, instantaneous_frequency)
    
    threshold_freq = (mark_freq + space_freq) / 2
    
    samples_per_bit = sample_rate / bit_rate
    
    start_offset_samples = int(samples_per_bit * start_offset_bits_param)

    if start_offset_samples >= len(filtered_frequency):
        return None

    raw_bits = []
    num_bits_to_decode = target_string_length * 8
    
    for i in range(start_offset_samples, len(filtered_frequency), int(samples_per_bit)):
        if i < len(filtered_frequency) and len(raw_bits) < num_bits_to_decode:
            bit = 1 if filtered_frequency[i] > threshold_freq else 0
            raw_bits.append(bit)
        elif len(raw_bits) >= num_bits_to_decode:
            break 
    
    if len(raw_bits) < num_bits_to_decode: 
        return None 

    decoded_bytes = bytearray()
    byte_value = 0
    bit_count = 0

    for bit in raw_bits[:num_bits_to_decode]:
        byte_value = (byte_value << 1) | bit
        bit_count += 1
        if bit_count == 8:
            decoded_bytes.append(byte_value)
            byte_value = 0
            bit_count = 0
    
    try:
        decoded_string = decoded_bytes.decode('ascii', errors='replace')
        
        if len(decoded_string) < target_string_length:
            decoded_string += ' ' * (target_string_length - len(decoded_string))
        elif len(decoded_string) > target_string_length:
            decoded_string = decoded_string[:target_string_length]

        return decoded_string
            
    except Exception as e:
        return "[Error during final string assembly]"


# --- Function to score decoded string quality (used internally for best guess) ---
def score_decoded_string(decoded_string):
    if decoded_string is None:
        return -1 
    
    score = 0
    for i in range(min(len(decoded_string), len(EXPECTED_STRING))):
        if decoded_string[i] == EXPECTED_STRING[i]:
            score += 2 
    
    score += sum(c in string.printable for c in decoded_string) * 0.5 

    return score


# --- Main part of the script ---
if __name__ == "__main__":
    sdr = RtlSdr()

    # SDR Configuration
    sdr.sample_rate = sdr_sample_rate
    sdr.center_freq = sdr_center_freq
    sdr.gain = sdr_gain

    print(f"SDR configured: Center Freq={sdr.center_freq/1e6} MHz, Sample Rate={sdr.sample_rate/1e6} MS/s, Gain={sdr.gain} dB")
    print(f"Expected string from transmitter: '{EXPECTED_STRING}' (Length: {len(EXPECTED_STRING)})")
    print("\nPlease run your ESP8266 with FSK LoRa module set to CONTINUOUS transmission.")
    print("Starting continuous FSK reception and decoding...")
    print(f"Listening for packets in chunks of {PACKET_CHUNK_SIZE} samples.")
    print(f"Automatically searching for best start_offset_bits in range {START_OFFSET_BITS_CANDIDATES.start}-{START_OFFSET_BITS_CANDIDATES.stop} (step {START_OFFSET_BITS_CANDIDATES.step}).")
    print("Press Ctrl+C to stop.")

    # --- Setup for dynamic plotting ---
    plt.ion() # Turn on interactive plotting mode
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8)) # Create one figure with two subplots
    fig.suptitle("FSK Signal Live Demodulation") # Main title for the figure
    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout to make space for suptitle

    try:
        while True:
            chunk_samples = capture_chunk(sdr, PACKET_CHUNK_SIZE)
            
            if chunk_samples is None:
                print("Problem capturing samples. Check SDR connection.")
                time.sleep(0.1) 
                continue
            
            signal_power_chunk = np.mean(np.abs(chunk_samples)**2)
            
            if signal_power_chunk > SIGNAL_ENERGY_THRESHOLD:
                best_decoded_string = None
                best_score = -2 

                # Iterate through candidate offsets
                for offset in START_OFFSET_BITS_CANDIDATES:
                    decoded_text_candidate = fsk_demodulate_and_decode(
                        chunk_samples, sdr_sample_rate, fsk_bit_rate_bps, 
                        fsk_freq_dev_hz, f_mark, f_space, offset, len(EXPECTED_STRING) # Pass target length
                    )
                    
                    current_score = score_decoded_string(decoded_text_candidate)
                    
                    if current_score > best_score:
                        best_score = current_score
                        best_decoded_string = decoded_text_candidate
                        
                        if EXPECTED_STRING == str(best_decoded_string): # Check for perfect match
                            break 
                
                # --- Update and redraw plots for the best-found decoding ---
                update_spectrum_plot(ax1, chunk_samples, sdr_sample_rate, title=f"Packet Spectrum (Energy: {signal_power_chunk:.2e})")
                update_instantaneous_frequency_plot(ax2, chunk_samples, sdr_sample_rate, fsk_bit_rate_bps, fsk_freq_dev_hz, f_mark, f_space, title="Packet Instantaneous Frequency")
                
                fig.canvas.draw()
                fig.canvas.flush_events()
                
                # --- STREAM DECODED CHARACTERS IN FIXED LENGTH ---
                if best_decoded_string:
                    print(f"Decoded: '{best_decoded_string}'", end='')
                    if EXPECTED_STRING == best_decoded_string:
                        print(" -> SUCCESS!")
                    else:
                        print(" -> MISMATCH.")
                else:
                    print("Decoded: [No readable text after trying all offsets]")
                
                time.sleep(0.5) 
            
            time.sleep(0.01) 

    except KeyboardInterrupt:
        print("\nStopping reception.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        plt.ioff() 
        plt.show(block=True) 
        sdr.close()
        print("SDR closed.")