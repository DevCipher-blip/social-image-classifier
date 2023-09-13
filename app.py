import logging
import os

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from classifier import Classifier
from config import Config
from crawler import Crawler

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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

        image_links = Crawler().get_image_links(keyword)
        download_images(image_links)
        return {"predictions": Classifier.classify_image()}

    @app.post("/file")
    def classify_file():
        image = request.files.get("image")
        if not image:
            return {"message": "Please provide image with 'image' key in request"}, 400

        Classifier.save_image(image.filename, image)
        return {"predictions": Classifier.classify_image()}

    return app


def download_images(image_links):
    os.makedirs("images", exist_ok=True)
    for link in image_links:
        logger.info("Downloading %s", link)
        response = requests.get(link, allow_redirects=True)
        filename = link.rsplit("/", 1)[1]
        with open(f"images/{filename}.jpg", "wb") as f:
            for data in response.iter_content(1024):
                f.write(data)


if __name__ == "__main__":
    create_app().run()
