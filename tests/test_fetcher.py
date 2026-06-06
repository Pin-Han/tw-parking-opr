from data.fetcher import parse_taipei_xml


SAMPLE_TAIPEI_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<DATA>
    <ROAD>
        <cellStatusList>
            <cell>
                <cellStatus>1</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 19:06:58</data_Dt>
                <psId>01</psId>
            </cell>
            <cell>
                <cellStatus>2</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 17:54:59</data_Dt>
                <psId>02</psId>
            </cell>
            <cell>
                <cellStatus>1</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 17:12:24</data_Dt>
                <psId>08</psId>
            </cell>
        </cellStatusList>
        <roadSegAvail>-99</roadSegAvail>
        <roadSegCarType>1</roadSegCarType>
        <roadSegFee>30元</roadSegFee>
        <roadSegID>1002053</roadSegID>
        <roadSegName>中山區中山北路一段53巷</roadSegName>
        <roadSegtimeEnd>20:00</roadSegtimeEnd>
        <roadSegtimeStart>07:00</roadSegtimeStart>
        <roadSegTotalValue>8</roadSegTotalValue>
        <roadSegUpdatetime>20260606T204009</roadSegUpdatetime>
        <roadSegUsage>-99.0</roadSegUsage>
    </ROAD>
    <ROAD>
        <cellStatusList>
            <cell>
                <cellStatus>2</cellStatus>
                <coord_X>0.0</coord_X>
                <coord_Y>0.0</coord_Y>
                <data_Dt>2026-06-06 10:00:00</data_Dt>
                <psId>01</psId>
            </cell>
        </cellStatusList>
        <roadSegAvail>-99</roadSegAvail>
        <roadSegCarType>1</roadSegCarType>
        <roadSegFee>40元</roadSegFee>
        <roadSegID>2001001</roadSegID>
        <roadSegName>大安區忠孝東路四段</roadSegName>
        <roadSegtimeEnd>20:00</roadSegtimeEnd>
        <roadSegtimeStart>07:00</roadSegtimeStart>
        <roadSegTotalValue>20</roadSegTotalValue>
        <roadSegUpdatetime>20260606T204009</roadSegUpdatetime>
        <roadSegUsage>-99.0</roadSegUsage>
    </ROAD>
</DATA>
"""


def test_parse_taipei_xml_record_count():
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    assert len(records) == 2


def test_parse_taipei_xml_first_record_fields():
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    r = records[0]
    assert r["source"] == "taipei"
    assert r["road_id"] == "1002053"
    assert r["road_name"] == "中山區中山北路一段53巷"
    assert r["district"] == "中山區"
    assert r["total_spots"] == 3
    assert r["available_spots"] == 1
    assert abs(r["usage_rate"] - 2 / 3) < 0.01
    assert r["latitude"] is None
    assert r["longitude"] is None


def test_parse_taipei_xml_usage_calculated_from_cells():
    records = parse_taipei_xml(SAMPLE_TAIPEI_XML)
    r = records[1]
    assert r["usage_rate"] == 0.0
    assert r["available_spots"] == 1
    assert r["total_spots"] == 1


from data.fetcher import parse_ntpc_csv

SAMPLE_NTPC_CSV = """id,cellid,name,day,hour,pay,paycash,memo,roadid,roadname,cellstatus,isnowcash,parkingstatus,latitude,longitude,countycode,areacode
155355,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,"禁停0700-0900,1700-1900;",T63,建一路,Y,false,3,25.001812,121.487941,65000,65000030
155362,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,"禁停0700-0900,1700-1900;",T63,建一路,N,false,3,25.001441,121.487956,65000,65000030
155363,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,,T64,中正路,Y,false,3,25.002000,121.488000,65000,65000030
155364,0,時段性禁停停車位,週一-週五,07:00-20:00,計時收費,30元/時,,T64,中正路,Y,false,3,25.002100,121.488100,65000,65000030
"""


def test_parse_ntpc_csv_aggregates_by_road():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    assert len(records) == 2


def test_parse_ntpc_csv_usage_rate():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    records.sort(key=lambda r: r["road_name"])
    assert records[0]["road_name"] == "中正路"
    assert records[0]["usage_rate"] == 1.0
    assert records[0]["total_spots"] == 2
    assert records[0]["available_spots"] == 0
    assert records[1]["road_name"] == "建一路"
    assert records[1]["usage_rate"] == 0.5
    assert records[1]["available_spots"] == 1


def test_parse_ntpc_csv_district_from_areacode():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    for r in records:
        assert r["district"] == "中和區"


def test_parse_ntpc_csv_has_coordinates():
    records = parse_ntpc_csv(SAMPLE_NTPC_CSV)
    for r in records:
        assert r["latitude"] is not None
        assert r["longitude"] is not None
        assert r["source"] == "ntpc"
