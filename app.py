import json
import os

import requests
from flask import Flask, request
from flask_api import status

from flask_restful import Api, Resource
from custom_flask_api import CustomFlaskApi
from crawler import Crawler
from classifier import Classifier
import tqdm


flask_app = Flask(__name__)
api = CustomFlaskApi(flask_app)


class StatusAPIView(Resource):
    def get(self):
        message = "API is up and running"
        return {"status": message}, status.HTTP_200_OK


class KeywordAPIView(Resource):
    def get(self):
        keyword = request.args.get("keyword", None)

        if not keyword:
            return {
                "message": "Please provide a keyword argument in query params"
            }, status.HTTP_400_BAD_REQUEST

        crawler = Crawler()
        image_links = crawler.get_image_links(keyword)
        self.download_images(image_links)

        predictions = Classifier.classify_image()
        return {"predictions": predictions}, status.HTTP_200_OK

    def download_images(self, image_links):
        for link in image_links:
            print("Downloading {}".format(link))
            response = requests.get(link, allow_redirects=True)

            if not os.path.exists("images"):
                os.mkdir("images")

            if link.find("/"):
                filename = link.rsplit("/", 1)[1]
            block_size = 1024  # One 1kb
            with open(f"images/{filename}.jpg", "wb") as f:
                for data in response.iter_content(block_size):
                    f.write(data)


class FileAPIView(Resource):
    def post(self):
        request_data = request.files
        image = request_data.get("image", None)

        if not image:
            return {
                "message": "Please provide image with 'image' key in request"
            }, status.HTTP_400_BAD_REQUEST

        Classifier.save_image(image.filename, image)
        predictions = Classifier.classify_image()

        return {"predictions": predictions}, status.HTTP_200_OK


api.add_resource(StatusAPIView, "/status")
api.add_resource(KeywordAPIView, "/keyword")
api.add_resource(FileAPIView, "/file")

if __name__ == "__main__":
    flask_app.run()
