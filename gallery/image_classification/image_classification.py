"""# Image Classification

This is an image classifier app that enables a user to

- select a **classifier model**,
- upload an image

and get a prediction/ classification in return.

This app is inspired by the [imageNet](https://github.com/iamatulsingh/imageNet-streamlit)
application developed by awesome [Atul Kumar Singh](https://github.com/iamatulsingh)."""
import os
from typing import Callable, List, NamedTuple, Tuple

import altair as alt
import keras.backend.tensorflow_backend as tb
import numpy as np
import pandas as pd
import streamlit as st
from keras.applications import (
    VGG16,
    VGG19,
    InceptionV3,
    MobileNetV2,
    ResNet50,
    Xception,
    imagenet_utils,
    inception_v3,
)
from keras.preprocessing.image import img_to_array, load_img
from PIL import Image

# Hack
# I get a '_thread._local' object has no attribute 'value' error without this
# See https://github.com/keras-team/keras/issues/13353#issuecomment-545459472
tb._SYMBOLIC_SCOPE.value = True  # pylint: disable=protected-access


class KerasApplication(NamedTuple):
    """We wrap a Keras Application into this class for ease of use"""

    name: str
    keras_application: object
    input_shape: Tuple[int, int] = (224, 224)
    preprocess_input_func: Callable = imagenet_utils.preprocess_input
    url: str = "https://keras.io/applications/"

    def load_image(self, image_path: str) -> Image:
        """Loads the image from file

        Arguments:
            image_path {str} -- The absolute path to the image

        Returns:
            Image -- The image loaded
        """
        return load_img(image_path, target_size=self.input_shape)

    def to_input_shape(self, image: Image) -> Image:
        """Resizes the image to the input_shape

        Arguments:
            image {Image} -- The image to reshape

        Returns:
            Image -- The reshaped image
        """
        return image.resize(self.input_shape)

    @st.cache()
    def get_model(self) -> object:
        """The Keras model with weights="imagenet"

        Returns:
            [object] -- An instance of the keras_application with weights="imagenet"
        """
        return self.keras_application(weights="imagenet")

    def preprocess_input(self, image: Image) -> Image:
        """Prepares the image for classification by the classifier

        Arguments:
            image {Image} -- The image to preprocess

        Returns:
            Image -- The preprocessed image
        """
        image = self.to_input_shape(image)
        image = img_to_array(image)
        image = np.expand_dims(image, axis=0)
        image = self.preprocess_input_func(image)
        return image

    def get_top_predictions(
        self, image: Image = None, report_progress_func=print
    ) -> List[Tuple[str, str, float]]:
        """[summary]

        Keyword Arguments:
            image {Image} -- An image (default: {None})
            report_progress_func {Callable} -- A function like 'print', 'st.write' or similar
            (default: {print})

        Returns:
            [type] -- The top predictions as a list of 3-tuples on the form
            (id, prediction, probability)
        """
        report_progress_func(
            f"Loading {self.name} model ... (This might take from seconds to several minutes)", 10
        )
        model = self.get_model()

        report_progress_func(f"Processing image ... ", 67)
        image = self.preprocess_input(image)

        report_progress_func(f"Classifying image with '{self.name}'... ", 85)
        predictions = model.predict(image)
        top_predictions = imagenet_utils.decode_predictions(predictions)

        report_progress_func("", 0)

        return top_predictions[0]

    @staticmethod
    def to_main_prediction_string(predictions) -> str:
        """A pretty string of the main prediction to output to the user"""
        _, prediction, prob = predictions[0]
        return f"It's a **{prediction.capitalize()}** with probability {prob * 100:.0f}%"

    @staticmethod
    def to_predictions_chart(predictions) -> alt.Chart:
        """A pretty chart of the (prediction, probability) to output to the user"""
        dataframe = pd.DataFrame(predictions, columns=["id", "prediction", "probability"])
        dataframe["probability"] = dataframe["probability"].round(2) * 100
        chart = (
            alt.Chart(dataframe)
            .mark_bar()
            .encode(
                x="probability",
                y=alt.Y(
                    "prediction:N",
                    sort=alt.EncodingSortField(field="probability", order="descending"),
                ),
            )
        )
        return chart


def get_resources_markdown(model: KerasApplication) -> str:
    """Some info regarding Resources

    Arguments:
        model {KerasApplication} -- The KerasApplication employed

    Returns:
        str -- A Markdown string with links to relevant resources
    """

    return f"""### Resources

- [Keras](https://keras.io/)
  - [Keras Apps](https://keras.io/applications)
    - [{model.name} Docs]({model.url})
- Images
  - [ImageNet](http://www.image-net.org/)
  - [Awesome Images](https://github.com/heyalexej/awesome-images)
"""


# See https://keras.io/applications/
KERAS_APPLICATIONS: List[KerasApplication] = [
    KerasApplication("ResNet50", ResNet50, url="https://keras.io/applications/#resnet"),
    KerasApplication("VGG16", VGG16, url="https://keras.io/applications/#vgg16"),
    KerasApplication("VGG19", VGG19, url="https://keras.io/applications/#vgg19"),
    KerasApplication(
        "InceptionV3",
        InceptionV3,
        input_shape=(299, 299),
        preprocess_input_func=inception_v3.preprocess_input,
        url="https://keras.io/applications/#inceptionv3",
    ),
    KerasApplication(
        "Xception",
        Xception,
        input_shape=(299, 299),
        preprocess_input_func=inception_v3.preprocess_input,
        url="https://keras.io/applications/#xception",
    ),
    KerasApplication("MobileNetV2", MobileNetV2, url="https://keras.io/applications/#mobilenet"),
]

IMAGE_TYPES = ["png", "jpg"]


def set_environ():
    """Sets environment variables for logging etc."""
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


def main():
    """Run this to run the application"""
    set_environ()

    st.title("Image Classification with Keras and Tensorflow.")
    st.info(__doc__)
    selected_model = st.sidebar.selectbox(
        "Pick an image classifier model", options=KERAS_APPLICATIONS, format_func=lambda x: x.name
    )
    st.sidebar.info(get_resources_markdown(selected_model))
    image = st.file_uploader("Upload a file for classification", IMAGE_TYPES)

    if image:
        st.image(image, use_column_width=True)
        image = Image.open(image)
        progress_bar = st.empty()
        progress = st.empty()

        def report_progress(message, value, progress=progress, progress_bar=progress_bar):
            if value == 0:
                progress_bar.empty()
                progress.empty()
            else:
                progress_bar.progress(value)
                progress.markdown(message)

        predictions = selected_model.get_top_predictions(
            image=image, report_progress_func=report_progress
        )

        st.subheader("Main Prediction")
        main_prediction = selected_model.to_main_prediction_string(predictions)
        st.write(main_prediction)

        st.subheader("Alternative Predictions")
        predictions_chart = selected_model.to_predictions_chart(predictions)
        st.altair_chart(predictions_chart)


main()