# Unit test

from hydromt_fiat.workflows.vulnerability import Vulnerability

def test_create_step_function():
    x = Vulnerability()
    name = "roads_2"
    min_hazard_input = 0
    max_hazard_input = 15
    threshold_value = 0.5
    step_hazard_value = 2
    x.create_step_function("roads")
    x.create_step_function(name, threshold_value, min_hazard_input, max_hazard_input, step_hazard_value)



    assert x.functions  == {'roads': [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], 'roads_2': [0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]}
    assert x.hazard_values == [0.0, 0.49, 0.5, 0.59, 0.6, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]