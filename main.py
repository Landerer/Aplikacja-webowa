from typing import cast
from dataclasses import asdict
import io
import logging

from flask import Flask, send_file, render_template, request
from flask_restful import Api, Resource
from werkzeug.exceptions import NotFound
import matplotlib.pyplot as plt
import numpy as np

import images as img


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
api = Api(app)
images = img.Images("dane", "opisane")


@app.route("/")
def main_page():
    return render_template("main_page.html")


@app.route("/image")
def get_image():
    id = request.args.get("id")
    try:
        image_data = images.get_image(id).load()
    except img.ImageNotExistsError as e:
        raise NotFound(str(e)) from e

    file_object = io.BytesIO()
    plt.imsave(file_object, image_data, cmap="viridis")
    file_object.seek(0)

    return send_file(file_object, mimetype="image/PNG")


@api.resource("/images")
class Images(Resource):
    def get(self):
        return [asdict(image) for image in images.get_images(False)]


@api.resource("/images/<int:image_id>")
class Image(Resource):
    def get(self, image_id):
        try:
            asdict(images.get_image(image_id))
        except img.ImageNotExistsError as e:
            raise NotFound(str(e)) from e


@api.resource("/images/<int:image_id>/descriptions")
class Descriptions(Resource):
    def get(self, image_id):
        try:
            return [asdict(d) for d in images.get_descriptions(image_id)]
        except img.DescriptionNotExistsError as e:
            raise NotFound(str(e)) from e


@api.resource("/images/<int:image_id>/descriptions/<int:description_id>")
class Description(Resource):
    def get(self, image_id, description_id):
        try:
            return asdict(images.get_description(image_id, description_id))
        except img.DescriptionNotExistsError as e:
            raise NotFound(str(e)) from e

    def post(self, image_id, description_id):
        logging.debug(request.form)
        description = img.Description(
            description_id,
            image_id,
            int(request.form["x"]),
            int(request.form["y"]),
            int(request.form["width"]),
            int(request.form["height"]),
        )
        images.add_description(description)
        return asdict(description)


app.run()