import sys
import polars
from variantplaner import Vcf

vcf = Vcf()

try:
    vcf.from_path(sys.argv[1], "examples/parquets_lake/grch38.92.csv")
except variantplaner.exception.NotAVCFError:
    print("snpeff_annotations.vcf seems to have error")
    exit(1)
except variantplaner.exception.NoContigsLengthInformationError:
    print("snpeff_annotations.vcf header seems not contain contig information")
    exit(2)

lf = vcf.lf.with_columns(vcf.header.info_parser())
lf = lf.drop(["chr", "pos", "ref", "alt", "filter", "qual", "info"])
#lf = lf.rename({"vid": "id"})
lf = lf.explode("ANN")
#lf = lf.cast({"id": polars.UInt64})

lf = lf.with_columns(
    [
        polars.col("ANN")
        .str.split("|")
        .cast(polars.List(polars.Utf8()))
        .alias("ann"),
    ]
).drop("ANN")

lf = lf.with_columns(
    [
        polars.col("ann").list.get(1).alias("effect"),
        polars.col("ann").list.get(2).alias("impact"),
        polars.col("ann").list.get(3).alias("gene"),
        polars.col("ann").list.get(4).alias("geneid"),
        polars.col("ann").list.get(5).alias("feature"),
        polars.col("ann").list.get(6).alias("feature_id"),
        polars.col("ann").list.get(7).alias("bio_type"),
        polars.col("ann").list.get(8).alias("rank"),
        polars.col("ann").list.get(9).alias("hgvs_c"),
        polars.col("ann").list.get(10).alias("hgvs_p"),
        polars.col("ann").list.get(11).alias("cdna_pos"),
        polars.col("ann").list.get(12).alias("cdna_len"),
        polars.col("ann").list.get(13).alias("cds_pos"),
        polars.col("ann").list.get(14).alias("cds_len"),
        polars.col("ann").list.get(15).alias("aa_pos"),
    ]
).drop("ann")

lf.sink_parquet("snpeff_annotations.parquet")
