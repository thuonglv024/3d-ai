import numpy as np
import pytest
import trimesh
from app.images import InvalidPhoto
from app.measurements import anatomical_perimeter, ellipse_perimeter, estimate_from_profiles, closed_torso_section, fit_measurement_targets, scale_lateral
from app.reconstruction import read_template, deform_template


def cylinder(radius, x=0):
    mesh=trimesh.creation.cylinder(radius=radius,height=1.7,sections=128)
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]))
    mesh.apply_translation([x,.85,0])
    return mesh


def test_ellipse_has_correct_circle_limit_and_scale():
    assert ellipse_perimeter(40,40)==pytest.approx(40*np.pi)
    assert ellipse_perimeter(40,30)>ellipse_perimeter(40,20)
    assert ellipse_perimeter(80,40)==pytest.approx(2*ellipse_perimeter(40,20))


def test_closed_section_excludes_arms_without_cutting_open_segments():
    mesh=trimesh.util.concatenate([cylinder(.20),cylinder(.06,-.45),cylinder(.06,.45)])
    perimeter,points=closed_torso_section(mesh,.83)
    assert perimeter==pytest.approx(40*np.pi,rel=.001)
    assert np.array_equal(points[0],points[-1])
    assert np.max(np.abs(points[:,0]))<=.201


def test_no_closed_torso_returns_error_not_zero_or_default():
    with pytest.raises(InvalidPhoto):
        closed_torso_section(cylinder(.1,.5),.83)


@pytest.mark.parametrize('scale',[.55,.8,1.4,1.9])
def test_lateral_fit_never_folds_vertex_order_near_armpits(scale):
    x=np.linspace(-.5,.5,1001)
    result=scale_lateral(x,scale,.14)
    assert np.all(np.diff(result)>0)
    assert result[500]==pytest.approx(0)


def test_estimates_depend_on_both_views_and_do_not_invent_inseam():
    fractions=np.linspace(.12,1.12,35)
    first,_=estimate_from_profiles(fractions,np.full(35,.2),np.full(35,.14),175,.22)
    second,_=estimate_from_profiles(fractions,np.full(35,.2),np.full(35,.16),175,.22)
    assert first['chest_cm']==pytest.approx(anatomical_perimeter(35,24.5,'chest_cm'),abs=.05)
    assert second['chest_cm']>first['chest_cm']
    assert first['height_cm']==175
    assert first['inseam_cm'] is None
    assert first['shoulder_width_cm']==38.5


def test_hip_target_stays_in_pelvic_band_not_upper_thigh():
    """v7: hip max is searched in 0.95–1.02 of the shoulder-hip span, not 1.12."""
    fractions = np.linspace(.12, 1.12, 35)
    for height_cm, width, depth in ((175.0, .22, .16), (162.0, .19, .14), (172.0, .25, .19)):
        widths = width + .02 * np.exp(-((fractions - 1.0) / .05) ** 2)
        depths = depth + .01 * np.exp(-((fractions - 1.0) / .05) ** 2)
        _, targets = estimate_from_profiles(fractions, widths, depths, height_cm, .22, True, .805, .534)
        hip = next(t for t in targets if t["key"] == "hip_cm")
        assert .52 <= hip["level"] <= .545
        # The old 1.12 search would land at ~0.501 H.
        assert hip["level"] > .52


def test_anatomical_calibration_matches_template_sections_within_tolerance():
    template=read_template()
    mesh_170=template.copy();mesh_170.apply_scale(1.70)
    fractions=np.linspace(.12,1.12,35)
    widths,depths=[],[]
    for frac in fractions:
        level=float(.805-frac*(.805-.515))
        _,curve=closed_torso_section(template,level)
        widths.append(float(np.ptp(curve[:,0])))
        depths.append(float(np.ptp(curve[:,2])))
    widths=np.asarray(widths);depths=np.asarray(depths)
    _,targets=estimate_from_profiles(fractions,widths,depths,170,.22)
    for target in targets:
        actual_cm,_=closed_torso_section(mesh_170,target['level']*1.70)
        assert abs(target['target_cm']-actual_cm)<1.5
        assert anatomical_perimeter(target['width_cm'],target['depth_cm'],target['key'])==pytest.approx(actual_cm,abs=1.5)

    def_widths=widths*1.08
    def_depths=depths*.96
    _,def_targets=estimate_from_profiles(fractions,def_widths,def_depths,170,.22)
    deformed=deform_template(template,fractions,def_widths,def_depths,170)
    fitted,profile=fit_measurement_targets(deformed,def_targets,170)
    assert profile['measurement_method']=='two_photo_anatomical_calibrated_v2'
    assert profile['fit_status']=='matched'
    assert profile['max_fit_error_cm']<1.5
    for target in def_targets:
        actual_cm,curve=closed_torso_section(fitted,target['level']*1.70)
        assert abs(actual_cm-target['target_cm'])<1.5
        cur_w=float(np.ptp(curve[:,0])*100)
        cur_d=float(np.ptp(curve[:,2])*100)
        assert (cur_d/cur_w)==pytest.approx(target['depth_cm']/target['width_cm'],rel=.02)


def test_fitted_mesh_matches_targets_and_exports_actual_sections():
    mesh=read_template();mesh.apply_scale(1.75)
    targets=[]
    for key,level,factor in [('chest_cm',.705,1.04),('waist_cm',.60,.96),('hip_cm',.505,1.03)]:
        perimeter,points=closed_torso_section(mesh,level*1.75)
        targets.append({'key':key,'label':key,'level':level,'target_cm':perimeter*factor,'width_cm':np.ptp(points[:,0])*100})
    result,profile=fit_measurement_targets(mesh,targets,175)
    assert result.extents[1]==pytest.approx(1.75)
    assert profile['fit_status']=='matched'
    assert profile['max_fit_error_cm']<=1.5
    assert not np.allclose(mesh.vertices,result.vertices)
    for section in profile['sections']:
        points=np.array(section['points_m'])
        actual=np.linalg.norm(np.diff(points,axis=0),axis=1).sum()*100
        assert actual==pytest.approx(section['model_cm'],abs=.1)


def test_fitting_is_independent_of_depth_origin():
    mesh=read_template();mesh.apply_scale(1.7)
    targets=[]
    for key,level in [('chest_cm',.705),('waist_cm',.60),('hip_cm',.505)]:
        perimeter,points=closed_torso_section(mesh,level*1.7)
        targets.append({'key':key,'label':key,'level':level,'target_cm':perimeter*1.08,'width_cm':np.ptp(points[:,0])*100})
    baseline,_=fit_measurement_targets(mesh,targets,170)
    shifted=mesh.copy();shifted.apply_translation([0,0,.4])
    fitted,_=fit_measurement_targets(shifted,targets,170)
    assert np.allclose(fitted.vertices-[0,0,.4],baseline.vertices,atol=1e-6)


def test_local_side_silhouette_bump_does_not_create_a_back_spike():
    fractions=np.linspace(.12,1.12,35)
    widths=np.full(35,.18)
    depths=.13+.065*np.exp(-((fractions-.66)/.07)**2)
    result=deform_template(read_template(),fractions,widths,depths,170)
    back=[]
    for level in np.linspace(.53,.70,18):
        _,curve=closed_torso_section(result,level*1.7)
        back.append(curve[:,2].min()/1.7)
    # A smooth prior must not imprint a several-cm spur over one 1%-height band.
    assert np.max(np.abs(np.diff(back)))<.012


def test_baseline_vs_calibrated_perimeter_comparison():
    """Keep baseline (apply_anatomical_calibration=False) vs calibrated (True) comparable."""
    from app.measurements import ANATOMICAL_SECTION_FACTORS

    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.19)
    depths = np.full(35, 0.135)
    vals_raw, targets_raw = estimate_from_profiles(
        fractions, widths, depths, 172.0, 0.22, apply_anatomical_calibration=False
    )
    vals_cal, targets_cal = estimate_from_profiles(
        fractions, widths, depths, 172.0, 0.22, apply_anatomical_calibration=True
    )
    for t_raw, t_cal in zip(targets_raw, targets_cal):
        key = t_raw["key"]
        assert t_raw["k_anatomy"] == 1.0
        assert t_cal["k_anatomy"] == pytest.approx(ANATOMICAL_SECTION_FACTORS[key], rel=1e-4)
        assert t_cal["target_cm"] == pytest.approx(t_raw["ellipse_cm"] * ANATOMICAL_SECTION_FACTORS[key], rel=1e-5)
        assert vals_cal[key] > vals_raw[key]


def test_sensitivity_to_height_error_and_clothing_dilation():
    """Verify linear sensitivity to height_cm (+/-5 cm) and clothing thickness (+4 px per side)."""
    fractions = np.linspace(0.12, 1.12, 35)
    h_px = 500.0
    base_w_px = np.full(35, 95.0)
    base_d_px = np.full(35, 68.0)
    widths = base_w_px / h_px
    depths = base_d_px / h_px

    # 1. Height sensitivity (+/- 5 cm around 170 cm -> +/- 2.94%)
    m_165, _ = estimate_from_profiles(fractions, widths, depths, 165.0, 0.22)
    m_170, _ = estimate_from_profiles(fractions, widths, depths, 170.0, 0.22)
    m_175, _ = estimate_from_profiles(fractions, widths, depths, 175.0, 0.22)
    assert m_175["chest_cm"] / m_170["chest_cm"] == pytest.approx(175.0 / 170.0, rel=2e-3)
    assert m_165["chest_cm"] / m_170["chest_cm"] == pytest.approx(165.0 / 170.0, rel=2e-3)

    # 2. Simulated clothing dilation (+4 px on each side => +8 px total width and depth)
    widths_padded = (base_w_px + 8.0) / h_px
    depths_padded = (base_d_px + 8.0) / h_px
    m_padded, _ = estimate_from_profiles(fractions, widths_padded, depths_padded, 170.0, 0.22)
    delta_chest = m_padded["chest_cm"] - m_170["chest_cm"]
    # +8 px on ~81.5 px average diameter (~+9.8%) increases chest circumference by ~8-10 cm
    assert 6.0 < delta_chest < 12.0
    assert m_padded["waist_cm"] > m_170["waist_cm"]


def test_validate_glb_mesh_verifies_metre_scale_and_rejects_corrupted_geometry():
    from app.measurements import validate_glb_mesh

    template = read_template()
    fractions = np.linspace(0.12, 1.12, 35)
    widths = np.full(35, 0.19)
    depths = np.full(35, 0.135)
    _, targets = estimate_from_profiles(fractions, widths, depths, 172.0, 0.22)
    deformed = deform_template(template, fractions, widths, depths, 172.0)
    fitted, profile = fit_measurement_targets(deformed, targets, 172.0)

    # 1. Valid mesh passes and populates profile["mesh_validation"]
    assert "mesh_validation" in profile
    validation = validate_glb_mesh(fitted, 172.0, profile["sections"])
    assert validation["valid"] is True
    assert validation["unit"] == "m"
    assert validation["actual_height_m"] == pytest.approx(1.72, abs=0.01)
    assert validation["degenerate_face_count"] == 0
    assert validation["finite_geometry"] is True
    assert validation["sections_validated"] == 3

    # 2. Wrong height scale (e.g. cm instead of m or wrong height) is rejected
    with pytest.raises(InvalidPhoto, match="Chiều cao mô hình 3D"):
        validate_glb_mesh(fitted, 185.0, profile["sections"])

    # 3. NaN vertex is rejected
    bad_nan = fitted.copy()
    bad_verts = bad_nan.vertices.copy()
    bad_verts[0, 1] = np.nan
    bad_nan.vertices = bad_verts
    with pytest.raises(InvalidPhoto, match="NaN/Inf"):
        validate_glb_mesh(bad_nan, 172.0, profile["sections"])

    # 4. Unaligned floor (shifted up by 5 cm) is rejected
    bad_floor = fitted.copy()
    bad_floor.apply_translation([0.0, 0.05, 0.0])
    with pytest.raises(InvalidPhoto, match="mặt sàn"):
        validate_glb_mesh(bad_floor, 172.0, profile["sections"])
