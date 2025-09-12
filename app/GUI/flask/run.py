from flask import Flask, redirect, url_for
from blueprints.acquisition import bp as acquisition_bp

def create_app():
    app = Flask(__name__)

    # enregistre le blueprint Acquisition
    app.register_blueprint(acquisition_bp)

    # redirige la racine vers /acquisition
    @app.route("/")
    def home():
        return redirect(url_for("acquisition.acquisition_page"))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
