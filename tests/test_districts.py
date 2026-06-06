from data.districts import extract_district_taipei, extract_district_ntpc, NTPC_AREA_CODES


def test_taipei_district_from_road_name():
    assert extract_district_taipei("大安區忠孝東路四段") == "大安區"
    assert extract_district_taipei("信義區松仁路") == "信義區"


def test_taipei_district_unknown():
    assert extract_district_taipei("某某路") == "其他"


def test_ntpc_district_from_areacode():
    assert extract_district_ntpc("65000010") == "板橋區"
    assert extract_district_ntpc("65000020") == "三重區"


def test_ntpc_district_unknown_code():
    assert extract_district_ntpc("99999999") == "其他"


def test_ntpc_area_codes_dict_not_empty():
    assert len(NTPC_AREA_CODES) >= 10
