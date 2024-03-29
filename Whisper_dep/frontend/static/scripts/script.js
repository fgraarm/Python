function setLoading(isLoading) {
    document.getElementById('loading').style.display = isLoading ? 'block' : 'none';
}

function toggleRecordingButtons(isRecording) {
    document.getElementById('record-btn').style.display = isRecording ? 'none' : 'block';
    document.getElementById('stop-btn').style.display = isRecording ? 'block' : 'none';
}

document.getElementById('upload-form').addEventListener('submit', function(e) {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData();
    formData.append('file', document.getElementById('audio-file').files[0]);
    formData.append('model', document.getElementById('model-select').value);
    formData.append('language', document.getElementById('language-input').value);
    const outputOption = document.getElementById('output-option').value;
    formData.append('outputOption', outputOption);

    let endpoint = '/transcribe';
    if (outputOption === 'diarization') {
        endpoint = '/diarize';
    } else if (outputOption === 'translate_to_english') {
        endpoint = '/translate_to_english'; // Nuevo endpoint para traducción directa al inglés
    }

    fetch(endpoint, {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        setLoading(false);
        if (outputOption === 'translate_to_english') {
            // Mostrar el resultado de la traducción directa al inglés
            document.getElementById('translation-result').textContent = data.translation || "No se encontró traducción.";
        } else {
            // Mostrar el resultado de la transcripción o diarización
            displayTranscriptionResult(data, endpoint);
        }
    })
    .catch(error => {
        setLoading(false);
        console.error('Error:', error);
    });
});

let recordingInterval;
document.getElementById('record-btn').addEventListener('click', function() {
    startRecording();
});

document.getElementById('stop-btn').addEventListener('click', function() {
    stopRecording();
});

document.getElementById('translate-btn').addEventListener('click', function() {
    translateTranscription();
});

function fetchTranscription() {
    fetch('/get_transcription')
    .then(response => response.json())
    .then(data => {
        if (data.transcript) {
            let currentText = document.getElementById('transcription-result').textContent;
            document.getElementById('transcription-result').textContent = `${currentText}\n${data.transcript}`;
        }
    })
    .catch(error => console.error('Error:', error));
}

function startRecording() {
    document.getElementById('recording-gif').style.display = 'block';
    toggleRecordingButtons(true);
    const model = document.getElementById('model-select').value;
    const language = document.getElementById('language-input').value;

    const requestBody = { model, language };
    fetch('/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(handleResponse)
    .then(() => {
        recordingInterval = setInterval(fetchTranscription, 5000); // Cada 5 segundos
    })
    .catch(handleError);
}

function stopRecording() {
    document.getElementById('recording-gif').style.display = 'none';
    toggleRecordingButtons(false);
    clearInterval(recordingInterval);
    fetch('/stop_record', { method: 'POST' })
    .then(handleResponse)
    .catch(handleError);
}

function translateTranscription() {
    document.getElementById('translating-gif').style.display = 'block';
    const transcription = document.getElementById('transcription-result').textContent;
    const sourceLang = document.getElementById('source-lang-select').value;
    const targetLang = document.getElementById('target-lang-select').value;

    fetch('/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: transcription, source_lang: sourceLang, target_lang: targetLang }),
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('translating-gif').style.display = 'none';
        document.getElementById('translation-result').textContent = data.translation;
    })
    .catch(error => {
        document.getElementById('translating-gif').style.display = 'none';
        console.error('Error:', error);
    });
}

function handleResponse(response) {
    if (!response.ok) throw new Error('Network response was not ok');
    return response.json();
}

function handleError(error) {
    document.getElementById('recording-gif').style.display = 'none';
    toggleRecordingButtons(false);
    console.error('Error:', error);
}

function displayTranscriptionResult(data, endpoint) {
    if (endpoint === '/diarize' && data.diarization && data.diarization.length > 0) {
        let diarizationResult = data.diarization.map(segment => `<li>${segment.start}-${segment.end} ${segment.speaker}: ${segment.transcript}</li>`).join('');
        document.getElementById('transcription-result').innerHTML = `<ul>${diarizationResult}</ul>`;
    } else {
        document.getElementById('transcription-result').textContent = data.transcript || data.translation || "No se encontraron resultados.";
    }
}
document.getElementById('export-btn').addEventListener('click', function() {
    const includeTranslation = document.getElementById('include-translation').checked;
    const transcriptionText = document.getElementById('transcription-result').textContent;
    const translationText = document.getElementById('translation-result').textContent;
    
    let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // Incluye el BOM UTF-8
    csvContent += "Transcripción,Traducción\n"; // Encabezados del CSV
    
    // Prepara la línea de datos para el CSV
    let dataString = '"' + transcriptionText.replace(/"/g, '""') + '"'; // Escapa comillas dobles en la transcripción
    if (includeTranslation) {
        dataString += ',"' + translationText.replace(/"/g, '""') + '"'; // Escapa comillas dobles en la traducción
    }
    csvContent += dataString + "\n";
    
    // Crea un elemento de enlace para descargar el CSV
    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "transcripcion_y_traduccion.csv");
    document.body.appendChild(link); // Required for FF
    
    link.click(); // Inicia la descarga
    document.body.removeChild(link); // Limpia añadiendo y quitando el enlace
});