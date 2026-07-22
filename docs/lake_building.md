
# Lake building


## Intro

`TinyVV` can run over a lake of parquet files, but you have to build it first

We provide the script `bin/build_lake.sh <LAKE_PATH>` that creates all required subdirs

It relies heavily on the excellent [variant-planer](https://github.com/SeqOIA-IT/variantplaner) package, plus a few other custom steps

### An "id" to rule them all

One key feature of `variant-planer` is computing an `id` for each variant

It is present in all parquets (so not described explicitly in the rest of this doc)

And used as primary key linking them, to perform easy join operations

One step common to all, is sorting by `id`. This could speed up some operations (but not used currently)

<br>

## Input

Under `<LAKE_PATH>` argument of `build_lake.sh`, there should be a `vcf` subdir

In which you put VCFs to build your lake from

Ideally single-sample VCFs, not multi-samples ones (untested on multi-samples)

### Lake increment

If an input VCF already has a parquet under `genotypes/samples`, it is not recomputed

This way you can easily increment your lake by simply adding new VCFs to `vcf` subdir

Other steps are **always** recomputed (i.e. occurrences, uniq_variants)

<br>

## Genotypes

Parquets in `genotypes/samples` subdir contains variants splitted by samples

But only `FORMAT` fields from VCFs, i.e. "GT", but also "AD" and "DP" for example

Another interesting column is `sample`, which is the name of the sample showing the variant/genotype

As a post-processing, genotypes are converted from "1" ; "2" (originally produced by variant-planer)

To good-old "0/1" ; "1/1". **Only "0/0" are left "blank" (null in Polars), for performance considerations**

<br>

## variants / uniq_variants

Parquets in "variants" subdir contains "chr" ; "pos" ; "ref" ; "alt" values of each variant

They are only used as intermediate files to build `uniq_variants` subdir

This 2nd subdir is self-explanatory and parquets inside are splitted by chromosome

It is used both :

- To make variant annotation more efficient (annotate each variant once, instead of 1 time x each sample)
- To get back good-old `chr-pos-ref-alt` values, instead of efficient but obscure `id`

<br>

## Variant occurrences

We compute variant occurrence for all variants from all samples of the lake

It is done from `genotypes/samples` parquets

This way we can have the list of samples supporting each occurrence (`found_in` column, shown as tooltip for `occurrence` column)

<br>

## Annotations

`TinyVV` requires parquets with variants annotation under "annotations" subdir

This part is not handled by `build_lake.sh` script, but bellow are detailed steps to follow

### Theorical steps

1. Convert back `uniq_variants/*.parquet` to `*.vcf` using `variantplaner parquet2vcf` subcommand (see: https://seqoia-it.github.io/variantplaner/usage/#snpeff-annotations)

2. Annotate each VCF with your favorite tool (can be done in parallel over each chromosome)

3. Convert annotated VCF to parquet, method depends on the tool used :

- For un-nested annotations (such as with Annovar), you can use `variantplaner vcf2parquet annotations` subcommand

- For nested annotations (such as with VEP or SnpEff), you should 1st "flatten" them
We advice the excellent [vcf-reformatter](https://github.com/flalom/vcf-reformatter) to do that. 
Then we provide `bin/nestedAnn_to_parquet.py` which takes output TSV from `vcf-reformatter` and add `id`
(using `variant-planer`'s python API)

**MEMO**`: You can leave annotation parquets splitted by chromosome, this is 100% handled

### Example data

We provide already annotated VCFs under `examples/parquets_lake/annotations`

Following theorical steps above, we start at **step 3**

#### Nested annotations scenario

`vep_ann.vcf.gz` is annotated by VEP
(using "ANN" key of default "CSQ", which does not matter as auto-detected by `vcf-reformatter`)

```bash
# Flatten nested annotations and produce a TSV
vcf-reformatter \
    --transcript-handling split \
    --compress \
    examples/parquets_lake/annotations/vep_ann.vcf.gz

# Convert to parquet:
bin/nestedAnn_to_parquet.py \
    vep_ann_reformatted.tsv.gz \
    examples/parquets_lake/grch38.92.csv \
    examples/parquets_lake/annotations/vep_ann.parquet
```

#### Un-nested annotations scenario

`annovar_MPA.vcf.gz` is annotated by Annovar

```bash
variantplaner vcf2parquet \
        -c examples/parquets_lake/grch38.92.csv \
        -i examples/parquets_lake/annotations/annovar_MPA.vcf.gz \
        annotations -o examples/parquets_lake/annotations/annovar_MPA.parquet \
        --rename-id annovar_id
```

**WARNING 1** : Having annotation parquets annotated by different tools is not supported

**WARNING 2** : You better use same parameters (same databases, same versions etc) to produce all annotations parquet (not tested otherwise)
