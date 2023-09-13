import logging

import requests
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from classifier import Classifier
from config import Config
from crawler import Crawler, CrawlerUnavailable, InvalidHandle
from fetcher import FetchError, UnsafeImageURL, fetch_image_bytes, media_filename
from imaging import InvalidImage, decode_image

logger = logging.getLogger(__name__)


def create_app(classifier=None, crawler_factory=Crawler, http=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    classifier = classifier or Classifier()
    http = http or requests.Session()

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify(message=error.description), error.code

    @app.errorhandler(InvalidImage)
    def handle_invalid_image(error):
        return jsonify(message=str(error)), error.status_code

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

        try:
            links = crawler_factory().get_image_links(keyword)
        except InvalidHandle as error:
            return {"message": str(error)}, 400
        except CrawlerUnavailable as error:
            return {"message": str(error)}, 503

        predictions, skipped = [], []
        for link in links[: app.config["MAX_IMAGES_PER_KEYWORD"]]:
            try:
                image = decode_image(fetch_image_bytes(http, link))
            except (UnsafeImageURL, FetchError, InvalidImage) as error:
                logger.warning("Skipping %s: %s", link, error)
                skipped.append({"url": link, "reason": str(error)})
                continue
            predictions.append(classifier.predict(image, media_filename(link)))
        return {"predictions": predictions, "skipped": skipped}

    @app.post("/file")
    def classify_file():
        upload = request.files.get("image")
        if not upload:
            return {"message": "Please provide image with 'image' key in request"}, 400

        image = decode_image(upload.read())
        filename = secure_filename(upload.filename or "") or "upload"
        return {"predictions": [classifier.predict(image, filename)]}

    return app


if __name__ == "__main__":
    create_app().run()
