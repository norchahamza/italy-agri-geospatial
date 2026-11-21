from agri.cleaning.silver import crop_expr, to_double, zfill_code
from pyspark.sql import functions as F

CMAP = {"wheat": ["frumento", "durum wheat"], "maize": ["mais"]}


def test_numeric_and_code_cleaning(spark):
    df = spark.createDataFrame([("1", "12,5", "Frumento"), ("12", "1.234,5", " MAIS "), ("7", "n.d.", "Kiwi")],
                               "code string, v string, crop string")
    df = to_double(df, "v").withColumn("code", zfill_code("code")).withColumn("crop", crop_expr("crop", CMAP))
    rows = {r.code: r for r in df.collect()}
    assert rows["001"].v == 12.5 and rows["001"].crop == "wheat"
    assert rows["012"].v == 1234.5 and rows["012"].crop == "maize"
    assert rows["007"].v is None and rows["007"].crop == "kiwi"


def test_location_quotient_formula(spark):
    # 2 provinces, 2 crops: LQ = (area_pc/area_p) / (nat_crop/nat_total)
    df = spark.createDataFrame([("P1", "a", 80.0), ("P1", "b", 20.0), ("P2", "a", 20.0), ("P2", "b", 80.0)],
                               "p string, c string, area double")
    from pyspark.sql import Window
    w_p, w_c = Window.partitionBy("p"), Window.partitionBy("c")
    r = df.withColumn("lq", (F.col("area") / F.sum("area").over(w_p)) / (F.sum("area").over(w_c) / F.lit(200.0)))
    p1a = [x for x in r.collect() if x.p == "P1" and x.c == "a"][0]
    assert abs(p1a.lq - 0.8 / 0.5) < 1e-9
