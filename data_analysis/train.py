import os
import json
import numpy as np
import scipy.signal
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from scipy.io import wavfile

# --- Dataset and Model Configuration ---
DATASET_DIR = "dataset"
METADATA_FILE = os.path.join(DATASET_DIR, "metadata.json")
MODEL_FILENAME = "fsk_model.h5"

# --- Parameters for Spectrogram Generation ---
NPERSEG = 128
NOVERLAP = NPERSEG // 2

# --- Function to load and preprocess audio data ---
def load_and_preprocess_data(metadata_file, nperseg, noverlap):
    """
    Loads WAV files and their labels, computes spectrograms, and one-hot encodes labels.
    
    This function has been updated to iterate through subdirectories for class labels
    instead of relying solely on the metadata file.
    """
    print("Loading data from subdirectories...")

    X_data = []
    y_labels = []

    # Get a list of subdirectories to use as class labels
    class_folders = [d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))]
    
    if not class_folders:
        print(f"Error: No class folders found in {DATASET_DIR}")
        return None, None, None

    print(f"Found class folders: {class_folders}")

    # Process files within each class folder
    for folder_name in class_folders:
        label = folder_name.replace("_", " ")  # Convert folder name back to original label
        folder_path = os.path.join(DATASET_DIR, folder_name)
        
        for filename in os.listdir(folder_path):
            if filename.endswith('.wav'):
                file_path = os.path.join(folder_path, filename)
                
                try:
                    sample_rate, data = wavfile.read(file_path)
                    i_component = data[:, 0]
                    q_component = data[:, 1]
                    complex_data = i_component + 1j * q_component
                    
                    _, _, Zxx = scipy.signal.stft(
                        complex_data, 
                        fs=sample_rate, 
                        nperseg=nperseg, 
                        noverlap=noverlap
                    )
                    
                    spectrogram = np.abs(Zxx)
                    spectrogram_normalized = (spectrogram - spectrogram.min()) / (spectrogram.max() - spectrogram.min() + 1e-9)

                    X_data.append(spectrogram_normalized)
                    y_labels.append(label)

                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    continue
    
    if not X_data:
        print("No valid data found to process.")
        return None, None, None

    max_shape = max(s.shape for s in X_data)
    print(f"Padding spectrograms to a uniform shape: {max_shape}")
    X_data_padded = []
    for spec in X_data:
        padded_spec = np.zeros(max_shape)
        padded_spec[:spec.shape[0], :spec.shape[1]] = spec
        X_data_padded.append(padded_spec)

    X_data_array = np.array(X_data_padded)
    
    label_encoder = LabelEncoder()
    integer_encoded = label_encoder.fit_transform(y_labels)
    y_data = to_categorical(integer_encoded)

    # --- NEW: Print unique labels found in the dataset for debugging ---
    print(f"\nUnique labels found in dataset: {label_encoder.classes_}")

    return X_data_array, y_data, label_encoder

# --- Function to build the neural network model ---
def build_model(input_shape, num_classes):
    model = Sequential([
        Flatten(input_shape=input_shape),
        Dense(128, activation='relu'),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

# --- Main execution block ---
if __name__ == '__main__':
    print("--- Step 1: Loading and preprocessing the dataset for training ---")
    X, y, label_encoder = load_and_preprocess_data(METADATA_FILE, NPERSEG, NOVERLAP)

    if X is None or y is None:
        print("Exiting due to data loading error.")
        exit()

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    num_classes = y_train.shape[1]
    input_shape = X_train.shape[1:]

    print("\nBuilding model...")
    model = build_model(input_shape, num_classes)
    model.summary()

    print("\nStarting model training...")
    history = model.fit(
        X_train, y_train,
        epochs=25,
        batch_size=4,
        validation_data=(X_val, y_val),
        verbose=1
    )

    print(f"\nTraining complete. Saving model to {MODEL_FILENAME}")
    model.save(MODEL_FILENAME)

    print("\nModel training script finished.")
