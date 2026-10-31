import numpy as np
from app.arm_metrics import cross_section_width_px, limb_girth_from_mask


def _arm_mask(width_px=20, height=200):
    mask = np.zeros((height, 300), dtype=bool)
    mask[:, 140:160] = True   # dải dọc rộng đúng 20 px
    return mask


def test_cross_section_is_exact_on_a_vertical_band():
    mask = _arm_mask()
    # trục dọc theo dải: cắt vuông góc = 20 px
    # sai số 1 px do lấy mẫu rời rạc\n    assert 19.0 <= cross_section_width_px(mask, (150.0, 20.0), (150.0, 180.0)) <= 21.0


def test_cross_section_of_a_diagonal_arm_is_not_inflated():
    mask = np.zeros((300, 300), dtype=bool)
    for y in range(40, 260):
        x = y  # dải chéo 45 độ, dày 20 px theo phương vuông góc
        mask[y, x - 14:x + 14] = True   # 28 px ngang ~ 20 px vuông góc
    # cắt ngang hàng sẽ rộng ~20 px; cắt vuông góc cũng phải ~20 px, không phải 28
    along = cross_section_width_px(mask, (60.0, 60.0), (240.0, 240.0))
    assert along is not None and 18.0 <= along <= 22.0


def test_girth_from_mask_uses_pi_times_width():
    mask = _arm_mask()
    # rộng 20 px, 0.25 cm/px -> bán kính 2.5 cm -> chu vi 15.7 cm
    assert 15.0 <= limb_girth_from_mask(mask, (150.0, 20.0), (150.0, 180.0), 0.25) <= 16.5


def test_girth_refuses_when_the_cut_is_off_the_arm():
    mask = _arm_mask()
    assert limb_girth_from_mask(mask, (20.0, 20.0), (20.0, 180.0), 0.25) is None


