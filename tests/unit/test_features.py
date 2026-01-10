import numpy as np
from PIL import Image

from app.core.features import compute_image_feature, rgb_to_lab


def test_rgb_to_lab_shape():
    rgb = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
    lab = rgb_to_lab(rgb)
    assert lab.shape == (1, 1, 3)


def test_compute_image_feature_edges():
    image = Image.new("RGBA", (4, 4), color=(120, 130, 140, 255))
    feature = compute_image_feature(image)
    assert feature.shape == (5,)
    assert feature[3] < 1e-6
    assert abs(feature[4] - 1.0) < 1e-6
