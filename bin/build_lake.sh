#!/usr/bin/env bash

set -euo pipefail

LAKE_PATH=$1


# Convert VCFs to parquet:
# There are split between 'variants' and 'genotypes'
# All linked by an ID representing each variant
mkdir -p $LAKE_PATH/variants $LAKE_PATH/genotypes/samples/

# WARN: Bellow expects a 'vcf' subdir, with VCFs to convert
for vcf_path in $(ls $LAKE_PATH/vcf/*.vcf.gz)
do
	sample_name=$(basename ${vcf_path} .vcf.gz)
	variantplaner vcf2parquet -i ${vcf_path} \
		variants -o $LAKE_PATH/variants/${sample_name}.parquet \
		genotypes -o $LAKE_PATH/genotypes/samples/${sample_name}.parquet
	echo "Wrote: '$LAKE_PATH/variants/${sample_name}.parquet' and: '$LAKE_PATH/genotypes/samples/${sample_name}.parquet'"
done


# Compute parquets with all uniq variants (for annotation):
# VariantPlanner split them by chromosomes by default
variantplaner struct -i $LAKE_PATH/variants/*.parquet -- \
	variants -o $LAKE_PATH/uniq_variants/
echo "Wrote: $(ls -d $LAKE_PATH/uniq_variants/*)"


# Compute occurrence of each variant
echo "Computing '$LAKE_PATH/occurrences/all_samples.parquet' with occurrences of each variant for whole lake.."
mkdir -p $LAKE_PATH/occurrences
bin/count_occurr.py $LAKE_PATH


# Add annotations:
#   At this step normally to should annotate 'uniq_variants/chr*' with your favorite annotator
#   $ vep --input uniq_variants/chr1.vcf.gz
#   But here we use an already annotated VCF


PREFIX_ANN=vep_ann

# For SnpEff and VEP, annotations are nested and should be splitted first
#   We use the excellent vcf-reformatter to do that (https://github.com/flalom/vcf-reformatter)
vcf-reformatter \
	--transcript-handling split \
	--compress \
	$LAKE_PATH/annotations/${PREFIX_ANN}.vcf.gz
rm -v vep_ann_header.txt  # Useless intermediate file

# Then we add variant planer's id using dedicated script:
# MEMO: 'grch38.92.csv' is simply a file with length of each chromosome
bin/nestedAnn_to_parquet.py \
	${PREFIX_ANN}_reformatted.tsv.gz \
	$LAKE_PATH/grch38.92.csv \
	$LAKE_PATH/annotations/${PREFIX_ANN}.parquet

# Clean-up intermediate TSV
rm -v ${PREFIX_ANN}_reformatted.tsv.gz

exit

# Alt method
# Works mosty for Annovar were annotations are not nested
variantplaner -t 4 vcf2parquet \
	-c $LAKE_PATH/grch38.92.csv \
	-i $LAKE_PATH/annotations/annovar_MPA.vcf.gz \
	annotations -o $LAKE_PATH/annotations/annovar_MPA.parquet \
	--rename-id annovar_id
echo "Wrote: '$LAKE_PATH/annotations/annovar_MPA.parquet'"
