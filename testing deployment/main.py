from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, this is the test on local server!"

if __name__ == "__main__":
    app.run(debug=True)

