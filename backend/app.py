# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from services.chat_service import ChatService
from services.student_service import StudentService

app = Flask(__name__)
CORS(app)

chat_service = ChatService()
student_service = StudentService()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'message' not in data or 'conversation_id' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    response = chat_service.process_user_input(
        data['conversation_id'],
        data['message']
    )
    return jsonify(response)

@app.route('/submit-form', methods=['POST'])
def submit_form():
    data = request.json
    try:
        student = student_service.register_student(data)
        return jsonify(student.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)