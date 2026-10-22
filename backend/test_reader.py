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


SPAR_HEADER = "Izdelek | Količina | Cena Popust | Znesek"


def qty(lines, header=SPAR_HEADER):
    return [(i["name"], i["quantity"], i["price"]) for i in parse_by_rules([header, *lines, "SKUPAJ | EUR | 0,00"])["items"]]


def test_quantity_column_with_discount():
    assert qty(["SPAR FF KRUH SEMENA 2 | 2 | 1,79 | 0,50 | 3,08 | B"]) == [("SPAR FF KRUH SEMENA 2", 2, 3.08)]


def test_weight_in_quantity_column_is_one_piece():
    assert qty(["KRAČE PIŠČANČJE IK | 0.796 | 5.79 | 2.23 | 2.38 B"]) == [("KRAČE PIŠČANČJE IK", 1, 2.38)]


def test_quantity_as_whole_decimal():
    assert qty(["Burrtadella | 1,00 | 10.90 | 10,90"], "Naziv | Kol. Cena/em | Znesek") == [("Burrtadella", 1, 10.9)]
    assert qty(["Njoki | 2,00 | 4,50 | 9,00"], "Naziv | Kol. Cena/em | Znesek") == [("Njoki", 2, 9.0)]


def test_quantity_with_unit_kos():
    assert qty(["TUB Orange Blossom | 4,00 | KOS | 4.99 | 19,96"], "Naziv | Količina | ME | Cena | Znesek") == [
        ("TUB Orange Blossom", 4, 19.96)]


def test_quantity_in_middle_column_and_thousands():
    header = "Naziv | Cena | Količina | Znesek"
    assert qty(["OMARA | 3.758,75 EUR | 1 | 3.758,75 EUR", "PRT | 10,00 EUR | 2 | 20,00 EUR"], header) == [
        ("OMARA", 1, 3758.75), ("PRT", 2, 20.0)]


def test_quantity_from_unit_and_line_price_only():
    assert qty(["KOSILO'3 | 14.00 | 28.00"], "Artikel/Cena | Kol | Popust | Vrednost") == [("KOSILO'3", 2, 28.0)]


def test_missing_quantity_digit_is_computed_from_prices():
    # OCR je izpustil "3": 3 × 0,54 = 1,62
    assert qty(["ŠTRUČKA SENDVIČ 140G | 0,54 | 0,00 | 1,62 | B"]) == [("ŠTRUČKA SENDVIČ 140G", 3, 1.62)]


def test_one_piece_with_whole_unit_price_is_not_multiplied():
    assert qty(["Pivo | 1,00 | 5,00 | 5,00"], "Naziv | Kol. Cena/em | Znesek") == [("Pivo", 1, 5.0)]


def test_number_in_name_is_not_quantity():
    assert qty(["ARAŠIDI SLANI ÜLTJE 4 | 4,99 | 1,00 | 3,99 | B"]) == [("ARAŠIDI SLANI ÜLTJE 4", 1, 3.99)]


def test_weight_with_discount_is_one_piece():
    assert qty(["STEGNO ML.GOV. BK IK | 0,194 | 18,99 | 0,92 | 2,76 | B"]) == [("STEGNO ML.GOV. BK IK", 1, 2.76)]


def test_ocr_extra_digit_in_quantity():
    assert qty(["NAPITEK JABOLČNI CL.1 | 21 | 2,39 | 1,20 | 3,58 | C"]) == [("NAPITEK JABOLČNI CL.1", 2, 3.58)]


def test_quantity_column_trusted_when_unit_price_unreadable():
    assert qty(["RADENSKA CLASSIC 1,5L | 2 | 66.0 | 0,68 | 1,30 | B"]) == [("RADENSKA CLASSIC 1,5L", 2, 1.3)]
    assert qty(["NEKTAR H.D. BRUSNICA | 4 | 0,00 | 15,52 | C"]) == [("NEKTAR H.D. BRUSNICA", 4, 15.52)]


def test_one_with_extra_digit_stays_one():
    assert qty(["ČAJ LED.SOLA BRESKEV | 11 | 0,91 | 0,00 | 0,91 | C"]) == [("ČAJ LED.SOLA BRESKEV", 1, 0.91)]
    assert qty(["SPAR FREE MLEKO 1,5% | 12 | 1,39 | 0,32 | 1,07 | B"]) == [("SPAR FREE MLEKO 1,5%", 1, 1.07)]


def test_date_lines_and_unit_words_are_not_items():
    lines = ["DATUM 21.10.26 | URA 18:24:27", "TUB Orange Blossom | 9,5", "4,00 | KOS | 4.99 | 19,96"]
    assert qty(lines, "Naziv | Količina | ME | Cena | Znesek") == [("TUB Orange Blossom", 4, 19.96)]


# --- tabela ("lažni CSV") in popravek po vsoti ---
from reader.local import parse_rows  # noqa: E402

COLS = {"Izdelek": 10, "Količina": 200, "Cena": 270, "Popust": 330, "Znesek": 400}


def table_rows(rows):
    """Vrstice tabele kot škatle: vsaka celica na x položaju svojega stolpca."""
    out, y = [], 0
    for cells in rows:
        y += 30
        row = []
        for col, text in cells.items():
            x = COLS.get(col, col) if isinstance(col, str) else col
            row.append(Box(x - 20, y, x + 20, y + 20, text, 0.99))
        out.append(row)
    return out


def test_table_computes_broken_amount_from_columns():
    rows = table_rows([
        {"Izdelek": "Izdelek", "Količina": "Količina", "Cena": "Cena", "Popust": "Popust", "Znesek": "Znesek"},
        {"Izdelek": "NAMAZ PISTACIJA", "Količina": "1", "Cena": "9,29", "Popust": "2,32", "Znesek": "∠69"},
        {"Izdelek": "RIZ ARBORIO", "Količina": "1", "Cena": "5,29", "Popust": "0,00", "Znesek": "5,29"},
        {"Izdelek": "SKUPAJ", "Znesek": "12,26"},
    ])
    receipt, _ = parse_rows(rows)
    assert [(i["name"], i["price"]) for i in receipt["items"]] == [("NAMAZ PISTACIJA", 6.97), ("RIZ ARBORIO", 5.29)]


def test_table_missing_amount_for_weight():
    rows = table_rows([
        {"Izdelek": "Izdelek", "Količina": "Količina", "Cena": "Cena", "Popust": "Popust", "Znesek": "Znesek"},
        {"Izdelek": "STEGNO GOV", "Količina": "0,314", "Cena": "18,99", "Popust": "0,00"},
        {"Izdelek": "SKUPAJ", "Znesek": "5,96"},
    ])
    receipt, _ = parse_rows(rows)
    assert receipt["items"] == [{"name": "STEGNO GOV", "quantity": 1, "price": 5.96}]


def test_table_storno_removes_item():
    rows = table_rows([
        {"Izdelek": "Izdelek", "Količina": "Količina", "Cena": "Cena", "Popust": "Popust", "Znesek": "Znesek"},
        {"Izdelek": "SPAR MLEKO", "Količina": "1", "Cena": "1,39", "Popust": "0,00", "Znesek": "1,39"},
        {"Izdelek": "LEGO 75437", "Količina": "1", "Cena": "30,99", "Popust": "0,00", "Znesek": "30,99"},
        {"Izdelek": "LEGO 75437", "Količina": "-1", "Cena": "30,99", "Popust": "0,00", "Znesek": "-30,99"},
        {"Izdelek": "SKUPAJ", "Znesek": "1,39"},
    ])
    receipt, _ = parse_rows(rows)
    assert [i["name"] for i in receipt["items"]] == ["SPAR MLEKO"]


def test_rules_line_discount_with_minus_counted_once():
    lines = ["TUB Orange Blossom | 9,5", "4,00 | KOS | 4.99 | 19,96", "-9.98", "VRSTICNI POPUST EUR | -9,98",
             "SKUPAJEUR | 9,98"]
    receipt = parse_by_rules(lines)
    assert receipt["items"] == [{"name": "TUB Orange Blossom", "quantity": 4, "price": 9.98}]
    assert receipt["total"] == 9.98


def test_vat_rate_is_not_a_price():
    lines = ["REKREACIJA ILIRIJA (9,50%)", "1,00 *6,50 = | 6,50", "Skupaj | 6,50"]
    assert parse_by_rules(lines)["items"] == [{"name": "REKREACIJA ILIRIJA (9,50%)", "quantity": 1, "price": 6.5}]


def test_amount_without_name_is_added_only_if_it_completes_total():
    lines = ["Denkmit Cotton Dream | 2.95", "Organic Shop maska | 1,95", "8.45", "Znesek | 13,35"]
    assert [i["price"] for i in parse_by_rules(lines)["items"]] == [2.95, 1.95, 8.45]
