import threading

from PIL import Image

from classifier.classify import PREPROCESS, load_labels
from tests.conftest import LABELS


def test_predict_returns_label_and_percentage(classifier):
    result = classifier.predict(Image.new("RGB", (300, 200), "blue"), "car.png")
    assert result["filename"] == "car.png"
    assert result["label"] == LABELS[2]
    assert 0 < result["probability"] <= 100


def test_model_runs_in_eval_mode_without_gradients(classifier, model_factory):
    classifier.predict(Image.new("RGB", (50, 50)), "a.png")
    call = model_factory.model.calls[0]
    assert call["training"] is False
    assert call["grad"] is False
    assert call["shape"] == (1, 3, 224, 224)


def test_model_is_built_once_across_requests(classifier, model_factory):
    for _ in range(3):
        classifier.predict(Image.new("RGB", (32, 32)), "x.png")
    assert model_factory.builds == 1


def test_concurrent_first_requests_build_model_once(classifier, model_factory):
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        classifier.predict(Image.new("RGB", (32, 32)), "x.png")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert model_factory.builds == 1


def test_greyscale_and_alpha_images_are_converted_to_rgb(classifier):
    classifier.predict(Image.new("L", (40, 40)), "grey.png")
    classifier.predict(Image.new("RGBA", (40, 40)), "alpha.png")


def test_preprocess_keeps_aspect_then_crops():
    tensor = PREPROCESS(Image.new("RGB", (640, 360)))
    assert tuple(tensor.shape) == (3, 224, 224)


def test_bundled_labels_cover_imagenet():
    labels = load_labels()
    assert len(labels) == 1000
    assert labels[0].startswith("tench")
