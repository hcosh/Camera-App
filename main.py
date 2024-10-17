from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import threading

app = FastAPI()

recording = False
out = None
lock = threading.Lock()

def gen_frames():
    camera = cv2.VideoCapture(1)
    global out, recording, lock
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            with lock:
                if recording and out is not None:
                    out.write(frame)

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Camera Feed</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                margin-top: 50px;
            }
            h1 {
                color: #333;
            }
            img {
                border: 2px solid #333;
                border-radius: 10px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <h1>Live Camera Feed</h1>
        <img src="/video_feed" width="640" height="480" class="img-fluid"/>
        <button class="btn btn-success btn-lg m-2" onclick="startRecording()">Start Recording</button>
        <button class="btn btn-danger btn-lg m-2" onclick="stopRecording()">Stop Recording</button>
        <script>
            function startRecording() {
                fetch('/start_recording', {method: 'POST'});
            }
            function stopRecording() {
                fetch('/stop_recording', {method: 'POST'});
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/start_recording")
def start_recording():
    global recording, out, lock
    with lock:
        if not recording:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))
            recording = True
    return {"message": "Recording started"}

@app.post("/stop_recording")
def stop_recording():
    global recording, out, lock
    with lock:
        if recording:
            recording = False
            if out is not None:
                out.release()
                out = None
    return {"message": "Recording stopped"}