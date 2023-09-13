import io
import logging

import requests
from flask import Flask, jsonify, request
from PIL import Image
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from classifier import Classifier
from config import Config
from crawler import Crawler

logger = logging.getLogger(__name__)


def create_app(classifier=None, crawler_factory=Crawler, http=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    classifier = classifier or Classifier()
    http = http or requests.Session()

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(message=error.description), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.exception("Unhandled error while serving %s", request.path)
        return jsonify(message="Something went wrong"), 500

    @app.get("/status")
    def status():
        return {"status": "API is up and running"}

    @app.get("/keyword")
    def classify_keyword():
        keyword = request.args.get("keyword")
        if not keyword:
            return {"message": "Please provide a keyword argument in query params"}, 400

        predictions = []
        for link in crawler_factory().get_image_links(keyword):
            logger.info("Downloading %s", link)
            response = http.get(link)
            image = Image.open(io.BytesIO(response.content))
            predictions.append(classifier.predict(image, link.rsplit("/", 1)[-1]))
        return {"predictions": predictions}

    @app.post("/file")
    def classify_file():
        upload = request.files.get("image")
        if not upload:
            return {"message": "Please provide image with 'image' key in request"}, 400

        image = Image.open(io.BytesIO(upload.read()))
        filename = secure_filename(upload.filename or "") or "upload"
        return {"predictions": [classifier.predict(image, filename)]}

    return app


if __name__ == "__main__":
    create_app().run()
