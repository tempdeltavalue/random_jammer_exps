import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import butter, lfilter
from scipy.fft import fft, fftshift
import os

# --- WAV File and SDR Configuration ---
# IMPORTANT: Update this path to your actual WAV file.
WAV_FILE_PATH = 'baseband_433123259Hz_12-22-59_30-07-2025.wav' # Your current WAV file
sdr_sample_rate_ref = 2.4e6 # Reference: SDR sample rate (samples per second).

# --- FSK Parameters (for plotting reference lines) ---
# These values are taken from your Arduino code and are used to draw
# reference lines on the instantaneous frequency plot.
fsk_bit_rate_bps = 9600.0
fsk_freq_dev_hz = 10000.0
f_mark = fsk_freq_dev_hz
f_space = -fsk_freq_dev_hz

# --- Parameters for finding the best signal chunk ---
WAV_CHUNK_SIZE_FOR_ANALYSIS = 2**15 # Size of chunks for initial power analysis
FFT_SIZE_FOR_ANALYSIS = 1024 # FFT size for power spectrum calculation
OVERLAP_PERCENT_FOR_ANALYSIS = 50 # Overlap for FFT windows (e.g., 50% overlap)

# Define a dummy longest expected string length for chunk sizing,
# as the actual string content is not used for decoding here.
# This ensures the extracted chunk is large enough to contain a message.
LONGEST_EXPECTED_STRING_LENGTH = 20 # A reasonable length for a short message

# Calculate samples per bit globally, using the reference sample rate
samples_per_bit_float = sdr_sample_rate_ref / fsk_bit_rate_bps


# --- Function to read WAV file data and extract I/Q ---
def read_iq_wav(file_path):
    """
    Reads an I/Q WAV file recorded by SDR++ (Baseband, Float32)
    and returns complex I/Q data and sample rate.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}. Please ensure the path is correct.")
        return None, None
    try:
        sample_rate, data = wavfile.read(file_path)
        print(f"Loaded WAV file. Sample Rate: {sample_rate} Hz, Shape: {data.shape}, Dtype: {data.dtype}")
        
        # Ensure the sdr_sample_rate_ref matches the actual_wav_sample_rate for consistency
        global sdr_sample_rate_ref # Declare global to modify it
        if sdr_sample_rate_ref != sample_rate:
            print(f"WARNING: sdr_sample_rate_ref ({sdr_sample_rate_ref}) does not match actual WAV sample rate ({sample_rate}). Updating sdr_sample_rate_ref.")
            sdr_sample_rate_ref = sample_rate
            # Recalculate samples_per_bit_float if sdr_sample_rate_ref changes
            global samples_per_bit_float
            samples_per_bit_float = sdr_sample_rate_ref / fsk_bit_rate_bps
            print(f"DEBUG: samples_per_bit_float recalculated to {samples_per_bit_float:.2f}")

        if data.ndim < 2 or data.shape[1] < 2:
            raise ValueError(f"WAV file is not stereo ({data.ndim}D, channels: {data.shape[1] if data.ndim > 0 else 'N/A'}). Cannot extract I/Q.")
        i_component = data[:, 0]
        q_component = data[:, 1]
        
        if data.dtype == np.int16:
            max_int_val = np.iinfo(np.int16).max
            i_component = i_component.astype(np.float32) / max_int_val
            q_component = q_component.astype(np.float32) / max_int_val
            print("Converted Int16 to normalized Float32.")
        elif data.dtype == np.float32:
            i_component = i_component.astype(np.float32)
            q_component = q_component.astype(np.float32)
            print("Data already Float32.")
        else:
            print(f"Warning: Unexpected WAV sample data type: {data.dtype}. Attempting conversion to float32 anyway.")
            i_component = i_component.astype(np.float32)
            q_component = q_component.astype(np.float32)
        
        iq_samples_full = i_component + 1j * q_component
        print(f"Extracted {len(iq_samples_full)} complex samples.")
        return iq_samples_full, sample_rate
    except Exception as e:
        print(f"Error reading WAV file: {e}")
        return None, None

# --- Function to find the chunk with the highest signal power ---
def find_best_signal_chunk(full_iq_samples, sample_rate, chunk_size, fft_size, overlap_percent):
    """
    Analyzes the full IQ samples to find the chunk with the highest peak power in its spectrum.
    This simulates finding the 'brightest line' in a waterfall plot.
    """
    print(f"\nAnalyzing full IQ data to find the chunk with the highest signal power...")
    
    max_peak_power_db = -np.inf
    best_chunk_start_idx = -1
    best_chunk_samples = None

    overlap = int(fft_size * overlap_percent / 100)
    step_size = fft_size - overlap

    # Iterate through the data, calculating spectrum for each window
    for i in range(0, len(full_iq_samples) - fft_size, step_size):
        chunk = full_iq_samples[i : i + fft_size]
        if len(chunk) < fft_size: # Ensure full FFT window
            continue

        # Calculate power spectrum for the current chunk
        yf = fft(chunk * np.hanning(fft_size))
        power_spectrum_db = 20 * np.log10(np.abs(fftshift(yf)) + 1e-10) # Add small epsilon to avoid log(0)
        
        # Find the peak power in this spectrum
        current_peak_power_db = np.max(power_spectrum_db)

        if current_peak_power_db > max_peak_power_db:
            max_peak_power_db = current_peak_power_db
            best_chunk_start_idx = i
            
            # Extract a larger chunk around the peak for plotting
            # Ensure it's at least the size needed for a message (LONGEST_EXPECTED_STRING_LENGTH)
            min_samples_for_string = int(LONGEST_EXPECTED_STRING_LENGTH * 8 * samples_per_bit_float)
            
            # Take a chunk of `chunk_size` around the peak, ensuring it's large enough for a message
            # and doesn't go out of bounds.
            end_idx_for_plot = best_chunk_start_idx + max(chunk_size, min_samples_for_string)
            if end_idx_for_plot > len(full_iq_samples):
                end_idx_for_plot = len(full_iq_samples)
            best_chunk_samples = full_iq_samples[best_chunk_start_idx : end_idx_for_plot]


    if best_chunk_start_idx != -1 and best_chunk_samples is not None:
        print(f"Found best signal chunk starting at sample {best_chunk_start_idx} with peak power {max_peak_power_db:.2f} dB.")
        print(f"This chunk has {len(best_chunk_samples)} samples.")
        return best_chunk_samples, best_chunk_start_idx
    else:
        print("No significant signal chunk found.")
        return None, None

# --- Function to plot the spectrum (FFT) ---
def plot_spectrum(ax, iq_data, sample_rate, title="Spectrum of Best Signal", center_freq_offset_hz=0):
    """
    Generates and displays a spectrum plot (FFT) from IQ data.
    Applies frequency offset correction before FFT.
    """
    ax.clear()
    N = len(iq_data)
    if N == 0: return

    # Apply frequency offset correction to the IQ data before FFT
    if center_freq_offset_hz != 0:
        t = np.arange(N) / sample_rate
        complex_exp = np.exp(1j * 2 * np.pi * center_freq_offset_hz * t)
        iq_data = iq_data * complex_exp

    yf = fft(iq_data * np.hanning(N))
    xf = fftshift(np.fft.fftfreq(N, 1 / sample_rate))
    power_spectrum = np.abs(fftshift(yf))
    power_spectrum = power_spectrum / np.max(power_spectrum) if np.max(power_spectrum) > 0 else power_spectrum
    power_spectrum_db = 20 * np.log10(power_spectrum + 1e-10)

    ax.plot(xf / 1e3, power_spectrum_db)
    ax.set_xlabel("Frequency Offset (kHz)")
    ax.set_ylabel("Power (dB)")
    ax.set_title(title)
    ax.grid(True)
    ax.set_ylim(-100, 0) # Typical range for normalized power spectrum
    # --- UPDATED: Narrow the X-axis range as requested ---
    ax.set_xlim(-200, -140) # Focus on -100 kHz to 0 kHz
    # ---------------------------------------------------------------------

# --- Function to plot instantaneous frequency ---
def plot_instantaneous_frequency(ax, iq_data, sample_rate, bit_rate, freq_dev, mark_freq, space_freq, title="Instantaneous Frequency of Best Signal", center_freq_offset_hz=0):
    """
    Generates and displays a plot of instantaneous frequency from IQ data.
    Applies frequency offset correction before frequency discrimination.
    """
    if iq_data is None or sample_rate is None:
        print("Invalid I/Q data or sample rate provided for frequency plot.")
        return

    print(f"Plotting instantaneous frequency for {len(iq_data)} samples...")

    # Apply frequency offset correction to the IQ data
    if center_freq_offset_hz != 0:
        t = np.arange(len(iq_data)) / sample_rate
        complex_exp = np.exp(1j * 2 * np.pi * center_freq_offset_hz * t)
        iq_data = iq_data * complex_exp

    # Instantaneous Frequency Discrimination
    phase = np.unwrap(np.angle(iq_data))
    instantaneous_frequency = np.diff(phase) * (sample_rate / (2 * np.pi))

    # Low-pass filter the instantaneous frequency
    nyquist = 0.5 * sample_rate
    cutoff_norm = (bit_rate * 2) / nyquist # Use 2x bit rate as a heuristic for cutoff
    if cutoff_norm >= 1.0:
        filtered_frequency = instantaneous_frequency
    else:
        # Corrected: Use butter and lfilter directly
        b, a = butter(5, cutoff_norm, btype='low')
        filtered_frequency = lfilter(b, a, instantaneous_frequency)
    
    print(f"Filtered Freq. Stats (Min/Max/Mean): {np.min(filtered_frequency):.2f}/{np.max(filtered_frequency):.2f}/{np.mean(filtered_frequency):.2f} Hz. Len: {len(filtered_frequency)}")

    time_axis = np.arange(len(filtered_frequency)) / sample_rate

    ax.plot(time_axis, filtered_frequency)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title)
    # Reference lines for mark and space frequencies (relative to 0 Hz after correction)
    ax.axhline(mark_freq, color='green', linestyle='--', label=f'Mark Freq ({mark_freq} Hz)')
    ax.axhline(space_freq, color='red', linestyle='--', label=f'Space Freq ({space_freq} Hz)')
    ax.legend()
    ax.grid(True)
    
    # Adjust y-axis limits to clearly show mark/space frequencies
    min_ylim = min(f_space, f_mark) - abs(f_space - f_mark) * 0.5
    max_ylim = max(f_space, f_mark) + abs(f_space - f_mark) * 0.5
    ax.set_ylim(min_ylim, max_ylim) # Use ax.set_ylim directly

# --- NEW: Function to plot spectrogram (like a waterfall, but for a single chunk) ---
def plot_spectrogram(ax, iq_data, sample_rate, fft_size=256, overlap_percent=75, dynamic_range_db=80, center_freq_offset_hz=0):
    """
    Generates and displays a spectrogram plot from IQ data for a single chunk.
    Applies frequency offset correction and bandpass filtering.
    """
    ax.clear()
    if len(iq_data) < fft_size:
        print("Not enough data for spectrogram. Increase chunk size or decrease FFT size.")
        return

    # Apply frequency offset correction to the IQ data
    if center_freq_offset_hz != 0:
        t = np.arange(len(iq_data)) / sample_rate
        complex_exp = np.exp(1j * 2 * np.pi * center_freq_offset_hz * t)
        iq_data = iq_data * complex_exp

    # --- NEW: Bandpass filter the IQ data for display ---
    # This acts as a "zoom in" on the FSK signal's bandwidth
    fsk_bandwidth_for_filter_hz = (2 * fsk_freq_dev_hz + fsk_bit_rate_bps) * 1.5 # Slightly wider than signal
    nyquist = 0.5 * sample_rate
    
    # Filter should be centered at 0 Hz after applying center_freq_offset_hz
    lowcut_norm = (-fsk_bandwidth_for_filter_hz / 2) / nyquist
    highcut_norm = (fsk_bandwidth_for_filter_hz / 2) / nyquist

    # Ensure filter cutoffs are valid (0 to 1, where 1 is Nyquist)
    if lowcut_norm < 0: lowcut_norm = 0.01 
    if highcut_norm > 1: highcut_norm = 0.99
    if lowcut_norm >= highcut_norm:
        print("Warning: Spectrogram bandpass filter cutoff frequencies are invalid. Skipping filter.")
        filtered_iq_data = iq_data
    else:
        b_bp, a_bp = butter(4, [lowcut_norm, highcut_norm], btype='band', analog=False)
        filtered_iq_data = lfilter(b_bp, a_bp, iq_data)
    # --- END NEW BANDPASS FILTER ---


    num_samples = len(filtered_iq_data) # Use filtered data for spectrogram
    overlap = int(fft_size * overlap_percent / 100)
    step_size = fft_size - overlap

    num_windows = (num_samples - fft_size) // step_size + 1
    if num_windows <= 0:
        print("Not enough data for at least one FFT window for spectrogram.")
        return

    spectrogram_data = np.zeros((num_windows, fft_size))
    window = np.hanning(fft_size)

    for i in range(num_windows):
        start_idx = i * step_size
        end_idx = start_idx + fft_size
        if end_idx > num_samples:
            break

        chunk = filtered_iq_data[start_idx:end_idx] * window # Use filtered data
        fft_result = np.fft.fftshift(np.fft.fft(chunk))
        power_spectrum = np.abs(fft_result)**2
        power_spectrum_db = 10 * np.log10(power_spectrum + 1e-10)
        spectrogram_data[i, :] = power_spectrum_db

    # Normalize data for better visualization
    min_val = np.max(spectrogram_data) - dynamic_range_db
    spectrogram_data[spectrogram_data < min_val] = min_val
    
    # Calculate frequency axis in kHz (offset from center frequency)
    freq_axis_khz = np.linspace(-sample_rate / 2, sample_rate / 2, fft_size) / 1000.0
    
    # Calculate time axis in seconds
    time_axis_seconds = np.linspace(0, (num_windows * step_size) / sample_rate, num_windows)

    # Use imshow to create the spectrogram plot
    im = ax.imshow(spectrogram_data, aspect='auto', cmap='jet',
               extent=[freq_axis_khz[0], freq_axis_khz[-1], time_axis_seconds[-1], time_axis_seconds[0]])

    ax.set_title('Spectrogram of Best Signal Chunk (After Freq Correction & Bandpass)')
    ax.set_xlabel('Frequency Offset (kHz)')
    ax.set_ylabel('Time (s)')
    ax.grid(True, linestyle='--', alpha=0.6)
    # --- UPDATED: Narrow the X-axis range to match the filtered signal ---
    # The filter already narrows the signal, so set xlim to match the expected FSK range
    ax.set_xlim(- (fsk_freq_dev_hz + fsk_bit_rate_bps/2) / 1000.0 * 1.5, (fsk_freq_dev_hz + fsk_bit_rate_bps/2) / 1000.0 * 1.5)
    # --- UPDATED: Set xlim for spectrogram to -100 to 0 kHz as requested ---
    # ax.set_xlim(-100, 0) # Focus on -100 kHz to 0 kHz
    ax.set_xlim(-200, -140) # Focus on -100 kHz to 0 kHz

    # --------------------------------------------------------------------
    # --- Corrected: Call plt.colorbar with the image object and axes ---
    plt.colorbar(im, ax=ax, label='Power (dB)')


# --- Main part of the script ---
if __name__ == "__main__":
    print(f"Starting SDR signal analysis from WAV file: '{WAV_FILE_PATH}'")

    full_iq_samples, actual_sdr_sample_rate = read_iq_wav(WAV_FILE_PATH)

    if full_iq_samples is None:
        print("\nFailed to load WAV file. Exiting.")
        exit()

    sdr_sample_rate = actual_sdr_sample_rate # Use actual sample rate from WAV

    print(f"\nSearching for the chunk with the highest signal power...")
    best_signal_chunk, best_signal_chunk_start_idx = find_best_signal_chunk(
        full_iq_samples, sdr_sample_rate,
        WAV_CHUNK_SIZE_FOR_ANALYSIS, FFT_SIZE_FOR_ANALYSIS, OVERLAP_PERCENT_FOR_ANALYSIS
    )

    if best_signal_chunk is None:
        print("\nCould not find a significant signal chunk in the WAV file. Exiting.")
        exit()

    # --- IMPORTANT: Determine this offset from the SDR++ waterfall or by inspecting the raw IQ data ---
    # Based on your last screenshot, the peaks are roughly around -70kHz to -40kHz.
    # The center of these peaks is around (-70 + -40) / 2 = -55kHz.
    # To bring this to 0kHz, we need to add 55000Hz.
    # Let's use -60000.0 Hz as a starting point as you previously tried,
    # but be prepared to fine-tune this based on the new plots' 'Mean' value.
    center_freq_offset_hz_for_plotting = -60000.0 # Adjusted based on your last screenshot's peaks
    # -------------------------------------------------------------------------------------------------

    # Create a figure with three subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 15)) # 3 rows, 1 column
    fig.suptitle(f"Analysis of Brightest Signal Line (Start Sample: {best_signal_chunk_start_idx})")

    print(f"\nPlotting the spectrum of the brightest signal line...")
    plot_spectrum(
        ax1, # Pass the first subplot axis
        best_signal_chunk,
        sdr_sample_rate,
        title="Spectrum of Best Signal Chunk (After Freq Correction)",
        center_freq_offset_hz=center_freq_offset_hz_for_plotting # Apply correction for plotting
    )

    print(f"\nPlotting the instantaneous frequency of the brightest signal line...")
    # plot_instantaneous_frequency(
    #     ax2, # Pass the second subplot axis
    #     best_signal_chunk,
    #     sdr_sample_rate,
    #     fsk_bit_rate_bps,
    #     fsk_freq_dev_hz,
    #     f_mark,
    #     f_space,
    #     title="Instantaneous Frequency of Best Signal Chunk (After Freq Correction)",
    #     center_freq_offset_hz=center_freq_offset_hz_for_plotting # Apply correction for plotting
    # )

    print(f"\nPlotting the spectrogram of the brightest signal line...")
    plot_spectrogram(
        ax2 , # Pass the third subplot axis
        best_signal_chunk,
        sdr_sample_rate,
        fft_size=256, # Smaller FFT size for better time resolution in spectrogram
        overlap_percent=75,
        dynamic_range_db=90,
        center_freq_offset_hz=center_freq_offset_hz_for_plotting # Apply correction for plotting
    )


    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout to prevent title overlap
    plt.show()

    print("\nAnalysis complete. Observe the plots to identify signal characteristics.")
