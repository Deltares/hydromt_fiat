# Unit test

from hydromt_fiat.workflows.vulnerability import Vulnerability

def test_create_step_function():
    x = Vulnerability()
    name = "roads_2"
    min_hazard_input = 0
    max_hazard_input = 15
    threshold_value = 0.5
    step_hazard_value = 2
    x.create_step_function()
    x.create_step_function(name, threshold_value, min_hazard_input, max_hazard_input, step_hazard_value)
    
