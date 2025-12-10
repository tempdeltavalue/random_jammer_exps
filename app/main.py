from flask import Flask, request, jsonify, render_template
import json
import threading
import time
from collections import deque

app = Flask(__name__)

# Dictionary to store a history of FFT data for each channel
# Key: channel number (e.g., 76, 77)
# Value: deque (double-ended queue) of dictionaries, each containing
#        {"magnitudes": [...], "peak_frequency": float, "sampling_freq": float, "timestamp": float}
fft_history_per_channel = {}

# Max number of FFT samples to keep in history for each channel
MAX_HISTORY_SIZE = 100 # Adjust this based on how long you want the spectrogram to show

# Lock for thread-safe access to fft_history_per_channel
data_lock = threading.Lock()

@app.route('/')
def index():
    """
    Serves the main HTML page for spectrogram visualization.
    """
    return render_template('index.html')

@app.route('/receive_fft', methods=['POST'])
def receive_fft_data():
    """
    Receives FFT data from the ESP8266 via POST request.
    Expects a JSON payload with 'channel', 'sampling_freq', 'peak_frequency', and 'magnitudes'.
    Adds the latest data to the history for the specific channel.
    """
    if request.is_json:
        data = request.get_json()
        channel = data.get('channel')
        sampling_freq = data.get('sampling_freq')
        peak_frequency = data.get('peak_frequency')
        magnitudes = data.get('magnitudes')

        if (channel is not None and sampling_freq is not None and
            peak_frequency is not None and magnitudes is not None):
            with data_lock:
                if channel not in fft_history_per_channel:
                    fft_history_per_channel[channel] = deque(maxlen=MAX_HISTORY_SIZE)

                # Add new data point to the history
                fft_history_per_channel[channel].append({
                    "magnitudes": magnitudes,
                    "peak_frequency": peak_frequency,
                    "sampling_freq": sampling_freq,
                    "timestamp": time.time() # Use server time for consistency
                })

            print(f"Received FFT Data for Channel {channel}:")
            print(f"  Magnitudes (first 5): {magnitudes[:5]}...")
            print(f"  Peak Frequency: {peak_frequency} Hz")
            print(f"  Sampling Frequency: {sampling_freq} Hz")
            return jsonify({"status": "success", "message": f"FFT data received for Channel {channel}"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid data format. Missing 'channel', 'sampling_freq', 'peak_frequency', or 'magnitudes'."}), 400
    else:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

@app.route('/get_fft_history', methods=['GET'])
def get_fft_history():
    """
    Provides the historical FFT data for all channels to the frontend via GET request.
    """
    with data_lock:
        # Convert deques to lists for JSON serialization
        serializable_history = {
            channel: list(history) for channel, history in fft_history_per_channel.items()
        }
        return jsonify(serializable_history), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)