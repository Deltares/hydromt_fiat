# Unit test

from hydromt_fiat.workflows.vulnerability import Vulnerability


def test_create_step_function():
    x = Vulnerability()
    name = "roads"
    min_hazard_input = 0
    max_hazard_input = 15
    threshold_value = 0.5
    step_hazard_value = 2
    x.create_step_function("roads_2")
    x.create_step_function(
        name, threshold_value, min_hazard_input, max_hazard_input, step_hazard_value
    )

    assert x.functions == {
        "roads_2": [
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ],
        "roads": [
            0.0,
            0.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ],
    }
    assert x.hazard_values == [
        0.0,
        0.49,
        0.5,
        0.59,
        0.6,
        1,
        2.0,
        3,
        4.0,
        5,
        6.0,
        7,
        8.0,
        9,
        10.0,
        11,
        13,
        15,
    ]
