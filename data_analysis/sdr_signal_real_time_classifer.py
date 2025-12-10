import os
import json
import numpy as np
import scipy.signal
import tensorflow as tf
from tensorflow.keras.models import load_model
from rtlsdr import RtlSdr
from scipy.io import wavfile
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.utils import to_categorical

# --- Model and Configuration ---
MODEL_FILENAME = "fsk_model.h5"

# --- Parameters for Spectrogram Generation (MUST MATCH TRAINING) ---
NPERSEG = 128
NOVERLAP = NPERSEG // 2

# --- SDR Parameters (MUST BE CONFIGURED CORRECTLY) ---
SDR_CENTER_FREQ_HZ = 433_101_000  # Center frequency in Hz (e.g., 433.101 MHz)
SDR_SAMPLE_RATE_HZ = 2_400_000     # Sample rate in Hz (must match the WAV recording)
SDR_GAIN = 40                      # Gain in dB (adjust for your signal)
SDR_CHUNK_SIZE = 32768             # Number of samples to read at a time

# --- Define class labels in the same order as training ---
# This order is crucial for the model's output to be interpreted correctly.
# The order is based on alphabetical sorting of folder names: "Hello_humans", "Love_is_all_you_need", "random"
CLASS_LABELS = ['Hello humans', 'Love is all you need', 'random']

# --- Function to load and preprocess a single audio chunk ---
def preprocess_chunk(data_chunk, sample_rate, nperseg, noverlap, target_shape):
    """
    Preprocesses a single chunk of I/Q data into a normalized spectrogram.
    
    Args:
        data_chunk (np.ndarray): The raw complex I/Q data chunk.
        sample_rate (int): The sample rate of the data.
        nperseg (int): Length of each segment for the STFT.
        noverlap (int): Number of points to overlap.
        target_shape (tuple): The expected shape of the spectrogram from training.

    Returns:
        np.ndarray: The normalized spectrogram, padded to match the training shape.
    """
    try:
        if len(data_chunk) < nperseg:
            # Handle chunks that are too small for STFT
            return None

        # Compute spectrogram using STFT
        _, _, Zxx = scipy.signal.stft(
            data_chunk, 
            fs=sample_rate, 
            nperseg=nperseg, 
            noverlap=noverlap
        )
        
        spectrogram = np.abs(Zxx)
        spectrogram_normalized = (spectrogram - spectrogram.min()) / (spectrogram.max() - spectrogram.min() + 1e-9)

        # Pad or truncate the spectrogram to a uniform shape
        padded_spec = np.zeros(target_shape)
        padded_spec[:spectrogram_normalized.shape[0], :spectrogram_normalized.shape[1]] = spectrogram_normalized
        
        return np.expand_dims(padded_spec, axis=0) # Add batch dimension
    
    except Exception as e:
        print(f"Error processing chunk: {e}")
        return None

# --- Main execution block ---
if __name__ == '__main__':
    print("--- FSK Signal Classifier (Real-Time SDR) ---")
    
    # Load the trained model
    if not os.path.exists(MODEL_FILENAME):
        print(f"Error: Trained model file '{MODEL_FILENAME}' not found.")
        print("Please train the model first by running the `train_model.py` script.")
        exit()
    
    model = load_model(MODEL_FILENAME)
    print(f"\nSuccessfully loaded model '{MODEL_FILENAME}'.")
    
    # The input shape of the model can be used to define the spectrogram shape
    model_input_shape = model.input_shape[1:]
    
    # Initialize the SDR
    try:
        sdr = RtlSdr()
        sdr.sample_rate = SDR_SAMPLE_RATE_HZ
        sdr.center_freq = SDR_CENTER_FREQ_HZ
        sdr.gain = SDR_GAIN
        print("\nSuccessfully initialized SDR with the following parameters:")
        print(f"  - Center Frequency: {sdr.center_freq / 1e6:.3f} MHz")
        print(f"  - Sample Rate: {sdr.sample_rate / 1e6:.3f} MHz")
        print(f"  - Gain: {sdr.gain} dB")
    except Exception as e:
        print(f"Error initializing SDR: {e}")
        print("Please ensure your RTL-SDR dongle is connected and the drivers are installed.")
        exit()
    
    # --- Start the real-time analysis loop ---
    print("\nStarting real-time analysis. Press Ctrl+C to stop.")
    try:
        while True:
            # Read a chunk of complex samples from the SDR
            samples = sdr.read_samples(SDR_CHUNK_SIZE)

            # Preprocess the chunk into a spectrogram
            spectrogram_input = preprocess_chunk(samples, sdr.sample_rate, NPERSEG, NOVERLAP, model_input_shape)
            
            if spectrogram_input is None:
                continue
            
            # Make a prediction
            predictions = model.predict(spectrogram_input, verbose=0)
            
            # Get the predicted class index
            predicted_class_index = np.argmax(predictions, axis=1)[0]
            
            # Get the human-readable label and prediction confidence
            predicted_label = CLASS_LABELS[predicted_class_index]
            confidence = predictions[0][predicted_class_index]
            
            # Print the result
            print(f"Predicted Class -> '{predicted_label}' (Confidence: {confidence:.2f})")
    
    except KeyboardInterrupt:
        print("\nStopping analysis.")
    finally:
        sdr.close()
        print("SDR closed.")
    
    print("\nInference script finished.")
