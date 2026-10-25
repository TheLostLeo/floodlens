import pytest


def test_deeper_unet_preserves_full_tile_shape():
    torch = pytest.importorskip("torch")
    from floodlens_research.segmentation_model import FloodUNet

    model = FloodUNet(in_channels=2, base_channels=8)
    result = model(torch.zeros((2, 2, 128, 128)))
    assert result.shape == (2, 1, 128, 128)


def test_deeper_unet_has_three_downsampling_stages():
    pytest.importorskip("torch")
    from floodlens_research.segmentation_model import FloodUNet

    model = FloodUNet(in_channels=2, base_channels=8)
    assert len(model.encoders) == 3
