import numpy as np
import scipy.signal as signal
from scipy.io import wavfile
import string
import os
import time
import heapq
import json
import random

# --- WAV File and SDR Configuration (as recorded) ---
WAV_FILE_PATH = 'NEW_baseband_433102020Hz_12-09-54_02-08-2025.wav'
sdr_sample_rate_ref = 2.048e6

# --- FSK Parameters ---
fsk_bit_rate_bps = 48000.5
fsk_freq_dev_hz = 50000
f_mark = fsk_freq_dev_hz
f_space = -fsk_freq_dev_hz

# --- List of expected strings to find ---
EXPECTED_STRINGS = ["Love is all you need", "Hello humans"]
EXPECTED_STRING_LENGTHS = {s: len(s) for s in EXPECTED_STRINGS} # Map strings to lengths

# --- Parameters for dataset generation ---
DATASET_DIR = "dataset"
NUM_CHUNKS_PER_STRING = 5
SAMPLE_OFFSET_STEPS = [-500, -250, 0, 250, 500] # Offset from the found starting point

# --- TWEAKABLE RANGE FOR AUTOMATIC start_offset_bits SEARCH ---
START_OFFSET_BITS_CANDIDATES = range(10, 500, 1)

# --- HIGHLY OPTIMIZED: Narrowed search based on SDR waterfall plot ---
FREQ_OFFSET_CANDIDATES = [101000]

WAV_CHUNK_SIZE = 2**15

# --- All functions remain unchanged from the previous version ---
def read_wav_data(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist at '{file_path}'. Please check the path.")
        return None, None
    try:
        actual_wav_sample_rate, raw_audio_data = wavfile.read(file_path)
        print(f"DEBUG: Loaded WAV file. Sample Rate: {actual_wav_sample_rate} Hz, Shape: {raw_audio_data.shape}, Dtype: {raw_audio_data.dtype}")
        if raw_audio_data.ndim < 2 or raw_audio_data.shape[1] < 2:
            raise ValueError(f"WAV file is not stereo ({raw_audio_data.ndim}D, channels: {raw_audio_data.shape[1] if raw_audio_data.ndim > 0 else 'N/A'}). Cannot extract I/Q.")
        i_component = raw_audio_data[:, 0]
        q_component = raw_audio_data[:, 1]
        if raw_audio_data.dtype == np.int16:
            max_int_val = np.iinfo(np.int16).max
            i_component = i_component.astype(np.float32) / max_int_val
            q_component = q_component.astype(np.float32) / max_int_val
        elif raw_audio_data.dtype == np.float32:
            i_component = i_component.astype(np.float32)
            q_component = q_component.astype(np.float32)
        else:
            print(f"Warning: Unexpected WAV sample data type: {raw_audio_data.dtype}. Attempting conversion to float32 anyway.")
            i_component = i_component.astype(np.float32)
            q_component = q_component.astype(np.float32)
        iq_samples_full = i_component + 1j * q_component
        print(f"DEBUG: Extracted {len(iq_samples_full)} complex samples.")
        return iq_samples_full, actual_wav_sample_rate
    except Exception as e:
        print(f"ERROR: An error occurred while reading WAV file: {e}")
        return None, None

def calculate_amplitude_entropy(iq_samples, num_bins=100):
    amplitudes = np.abs(iq_samples)
    hist, bin_edges = np.histogram(amplitudes, bins=num_bins, density=True)
    probabilities = hist[hist > 0]
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy

def fsk_demodulate_and_decode(samples, sample_rate, bit_rate, freq_dev, mark_freq, space_freq, start_offset_bits_param, target_string_length, freq_offset_hz=0):
    if len(samples) < 2: return None
    if freq_offset_hz != 0:
        t = np.arange(len(samples)) / sample_rate
        complex_exp = np.exp(1j * 2 * np.pi * freq_offset_hz * t)
        samples = samples * complex_exp
    phase = np.unwrap(np.arctan2(samples.imag, samples.real))
    instantaneous_frequency = np.diff(phase) * (sample_rate / (2 * np.pi))
    nyquist = 0.5 * sample_rate
    cutoff_norm = (bit_rate * 2) / nyquist
    if cutoff_norm >= 1.0: filtered_frequency = instantaneous_frequency
    else: b, a = signal.butter(5, cutoff_norm, btype='low'); filtered_frequency = signal.lfilter(b, a, instantaneous_frequency)
    threshold_freq = (mark_freq + space_freq) / 2
    samples_per_bit_float = sample_rate / bit_rate
    raw_bits = []
    num_bits_to_decode = target_string_length * 8
    current_sample_index_float = float(samples_per_bit_float * start_offset_bits_param)
    for bit_count_in_loop in range(num_bits_to_decode):
        sample_index = int(current_sample_index_float + 0.5) 
        if sample_index < len(filtered_frequency):
            bit = 1 if filtered_frequency[sample_index] > threshold_freq else 0
            raw_bits.append(bit)
        else:
            break 
        current_sample_index_float += samples_per_bit_float
    if len(raw_bits) < num_bits_to_decode: return None
    decoded_bytes = bytearray(); byte_value = 0; bit_count = 0
    for bit in raw_bits[:num_bits_to_decode]:
        byte_value = (byte_value << 1) | bit; bit_count += 1
        if bit_count == 8: decoded_bytes.append(byte_value); byte_value = 0; bit_count = 0
    try:
        decoded_string = decoded_bytes.decode('ascii', errors='replace')
        if len(decoded_string) < target_string_length:
            decoded_string += ' ' * (target_string_length - len(decoded_string))
        elif len(decoded_string) > target_string_length:
            decoded_string = decoded_string[:target_string_length]
        return decoded_string
    except Exception as e: return "[Error during final string assembly]"

# --- NEW FUNCTION: Searches for exact matches for the given strings ---
def find_exact_matches(full_iq_samples, sdr_sample_rate, expected_strings, freq_offset):
    found_matches = {s: None for s in expected_strings}
    sorted_expected_strings = sorted(expected_strings, key=len, reverse=True)
    all_found_flag = False

    t = np.arange(len(full_iq_samples)) / sdr_sample_rate
    samples_with_offset = full_iq_samples * np.exp(1j * 2 * np.pi * freq_offset * t)

    for i in range(0, len(full_iq_samples), WAV_CHUNK_SIZE):
        if all_found_flag:
            break

        chunk_samples = samples_with_offset[i : i + WAV_CHUNK_SIZE]
        if not chunk_samples.any(): continue

        for expected_string in sorted_expected_strings:
            if found_matches[expected_string]:
                continue
            
            length = len(expected_string)
            if len(chunk_samples) < (length * 8 / fsk_bit_rate_bps):
                continue
            
            for offset in range(10, 500, 1):
                decoded_text = fsk_demodulate_and_decode(
                    chunk_samples, sdr_sample_rate, fsk_bit_rate_bps,
                    fsk_freq_dev_hz, f_mark, f_space, offset, length,
                    freq_offset_hz=0
                )
                
                if decoded_text and decoded_text.strip() == expected_string:
                    found_matches[expected_string] = {
                        "Chunk Start": i,
                        "Bit Offset": offset,
                        "Freq Offset": freq_offset,
                        "String": decoded_text.strip()
                    }
                    print(f"  --> FOUND: '{expected_string}' at Chunk Start: {i}, Bit Offset: {offset}, Freq Offset: {freq_offset} Hz")

                    if all(found_matches.values()):
                        all_found_flag = True
                        break
            if all_found_flag:
                break
        if all_found_flag:
            break
            
    return found_matches

# --- NEW FUNCTION: Creates folders, generates WAV files and metadata ---
def create_dataset_from_chunks(full_iq_samples, sdr_sample_rate, found_matches, dataset_dir, expected_strings):
    if os.path.exists(dataset_dir):
        print(f"Folder '{dataset_dir}' already exists. Deleting...")
        import shutil
        shutil.rmtree(dataset_dir)
    os.makedirs(dataset_dir)

    metadata = {}
    print("\n--- Generating dataset ---")

    for expected_string in expected_strings:
        match_info = found_matches.get(expected_string)
        if not match_info:
            print(f"Message '{expected_string}' not found. Skipping.")
            continue
        
        string_dir = os.path.join(dataset_dir, expected_string.replace(" ", "_")) # Create folder name from string
        os.makedirs(string_dir)
        
        start_sample_index = match_info['Chunk Start']
        bit_offset = match_info['Bit Offset']
        length_in_samples = int(len(expected_string) * 8 * (sdr_sample_rate / fsk_bit_rate_bps))
        
        print(f"Creating chunks for '{expected_string}'...")
        for i in range(len(SAMPLE_OFFSET_STEPS)):
            # Using the found bit offset, adding a small sample offset
            offset_from_start = int(bit_offset * (sdr_sample_rate / fsk_bit_rate_bps) + SAMPLE_OFFSET_STEPS[i])
            start_capture_index = start_sample_index + offset_from_start
            end_capture_index = start_capture_index + length_in_samples
            
            # Ensuring that the indexes do not go out of the file bounds
            if start_capture_index < 0: start_capture_index = 0
            if end_capture_index > len(full_iq_samples): end_capture_index = len(full_iq_samples)
            if end_capture_index <= start_capture_index: continue

            # Extracting I/Q data and applying frequency correction
            raw_chunk = full_iq_samples[start_capture_index:end_capture_index]
            t_chunk = np.arange(len(raw_chunk)) / sdr_sample_rate
            freq_offset = match_info['Freq Offset']
            corrected_chunk = raw_chunk * np.exp(1j * 2 * np.pi * freq_offset * t_chunk)
            
            # Converting to 16-bit format for the WAV file
            i_data = (corrected_chunk.real * 32767).astype(np.int16)
            q_data = (corrected_chunk.imag * 32767).astype(np.int16)
            stereo_data = np.stack([i_data, q_data], axis=1)

            # Saving the file
            file_name = f"{i+1}.wav"
            file_path = os.path.join(string_dir, file_name)
            wavfile.write(file_path, int(sdr_sample_rate), stereo_data)
            
            # Adding metadata
            metadata[file_name] = expected_string
            print(f"  - Saved {file_name} for '{expected_string}'")

    # --- Generate noise chunks ---
    print("\n--- Generating dataset: Creating noise chunks ---")
    noise_dir = os.path.join(dataset_dir, "random")
    os.makedirs(noise_dir)
    
    # We will pick 5 random chunks from the entire file, but avoid the signal areas.
    # First, find the locations of the signals to avoid them.
    signal_starts = [match['Chunk Start'] for match in found_matches.values()]
    signal_lengths = [len(s) for s in expected_strings]
    signal_regions = []
    for start, length in zip(signal_starts, signal_lengths):
        length_in_samples = int(length * 8 * (sdr_sample_rate / fsk_bit_rate_bps))
        signal_regions.append((start - 1000, start + length_in_samples + 1000)) # Add a buffer

    total_samples = len(full_iq_samples)
    noise_chunk_length = 32768 # Use a standard chunk size for noise
    num_noise_chunks_to_create = 5
    noise_chunks_created = 0

    while noise_chunks_created < num_noise_chunks_to_create:
        start_index = random.randint(0, total_samples - noise_chunk_length)
        end_index = start_index + noise_chunk_length
        
        # Check if the random chunk overlaps with any signal region
        is_in_signal_region = False
        for signal_start, signal_end in signal_regions:
            if not (end_index < signal_start or start_index > signal_end):
                is_in_signal_region = True
                break
        
        if not is_in_signal_region:
            noise_chunk = full_iq_samples[start_index:end_index]
            
            i_data = (noise_chunk.real * 32767).astype(np.int16)
            q_data = (noise_chunk.imag * 32767).astype(np.int16)
            stereo_data = np.stack([i_data, q_data], axis=1)
            
            file_name = f"random_{noise_chunks_created + 1}.wav"
            file_path = os.path.join(noise_dir, file_name)
            wavfile.write(file_path, int(sdr_sample_rate), stereo_data)
            
            metadata[file_name] = "random"
            print(f"  - Saved {file_name} for 'random'")
            noise_chunks_created += 1

    json_path = os.path.join(dataset_dir, 'metadata.json')
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"\nDataset generation complete. Metadata saved to '{json_path}'.")
    return True

if __name__ == "__main__":
    print(f"--- Script for FSK signal dataset generation ---")
    print(f"Searching for exact strings: {EXPECTED_STRINGS}")
    
    full_iq_samples, actual_sdr_sample_rate = read_wav_data(WAV_FILE_PATH)

    if full_iq_samples is None:
        print("\nFailed to load WAV file. Exiting.")
        exit()

    sdr_sample_rate = actual_sdr_sample_rate
    
    print("\n--- Stage 1: Searching for exact signal coordinates ---")
    found_matches = find_exact_matches(full_iq_samples, sdr_sample_rate, EXPECTED_STRINGS, FREQ_OFFSET_CANDIDATES[0])

    if all(found_matches.values()):
        print("\n--- Stage 2: Generating dataset files ---")
        create_dataset_from_chunks(full_iq_samples, sdr_sample_rate, found_matches, DATASET_DIR, EXPECTED_STRINGS)
    else:
        print("\n--- Search did not complete successfully ---")
        for s, info in found_matches.items():
            if not info:
                print(f"Message '{s}' not found.")
        print("Please make sure that the WAV file contains both messages.")
