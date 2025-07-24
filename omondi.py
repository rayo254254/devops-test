from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello from Omondi's Cloud Run app!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
    print("This is the main module of ryan.py")
else:
    print("This is not the main module of ryan.py")