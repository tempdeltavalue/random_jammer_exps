from flask import Flask, jsonify, render_template
import subprocess
import os
import time
import threading
import torch
import torch.nn as nn
import numpy as np

app = Flask(__name__)

# --- PyTorch Model Setup ---
# Визначаємо просту модель з двома лінійними шарами
class ComplexModel(nn.Module):
    def __init__(self, input_size=784, hidden_size=128, num_classes=10):
        super(ComplexModel, self).__init__()
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = self.flatten(x)
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.softmax(x)
        return x

# Створення екземпляру моделі
model = ComplexModel()
model.eval() # Переводимо модель у режим оцінки
print("PyTorch model with two layers loaded successfully.")

# Стан моделі та потік для її запуску
model_running = False
model_thread = None
prediction_result = None

# Функція, яка симулює роботу моделі
def run_pytorch_model():
    global model_running
    global prediction_result
    print("Starting PyTorch model prediction...")
    model_running = True
    while model_running:
        try:
            # Генерація випадкових вхідних даних, наприклад, зображення 28x28 (784 пікселі)
            dummy_input = torch.randn(1, 1, 28, 28)
            with torch.no_grad(): # Вимикаємо обчислення градієнтів
                output = model(dummy_input)
            
            # Отримуємо передбачений клас (індекс з найвищою ймовірністю)
            predicted_class = torch.argmax(output, dim=1).item()
            prediction_result = f"Predicted Class: {predicted_class}"

        except Exception as e:
            prediction_result = f"Error: {e}"
        time.sleep(1) # Виконуємо предикт кожну секунду
    print("Stopping PyTorch model...")
    prediction_result = "N/A"


# Функції для отримання даних залишаються без змін
def get_cpu_temperature():
    try:
        temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode('utf-8')
        return temp_output.replace('temp=', '').strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"

def get_cpu_usage():
    try:
        usage = os.popen('top -bn1 | grep "Cpu(s)"').readline().split(':')[1].split()
        return f"{usage[1]}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"

def get_memory_usage():
    try:
        mem_info = os.popen('free -m').readlines()[1].split()
        total_mem = mem_info[1]
        used_mem = mem_info[2]
        return f"Used: {used_mem}MB / Total: {total_mem}MB"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "N/A"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/pi-status')
def pi_status():
    return jsonify({
        "status": "online",
        "device": "Raspberry Pi",
        "hostname": os.uname()[1],
        "system_info": os.uname(),
        "cpu_temperature": get_cpu_temperature(),
        "cpu_usage": get_cpu_usage(),
        "memory_usage": get_memory_usage(),
        "model_status": "Running" if model_running else "Stopped",
        "prediction": prediction_result
    })

@app.route('/run-model')
def run_model():
    global model_running
    global model_thread
    if not model_running:
        model_thread = threading.Thread(target=run_pytorch_model)
        model_thread.daemon = True
        model_thread.start()
        return jsonify({"success": True, "message": "Model started"})
    return jsonify({"success": False, "message": "Model is already running"})

@app.route('/stop-model')
def stop_model():
    global model_running
    global model_thread
    if model_running:
        model_running = False
        if model_thread.is_alive():
            model_thread.join(timeout=2)
        return jsonify({"success": True, "message": "Model stopped"})
    return jsonify({"success": False, "message": "Model is not running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)