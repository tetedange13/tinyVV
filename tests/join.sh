#!/usr/bin/env bash


# Tests regarding join

## Check correctness of join

echo "MD5 of 'chr-pos-ref-alt + GT' from trio VCF:"
bcftools query -f '%CHROM-%POS-%REF-%ALT[\t%GT]' examples/single_parquet/INPUT_hg19_annovar_MPA.vcf.gz 2> /dev/null |
	sort -k1,1 |
	md5sum

echo "MD5 of 'chr-pos-ref-alt + GT' from lake:"
python tinyvv/query.py examples/parquets_lake B00GMSH,B00GMSI,B00GMSJ join_lake.tsv > /dev/null
sort -k1,1 -u join_lake.tsv | md5sum

rm -v join_lake.tsv
