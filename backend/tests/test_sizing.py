import pytest
from pydantic import ValidationError
from app.sizing import (
    SizeChart,
    VALID_SIZING_SOURCES,
    filter_valid_sizing_measurements,
    recommend_size,
)


def chart(**changes):
    value={'name':'Fixture only','garment':'top','source':'illustrative','measurement_basis':'body_cm','rows':[
        {'size':'S','chest_cm':{'min':80,'max':90},'waist_cm':{'min':60,'max':70}},
        {'size':'M','chest_cm':{'min':90,'max':100},'waist_cm':{'min':70,'max':80}}]}
    value.update(changes)
    return SizeChart(**value)


def test_top_is_sized_by_chest_and_waist_cannot_veto_it():
    # Áo chọn size theo vòng ngực: eo lệch khỏi hàng của size không phủ quyết.
    assert recommend_size({'chest_cm':95,'waist_cm':75},chart())['candidates']==['M']
    assert recommend_size({'chest_cm':95,'waist_cm':65},chart())['candidates']==['M']
    outside = recommend_size({'chest_cm':150,'waist_cm':100},chart())
    assert outside['candidates']==[]
    assert outside['status']=='no_match'


def test_overlapping_boundaries_returns_all_candidates_instead_of_guess():
    assert recommend_size({'chest_cm':90,'waist_cm':70},chart())['candidates']==['S','M']


def test_invalid_chart_and_missing_measurements():
    with pytest.raises(ValidationError):
        chart(measurement_basis='garment_cm')
    with pytest.raises(ValidationError):
        chart(rows=[{'size':'X','chest_cm':{'min':100,'max':90}}])
    assert recommend_size({'chest_cm':None,'waist_cm':75},chart())['status']=='insufficient_measurements'


def test_optional_dimension_in_chart_requires_a_measurement():
    custom = chart(rows=[{'size':'M','chest_cm':{'min':90,'max':100},
                         'waist_cm':{'min':70,'max':80},'hip_cm':{'min':90,'max':100}}])
    res = recommend_size({'chest_cm':95,'waist_cm':75,'hip_cm':None}, custom)
    assert res['status'] == 'insufficient_measurements'
    assert res['missing'] == ['hip_cm']
    assert 'vòng mông' in res['message']
    assert len(res['comparisons']) == 1
    assert res['comparisons'][0]['checks']['hip_cm']['value_cm'] is None
    assert res['comparisons'][0]['checks']['hip_cm']['within'] is False


def test_extra_fields_ignored_on_models():
    # Extra fields on Range, SizeRow, SizeChart should be ignored without error
    data = {
        'name': 'Chart with extra fields',
        'garment': 'top',
        'source': 'illustrative',
        'measurement_basis': 'body_cm',
        'extra_chart_prop': 'should_be_ignored',
        'rows': [
            {
                'size': 'S',
                'description': 'Small size',
                'image': 'https://example.com/s.jpg',
                'chest_cm': {'min': 80, 'max': 90, 'unit': 'cm'},
                'waist_cm': {'min': 60, 'max': 70, 'tolerance': 1.5},
            }
        ],
    }
    c = SizeChart(**data)
    assert c.name == 'Chart with extra fields'
    assert len(c.rows) == 1
    assert c.rows[0].size == 'S'
    assert c.rows[0].chest_cm.min == 80


def test_garment_types_validation():
    # Dress with chest_cm and waist_cm
    dress_chart_2dims = SizeChart(
        name="Váy 2 số đo",
        garment="dress",
        rows=[
            {"size": "S", "chest_cm": {"min": 80, "max": 86}, "waist_cm": {"min": 62, "max": 68}},
            {"size": "M", "chest_cm": {"min": 86, "max": 92}, "waist_cm": {"min": 68, "max": 74}},
        ],
    )
    assert dress_chart_2dims.garment == "dress"

    # Dress with chest_cm, waist_cm, and hip_cm
    dress_chart_3dims = SizeChart(
        name="Váy 3 số đo",
        garment="dress",
        rows=[
            {"size": "S", "chest_cm": {"min": 80, "max": 86}, "waist_cm": {"min": 62, "max": 68}, "hip_cm": {"min": 88, "max": 94}},
            {"size": "M", "chest_cm": {"min": 86, "max": 92}, "waist_cm": {"min": 68, "max": 74}, "hip_cm": {"min": 94, "max": 100}},
        ],
    )
    assert dress_chart_3dims.garment == "dress"

    # Dress missing chest or waist fails
    with pytest.raises(ValidationError):
        SizeChart(
            name="Váy thiếu ngực",
            garment="dress",
            rows=[{"size": "S", "waist_cm": {"min": 62, "max": 68}, "hip_cm": {"min": 88, "max": 94}}],
        )

    # Outerwear requires chest and waist
    outerwear_chart = SizeChart(
        name="Áo khoác",
        garment="outerwear",
        rows=[{"size": "L", "chest_cm": {"min": 100, "max": 110}, "waist_cm": {"min": 85, "max": 95}}],
    )
    assert outerwear_chart.garment == "outerwear"

    # Bottom requires waist and hip
    with pytest.raises(ValidationError):
        SizeChart(
            name="Quần thiếu mông",
            garment="bottom",
            rows=[{"size": "30", "waist_cm": {"min": 75, "max": 80}}],
        )


def test_filter_valid_sizing_measurements_excludes_template_model_and_non_positive():
    assert VALID_SIZING_SOURCES == {"photo_estimate", "photo_with_prior", "user_input"}
    db_rows = [
        {"metric_key": "height_cm", "value_cm": 170.0, "source": "user_input"},
        {"metric_key": "chest_cm", "value_cm": 92.0, "source": "photo_with_prior"},
        {"metric_key": "waist_cm", "value_cm": 74.0, "source": "photo_with_prior"},
        {"metric_key": "hip_cm", "value_cm": 94.5, "source": "template_model"},
        {"metric_key": "arm_length_cm", "value_cm": None, "source": "unavailable"},
    ]
    filtered = filter_valid_sizing_measurements(db_rows, capture_mode="upper_body")
    assert filtered["chest_cm"] == 92.0
    assert filtered["waist_cm"] == 74.0
    assert filtered["hip_cm"] is None
    assert filtered["arm_length_cm"] is None

    # Non-positive values in recommend_size are treated as missing (None), never 0
    bottom_chart = SizeChart(
        name="Quần test",
        garment="bottom",
        rows=[{"size": "M", "waist_cm": {"min": 70, "max": 80}, "hip_cm": {"min": 90, "max": 100}}],
    )
    res_zero = recommend_size({"waist_cm": 75, "hip_cm": 0}, bottom_chart)
    assert res_zero["status"] == "insufficient_measurements"
    assert "hip_cm" in res_zero["missing"]
