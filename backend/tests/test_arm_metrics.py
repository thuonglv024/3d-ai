from app.arm_metrics import arm_length_cm, arm_measurements, limb_girth_cm


def test_limb_girth_matches_the_tape_on_p01b():
    # P01b: tape bắp tay 23 cm, cẳng tay 20 cm; cm/px 0.2301
    cm_per_px = 0.2301
    bicep_radius = 23 / (2 * 3.14159265) / cm_per_px
    forearm_radius = 20 / (2 * 3.14159265) / cm_per_px
    assert limb_girth_cm(bicep_radius, cm_per_px) == 23.0
    assert limb_girth_cm(forearm_radius, cm_per_px) == 20.0


def test_limb_girth_rejects_impossible_radii():
    assert limb_girth_cm(None, 0.23) is None
    assert limb_girth_cm(0, 0.23) is None
    assert limb_girth_cm(1.0, 0.23) is None      # ~1.4 cm chu vi: quá nhỏ
    assert limb_girth_cm(100.0, 0.23) is None    # ~144 cm chu vi: quá lớn


def test_arm_length_sums_shoulder_elbow_wrist():
    points = [[0.0, 0.0] for _ in range(33)]
    points[11] = [100.0, 100.0]
    points[13] = [100.0, 200.0]   # 100 px
    points[15] = [100.0, 280.0]   # 80 px
    # 180 px * 0.25 cm/px = 45 cm
    assert arm_length_cm(points, 0.25) == 45.0


def test_arm_length_rejects_an_unusable_scale_or_pose():
    points = [[0.0, 0.0] for _ in range(33)]
    points[11] = [100.0, 100.0]
    points[13] = [100.0, 120.0]
    points[15] = [100.0, 140.0]
    assert arm_length_cm(points, 0.25) is None   # 10 cm: không phải tay người
    assert arm_length_cm(points, 0.0) is None


def test_arm_measurements_keeps_none_for_unmeasured_parts():
    points = [[0.0, 0.0] for _ in range(33)]
    points[11] = [0.0, 0.0]
    points[13] = [0.0, 120.0]
    points[15] = [0.0, 240.0]
    out = arm_measurements(points, 0.25, None, 12.8)
    assert out["arm_length_cm"] == 60.0
    assert out["bicep_cm"] is None
    assert out["forearm_cm"] == 20.1

