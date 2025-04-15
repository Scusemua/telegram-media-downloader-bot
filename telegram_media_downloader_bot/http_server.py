from flask import Flask, send_from_directory
import threading
import os

app = Flask(__name__)
VIDEO_FOLDER:str = os.path.join(os.getcwd(), "video")

print(f'VIDEO_FOLDER: "{VIDEO_FOLDER}"')

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route('/video/<filename>')
def serve_video(filename):
    print(f'Returning video "{filename}" from directory "{VIDEO_FOLDER}": "{os.path.join(VIDEO_FOLDER, filename)}"')
    return send_from_directory(VIDEO_FOLDER, filename, mimetype='video/mp4')

app.run(host='0.0.0.0', port=8081)