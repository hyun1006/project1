from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# 설정값 저장용 (임시 메모리, 또는 JSON 파일로 확장 가능)
config_data = {}

# UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
UPLOAD_FOLDER = os.path.abspath("uploads")

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('project.html')


@app.route('/save_settings', methods=['POST'])
def save_settings():
    global config_data
    config_data = request.json  # JSON 형태로 받음
    return jsonify({"message": "설정 저장 완료!"}), 200


@app.route('/upload', methods=['POST'])
def upload():
    global config_data
    file = request.files.get('file')

    if not file:
        return '파일이 선택되지 않았습니다.', 400

    filename = secure_filename(file.filename)
    upload_path = config_data.get("upload_path", UPLOAD_FOLDER)  # 설정된 경로 or 기본

    if not os.path.exists(upload_path):
        os.makedirs(upload_path)

    file.save(os.path.join(upload_path, filename))
    return f"파일 업로드 완료! 저장 위치: {os.path.join(upload_path, filename)}"

if __name__ == '__main__':
    app.run(host="0.0.0.0")
