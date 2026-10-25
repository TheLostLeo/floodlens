from datetime import date

from floodlens_research.events import antecedent_dates, flatten_positions


def test_flatten_positions_handles_polygon_coordinates():
    assert flatten_positions([[[80, 12], [81, 13]]]) == [(80.0, 12.0), (81.0, 13.0)]


def test_antecedent_dates_includes_event_day():
    assert antecedent_dates("2016-08-12", 3) == (date(2016, 8, 10), date(2016, 8, 12))
