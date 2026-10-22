from reader.lines import build_lines
from reader.ocr import Box
from reader.postprocess import item_name, line_amount, parse_by_rules, resolve_item_lines, sum_matches, trim_to_total


def box(x, y, text, score=0.99, h=20):
    return Box(x, y, x + 50, y + h, text, score)


def test_lines_group_by_height_and_sort_by_x():
    boxes = [box(400, 102, "2.38 B"), box(10, 100, "KRAČE PIŠČANČJE IK"), box(200, 101, "0.796"),
             box(10, 130, "MLETO MESO MEŠANO")]
    assert build_lines(boxes) == ["KRAČE PIŠČANČJE IK | 0.796 | 2.38 B", "MLETO MESO MEŠANO"]


def test_lines_drop_junk_and_low_score():
    boxes = [box(0, 0, "*冰冰***冰*"), box(0, 40, "neberljivo", score=0.3), box(0, 80, "Skupaj")]
    assert build_lines(boxes) == ["Skupaj"]


# Vrstice, kot jih OCR vrne za naše račune.
SPAR = [
    "Izdelek | Količina | Cena Popust | Znesek",
    "KRAČE PIŠČANČJE IK | 0.796 | 5.79 | 2.23 | 2.38 B",
    "MLETO MESO MEŠANO | 0.486 | 9.17 | 0.00 | 4.46 B",
    "Skupa,j | EUR | 6.84",
    "DAL | BA | EUR | 6.84",
    "A= 0.00 %, B= 9.50 %",
]
BURGER = ["RADLER", "2x4,50 | 00'6", "Veggie burger | 8,50", "EUR 32,40", "Za plačilo:"]
KRAS = ["C NEFILTRIRANO PIVO 0,5L", "4,00 | 2x | 8,00", "C HEINIKEN 0%", "3,20 | 2x | 6,40", "14,40",
        "ZA PLAČILO EUR:"]
DM = [
    "S&S žepni robčki sens.15x10kos | 1,55 | 1",
    "Always plat.vložki noč.30kos | 6,65 | 2",
    "Voelkel Ingv.shot lim&med 95ml | 2,45 | 2",
    "Sanft&Sicher v1.t.pa.Kam.2x50k | 1,75 | 1",
    "Znesek | 50,10",
]


def test_trim_cuts_footer_after_total():
    assert trim_to_total(SPAR) == SPAR[:5]


def test_name_is_first_text_column():
    assert item_name(SPAR[1]) == "KRAČE PIŠČANČJE IK"


def test_rules_weighed_items_with_discount():
    assert parse_by_rules(SPAR) == {
        "items": [{"name": "KRAČE PIŠČANČJE IK", "quantity": 1, "price": 2.38},
                  {"name": "MLETO MESO MEŠANO", "quantity": 1, "price": 4.46}],
        "total": 6.84,
    }


def test_broken_ocr_amount_is_computed_from_marker():
    # OCR je 9,00 prebral kot "00'6", a "2x4,50" je na računu
    assert line_amount("2x4,50 | 00'6") == (900, 2)


def test_rules_two_line_items_with_quantity_marker():
    receipt = parse_by_rules(KRAS)
    assert receipt["items"] == [{"name": "C NEFILTRIRANO PIVO 0,5L", "quantity": 2, "price": 8.0},
                                {"name": "C HEINIKEN 0%", "quantity": 2, "price": 6.4}]
    assert sum_matches(receipt)


def test_rules_burger_total_above_label():
    receipt = parse_by_rules(BURGER)
    assert receipt["items"] == [{"name": "RADLER", "quantity": 2, "price": 9.0},
                                {"name": "Veggie burger", "quantity": 1, "price": 8.5}]
    assert receipt["total"] == 32.40


def test_vat_code_and_kos_in_name_are_not_quantities():
    receipt = parse_by_rules(DM)
    assert [i["quantity"] for i in receipt["items"]] == [1, 1, 1, 1]
    assert [i["price"] for i in receipt["items"]] == [1.55, 6.65, 2.45, 1.75]


def test_quantity_column_with_unit_price():
    receipt = parse_by_rules(["Izdelek | Količina | Cena Popust | Znesek",
                              "SPAR FF KRUH SEMENA 2 | 2 | 1,79 | 0,00 | 3,58 | B", "SKUPAJ | EUR | 3,58"])
    assert receipt["items"] == [{"name": "SPAR FF KRUH SEMENA 2", "quantity": 2, "price": 3.58}]


def test_model_line_numbers_resolve_two_line_items():
    receipt = resolve_item_lines([1, 3, 99, 6], KRAS, 14.40)
    assert [(i["name"], i["quantity"], i["price"]) for i in receipt["items"]] == [
        ("C NEFILTRIRANO PIVO 0,5L", 2, 8.0), ("C HEINIKEN 0%", 2, 6.4)]
