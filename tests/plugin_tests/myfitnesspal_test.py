import importlib

from plugins import myfitnesspal
from tests.util import run_cmd


def test_mfp(mock_requests):
    importlib.reload(myfitnesspal)
    mock_requests.add(
        "GET",
        "http://www.myfitnesspal.com/food/diary/foo",
        body="""<table>
        <tr class="total"><td>5</td><td>9</td></tr>
        <tr class="alt"><td>7</td><td>12</td></tr>
        <tfoot><td class="nutrient-column">Bar<div>Foo</div></td></tfoot>
        </table>""",
    )
    assert run_cmd(myfitnesspal.mfp, "mfp", "foo") == [
        (
            "return",
            "Diary for foo: Bar: 9/12Foo (75%)  ("
            "http://www.myfitnesspal.com/food/diary/foo)",
        )
    ]
