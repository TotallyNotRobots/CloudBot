import math

import pytest


@pytest.mark.parametrize('bearing,direction', {
    (360, 'N'),
    (0, 'N'),
    (1, 'N'),
    (15, 'NNE'),
    (30, 'NNE'),
    (45, 'NE'),
    (60, 'ENE'),
    (75, 'ENE'),
    (90, 'E'),
    (105, 'ESE'),
    (120, 'ESE'),
    (135, 'SE'),
    (150, 'SSE'),
    (165, 'SSE'),
    (180, 'S'),
})
def test_wind_direction(bearing, direction):
    from plugins.weather import bearing_to_card
    assert bearing_to_card(bearing).name == direction


@pytest.mark.parametrize('temp_f,temp_c', [
    (32, 0),
    (212, 100),
    (-40, -40),
])
def test_temp_convert(temp_f, temp_c):
    from plugins.weather import convert_f2c
    assert convert_f2c(temp_f) == temp_c


@pytest.mark.parametrize('mph,kph', [
    (0, 0),
    (43, 69.2),
])
def test_mph_to_kph(mph, kph):
    from plugins.weather import mph_to_kph
    assert math.isclose(mph_to_kph(mph), kph, rel_tol=1e-3)
