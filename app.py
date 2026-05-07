from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, jsonify
from gemini_service import ask_gemini_with_wikipedia


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Missing message"}), 400

    user_message = data["message"].strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    try:
        answer = ask_gemini_with_wikipedia(user_message)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)