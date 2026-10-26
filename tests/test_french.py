"""The proxy parser must select value weighting and convert percentages exactly once."""
import runpy
from pathlib import Path

import pytest

parse = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/prepare_french.py"))["parse_value_weighted"]
HEADER = "Average Value Weighted Returns -- Daily\n,Cnsmr,Manuf,HiTec,Hlth,Other\n"


def test_proxy_block_and_units():
    source = HEADER + "20150102,1,-2,0,0.5,3\n20150105,0,0,0,0,0\n\nAverage Equal Weighted Returns -- Daily\n20150102,9,9,9,9,9\n"
    result = parse(source)
    assert len(result) == 2
    assert result[0] == ["2015-01-02", .01, -.02, 0., .005, .03]


@pytest.mark.parametrize("row", ["20150102,-99.99,0,0,0,0", "20150102,nan,0,0,0,0", "20150102,0,0,0,0", "20150105,0,0,0,0,0\n20150102,0,0,0,0,0"])
def test_proxy_rejects_missing_malformed_and_unsorted(row):
    with pytest.raises(ValueError):
        parse(HEADER + row + "\n")
