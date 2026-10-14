import numpy as np
import pytest
from app.reconstruction import center_run_width, deform_template, read_template, segmentation_mask
from app.images import InvalidPhoto


@pytest.mark.parametrize("channel_axis", [False, True])
def test_mediapipe_mask_versions_produce_same_2d_silhouette(channel_axis):
    raw = np.zeros((12, 8), dtype=np.float32)
    raw[2:10, 3:6] = 0.9
    mask = segmentation_mask(raw[:, :, None] if channel_axis else raw)
    assert mask.shape == (12, 8)
    assert mask.dtype == bool
    yy, xx = np.where(mask)
    assert (yy.min(), yy.max(), xx.min(), xx.max()) == (2, 9, 3, 5)


def test_unexpected_multichannel_mask_is_rejected():
    with pytest.raises(InvalidPhoto):
        segmentation_mask(np.zeros((12, 8, 3)))


def test_torso_run_excludes_separated_arms():
    mask = np.zeros((10, 100), dtype=bool)
    mask[:, 5:15] = True
    mask[:, 30:65] = True
    mask[:, 85:95] = True
    assert center_run_width(mask, 5, 48) == 35


def test_mesh_changes_with_actual_width_and_depth_and_preserves_height():
    mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.20)
    depths = np.full(35, 0.14)
    first = deform_template(mesh, fractions, widths, depths, 175)
    second = deform_template(mesh, fractions, widths * 1.12, depths * 1.15, 175)
    assert np.isfinite(first.vertices).all()
    assert first.extents[1] == pytest.approx(1.75)
    assert first.faces.shape == second.faces.shape
    assert not np.allclose(first.vertices, second.vertices)
    torso = (first.vertices[:, 1] > 0.95) & (first.vertices[:, 1] < 1.30)
    assert np.ptp(second.vertices[torso, 2]) > np.ptp(first.vertices[torso, 2])
    exported = first.export(file_type="glb")
    assert exported[:4] == b"glTF"


def test_arm_lateral_shift_when_torso_widens():
    mesh = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.20)
    depths = np.full(35, 0.14)
    normal = deform_template(mesh, fractions, widths, depths, 175)
    wider = deform_template(mesh, fractions, widths * 1.25, depths, 175)
    assert wider.extents[0] > normal.extents[0]

