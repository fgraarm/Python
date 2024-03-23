from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from whisper_integration import transcribe_audio
from audio_recording import start_recording, get_next_transcription, stop_recording  # Asegúrate de importar stop_recording
from transformers import pipeline
import os
import logging
import sys


# Inicializa la pipeline de traducción
translators = {
    'en-es': pipeline("translation", model="Helsinki-NLP/opus-mt-en-es"),
    'ru-es': pipeline("translation", model="Helsinki-NLP/opus-mt-ru-es"),
    'fr-es': pipeline("translation", model="Helsinki-NLP/opus-mt-fr-es"),
    'es-en': pipeline("translation", model="Helsinki-NLP/opus-mt-es-en"),
    'es-ru': pipeline("translation", model="Helsinki-NLP/opus-mt-es-ru"),
    'es-fr': pipeline("translation", model="Helsinki-NLP/opus-mt-es-fr"),
    'fr-en': pipeline("translation", model="Helsinki-NLP/opus-mt-fr-en"),
    'en-ru': pipeline("translation", model="Helsinki-NLP/opus-mt-en-ru"),
    'ru-en': pipeline("translation", model="Helsinki-NLP/opus-mt-ru-en"),
    'fr-ru': pipeline("translation", model="Helsinki-NLP/opus-mt-fr-ru")
}

# Definir la ruta al directorio frontend
frontend_dir = os.path.abspath("../frontend")
basedir = os.path.abspath(os.path.dirname(__file__))

# Verifica si la aplicación se está ejecutando como un ejecutable de PyInstaller
if getattr(sys, 'frozen', False):
    # Si es así, utiliza la carpeta temporal establecida por PyInstaller
    template_folder = os.path.join(sys._MEIPASS, 'frontend/templates')
    static_folder = os.path.join(sys._MEIPASS, 'frontend/static')
else:
    # De lo contrario, utiliza las rutas normales
    frontend_dir = os.path.abspath("../frontend")
    template_folder = os.path.join(frontend_dir, 'templates')
    static_folder = os.path.join(frontend_dir, 'static')
app = Flask(__name__, static_folder=static_folder, template_folder=template_folder)
app_logs = []  # Esta lista almacenará los logs

class MemoryHandler(logging.Handler):
    def emit(self, record):
        # Aquí es donde añadimos el mensaje de log a la lista app_logs
        app_logs.append(self.format(record))

# Configuramos el nivel de log a DEBUG para capturar todos los mensajes
app.logger.setLevel(logging.DEBUG)

# Creamos un manejador que usa nuestra clase MemoryHandler
memory_handler = MemoryHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
memory_handler.setFormatter(formatter)

# Añadimos nuestro manejador de memoria al logger de la aplicación y al logger de werkzeug
app.logger.addHandler(memory_handler)
logging.getLogger('werkzeug').addHandler(memory_handler)

@app.route('/logs')
def logs():
    """Ruta para servir la página de logs."""
    return render_template('logs.html')

@app.route('/get_logs', methods=['GET'])
def get_logs():
    """Endpoint para obtener los logs acumulados."""
    return jsonify({"logs": app_logs})

@app.route('/translate', methods=['POST'])

def translate_text():
    data = request.json
    source_text = data['text']
    source_lang = data.get('source_lang', 'en')  # Idioma de origen, por defecto 'en'
    target_lang = data.get('target_lang', 'es')  # Idioma de destino, por defecto 'es'
    translator_key = f'{source_lang}-{target_lang}'
    translator = translators.get(translator_key, None)
    if not translator:
        return jsonify({"error": "No se encontró un modelo de traducción para el par de idiomas especificado."}), 400
    # Divide el texto en segmentos más pequeños
    segment_size = 400  # Ajusta este valor según sea necesario
    segments = [source_text[i:i+segment_size] for i in range(0, len(source_text), segment_size)]
    
    translated_segments = []
    for segment in segments:
        try:
            # Traduce cada segmento
            translation = translator(segment, src_lang=source_lang, tgt_lang=target_lang, truncation=True)[0]['translation_text']
            translated_segments.append(translation)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # Combina todas las traducciones de segmentos en una respuesta
    full_translation = " ".join(translated_segments)
    return jsonify({"translation": full_translation})

@app.route('/')
def index():
    """Ruta para servir la página de inicio."""
    return render_template('index.html')

@app.route('/acerca-de')
def acerca_de():
    return render_template('acercade.html')

@app.route('/uso-herramienta')
def uso_herramienta():
    return render_template('usoherramienta.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Endpoint para transcribir archivos de audio."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    model = request.form.get('model', 'tiny')
    language = request.form.get('language', None)
    includeTimestamps = 'includeTimestamps' in request.form and request.form['includeTimestamps'] == 'true'
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        filename = os.path.join(uploads_dir, secure_filename(file.filename))
        file.save(filename)
        
        # Llamada a la función de transcripción
        transcript = transcribe_audio(filename, model, language, includeTimestamps)
        # Eliminar el archivo de audio importado una vez transcribido
        os.remove(filename)  # Añadido para eliminar el archivo después de la transcripción
        
        return jsonify({"transcript": transcript})
 

@app.route('/record', methods=['POST'])
def record():
    """Endpoint para grabar y transcribir audio en tiempo real."""
    data = request.get_json()  # Obtiene los datos enviados como JSON
    model = data.get('model', 'tiny')
    language = data.get('language', None)
    
    start_recording(model, language)
    return jsonify({"message": "Recording started"}), 200


def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
@app.route('/get_transcription', methods=['GET'])
def get_transcription():
    """Endpoint para obtener la transcripción acumulada."""
    transcript = get_next_transcription()
    if transcript:
       return jsonify({"transcript": transcript})
    else:
       return jsonify({"message": "No new transcription available"}), 204

@app.route('/stop_record', methods=['POST'])
def stop_record():
    stop_recording()
    return jsonify({"message": "Recording stopped"}), 200

# Servir archivos estáticos para cualquier ruta no capturada por las rutas anteriores
@app.route('/<path:path>')
def static_proxy(path):
    """Servir archivos estáticos."""
    return send_from_directory(frontend_dir, path)

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1' , port=5000)

