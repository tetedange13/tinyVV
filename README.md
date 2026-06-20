# TinyVV
Tiny (but powerful) Variants Viewer. Powered by [Dash AG Grid](https://dash.plotly.com/dash-ag-grid), polars and [VariantPlaner](https://seqoia-it.github.io/variantplaner/). Inspired by [Captain-ACHAB](https://github.com/mobidic/Captain-ACHAB)

## Disclamer
Very early stage, **use at your own risk**

<br>

## Features
Read single VCF converted in parquet by `vcf2parquet`

Read multiple VCF converted to a lake by `variantPlaner`

No pagination (based on `AG Grid`'s "infinite scroll" feature)

Works on millions of variants without loading them in memory (thanks to `AG Grid` + `polars` as a sort of backend)

Filter by columns and if multiple -> AND logic applied

Colored genotypes

Customization through companion yaml (see [documentation](https://github.com/tetedange13/tinyVV/blob/dev-felix/docs/customization.md)):
* Column selection
* Sort on a column
* Add a tooltip for a column, with info from other columns (hidden if so)

Link to Franklin variant page through `#CHROMPOSREFALT` column

<br>

## Installation
```
git clone https://github.com/tetedange13/tinyVV.git
cd tinyVV
conda env create -f environment.yml
conda activate tinyVV
```

<br>

## Usages

`TinyVV` supports 2 types of inputs :
* A single VCF, possibly multi-samples and annotated (better but not mandatory),
* A lake of parquet files, built using VariantPlaner

### Single parquet
If starting from a VCF, first convert it to parquet with `vcf2parquet` (included in env):
```
vcf2parquet \
    -i examples/single_parquet/INPUT_hg19_annovar_MPA.vcf.gz \
    convert \
    -o examples/single_parquet/INPUT_hg19_annovar_MPA.parquet
```

Then start app and open it your favorite Web browser:
```
python -m tinyvv \
    --parquet examples/single_parquet/INPUT_hg19_annovar_MPA.parquet \
    --config examples/single_parquet/INPUT_hg19_annovar_MPA.yaml \
    --build hg19

# Open URL in browser: http://127.0.0.1:8050/
```

### The real deal for single parquet mode
`TinyVV` main goal was to support interpretation of whole-genome VCF without pagination. Following steps will let you experiment its power with a public VCF containing millions of variants !

```
# Download NIST's benchmark VCF for HG001:
wget https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/NISTv4.2.1/GRCh38/HG001_GRCh38_1_22_v4.2.1_benchmark.vcf.gz

# Count variants:
bcftools +counts HG001_GRCh38_1_22_v4.2.1_benchmark.vcf.gz
# -> Expected: ~ 3.9 millions variants

# Convert to parquet:
vcf2parquet \
    -i HG001_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
    convert \
    -o HG001_GRCh38_1_22_v4.2.1_benchmark.parquet

# Explore it with tinyVV:
python -m tinyvv \
    --parquet HG001_GRCh38_1_22_v4.2.1_benchmark.parquet
```

### Lake of parquets

First you need to build your lake. We provide `bin/build_lake.sh` for that, and provide example VCFs you can build a lake from
```
bash bin/build_lake.sh examples/parquets_lake
```

This scripts also show the main `variantplanner` commands to use.
They are taken from the [VariantPlaner documentation](https://seqoia-it.github.io/variantplaner/usage/)

Then visualize your samples:
```
python -m tinyvv \
    --lake examples/parquets_lake \
    -i B00GMSH B00GMSI B00GMSJ \
    --config examples/parquets_lake/INPUT_lake.yaml \
    --build hg19
```

<br>

## Limitations / Known issues
- Parquet inputs (single or as lake) should be provided as command-line argument
- `chr-pos-ref-alt` col filter broken (always return "no match")
- Multiple columns are of type `list[str]` which fails most "text" filters (Polars error: `expected String type, got: list[str]`)
- Sorting by a column is possible through companion YAML, but you better be sorting your parquet beforehand (heavy in memory for large datasets)
- INFO/ANN colnames differ between single_pq and lake inputs ('info_' prefix vs None)
- GT are shown as (0, 1, 2) with lake input (vs 0/0, 0/1, 1/1)

<br>

## Credits
- Parts of the code were taken from this blog post : https://plotly.com/blog/polars-to-build-fast-dash-apps-for-large-datasets/
