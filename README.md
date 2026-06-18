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

## Usage
If starting from a VCF, first convert it to parquet with `vcf2parquet` (included in env):
```
vcf2parquet \
    -i examples/INPUT_hg19_annovar_MPA.vcf.gz \
    convert \
    -o examples/INPUT_hg19_annovar_MPA.parquet
```

Then start app and open it your favorite Web browser:
```
python -m tinyvv \
    --parquet examples/INPUT_hg19_annovar_MPA.parquet \
    -c examples/INPUT_hg19_annovar_MPA.yaml \
    --build hg19

# Open URL in browser: http://127.0.0.1:8050/
```

<br>

## The real deal
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

<br>

## Limitations / Known issues
- Parquet inputs (single or as lake) should be provided as command-line argument
- `chr-pos-ref-alt` col filter broken (always return "no match")
- Multiple columns are of type `list[str]` which fails most "text" filters (Polars error: `expected String type, got: list[str]`)
- Sorting by a column is possible through companion YAML, but you better be sorting your parquet beforehand (heavy in memory for large datasets)

<br>

## Credits
- Parts of the code were taken from this blog post : https://plotly.com/blog/polars-to-build-fast-dash-apps-for-large-datasets/
