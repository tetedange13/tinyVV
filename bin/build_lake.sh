#!/usr/bin/env bash

set -euo pipefail

LAKE_PATH=$1
cd $LAKE_PATH


# Convert VCFs to parquet:
# There are split between 'variants' and 'genotypes'
# All linked by an ID representing each variant
mkdir -p variants genotypes/samples/

# WARN: Bellow expects a 'vcf' subdir, with VCFs to convert
for vcf_path in $(ls vcf/*.vcf.gz)
do
    sample_name=$(basename ${vcf_path} .vcf.gz)
    variantplaner vcf2parquet -i ${vcf_path} \
    	variants -o variants/${sample_name}.parquet \
    	genotypes -o genotypes/samples/${sample_name}.parquet
	echo "Wrote: 'variants/${sample_name}.parquet' and: 'genotypes/samples/${sample_name}.parquet'"
done


# Compute parquets with all uniq variants (for annotation):
# VariantPlanner split them by chromosomes by default
variantplaner struct -i variants/*.parquet -- \
	variants -o uniq_variants/
echo "Wrote: $(ls -d uniq_variants/*)"


# Add annotations:
# At this step normally to should annotate 'uniq_variants/*' with your favorite annotator
# For this example we reuse Annovar annotations already present
# MEMO: For SnpEff and VEP, annotations are nested and should be splitted first
#       (not for Annovar which put each thing in an INFO key)
# 'grch38.92.csv' is simply a file with length of each chromosome
# It is advised to use it (but not mandatory)
variantplaner -t 4 vcf2parquet \
	-c grch38.92.csv \
	-i annotations/annovar_MPA.vcf.gz \
	annotations -o annotations/annovar_MPA.parquet \
	--rename-id annovar_id
echo "Wrote: 'annotations/annovar_MPA.parquet'"
