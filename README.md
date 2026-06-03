# tinyVV
Tiny but powerful variants viewer. Powered by [Dash AG Grid](https://dash.plotly.com/dash-ag-grid) and polars. Inspired by [Captain-ACHAB](https://github.com/mobidic/Captain-ACHAB)

## Disclamer
Very early stage, should not be used

## Features
- Read VCF converted in parquet by `vcf2parquet`
- No pagination (based on `AG Grid`'s "infinite scroll" feature)
- Works on millions of variants without loading them in memory (thanks to `AG Grid` + `polars` as a sort of backend)
- Filter by columns and if multiple -> AND logic applied
- Colored genotypes

## Installation
```
git clone https://github.com/tetedange13/tinyVV.git
cd tinyVV
conda env create -f environment.yml
conda activate tinyVV
```

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
python main.py examples/INPUT_hg19_annovar_MPA.parquet

# Open URL in browser: http://127.0.0.1:8050/
```

## The real deal (FIXME)
`tinyVV` main goal was to support interpretation of whole-genome VCF without pagination. Following steps will let you try its power with a public VCF containing millions of variants !

```
# Download NIST's benchmark VCF for HG001:
wget https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/NA12878_HG001/NISTv4.2.1/GRCh37/HG001_GRCh37_1_22_v4.2.1_benchmark.vcf.gz

# Split multi-allelic variants first:
bcftools norm -m -any -Oz -o WGS_splitted.vcf.gz HG001_GRCh37_1_22_v4.2.1_benchmark.vcf.gz

# Count variants:
bcftools +counts WGS_splitted.vcf.gz
# -> Expected: ~ 3.9 millions variants

# Convert to parquet:
vcf2parquet \
    -i WGS_splitted.vcf.gz \
    convert \
    -o WGS_splitted.parquet

# Explore it with tinyVV:
python main.py WGS_splitted.parquet
```

## Limitations
- Parquet input should be provided as command-line argument
- Only 1 parquet file supported at once
- Input VCF should be splitted for multi-allelic variants (eg: `bcftools norm -m -any`), otherwise filter on "ALT" column is broken (`polars` error on using a list of str)
- Many many things hard-written in `main.py`

## Credits
- Parts of the code were taken from this blog post : https://plotly.com/blog/polars-to-build-fast-dash-apps-for-large-datasets/