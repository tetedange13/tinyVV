# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<br>

## [Not planned]

### Feature

(f1) Let user select parquet file through page

(f2) Use ".shrink_dtype()" to solve problem of "List(str)" cols

### Reason

(r1) Browser convert loaded file to base64, which can be slow on big file. Also feature not very relevant if app sits on a parquets lake

(r2) ".shrink_dtype()" do not run on lazyFrame

<br>

## [Unreleased]

### Added

- New conf section "treat_as_number", to cast some columns as number (eg: GnomAD_freq)

<br>

## [0.9.0] - Unreleased

### Fixed

- Better match dtype inferred by Polars and ag-grid's "filterType".
This way more cols can correctly be filtered as "number" (if dtype correctly inferred by Polars)
- "and" logic was always applied, even if "or" were selected
- Put "logic" (and/or) as 1st on the left (smoother this way)
- Show back "no rows to show" when filtering returns nothing (broken with searchBuilder)

### Added

- Can now save filters (JSON file) and load filters from previously saved file

<br>

## [0.8.0] - 2026-07-28

### Changed

- Filtering now made through an equivalent of DataTables' [searchBuiler](https://datatables.net/extensions/searchbuilder/) (with AND/OR logic too)

### Added

- First test on join correctness

<br>

## [0.7.0] - 2026-07-22

### Fixed

- [pq_lake] Reduce number of callbacks when scrolling
- Handle "no config" better
- [pq_lake] Specify 'set_sorted(id)' in "count_occurr" was wrong
- [pq_lake] Improve filtering and remove abusive 'List(str)->str' casts
- [single_pq] Compute AB col too
- Correctly show "no matching rows" when filtering returns nothing. But still empty rows after filtered rows

### Changed

- [pq_lake] Do more transformations at lake building (-> once instead of at every callback)
- [pq_lake] Set collect_engine to "streaming". Known bug with "in-memory" engine in Polars v1.41 and above (https://github.com/pola-rs/polars/issues/28419). "streaming" engine is expected to be faster and become default in v1.43 anyway
- [lake_build] Do not handle "annotations" anymore
- [lake_build] Do not recompute "genotypes/samples/sample.parquet" if exist (easier to increment lake). Other parquets are always recomputed (occurr, uniq_variants)

### Added

- [pq_lake] Documentation for lake building

<br>

## [0.6.1] - 2026-07-16

### Fixed

- Set correct "filterType" for other FORMAT columns
- Disable filtering on "AD" column for now (dtype incompatibily)

<br>

## [0.6.0] - 2026-07-15

### Fixed

- Wrong "rowCount" passed to ag-grid (should ALWAYS be "total rows")
- Simplify "GT" colname: "format_sample_GT" -> "sample_GT"
- Total rows counting now faster on "real deal" datasets
- Previous commit broke "cols in tooltip are hidden" behaviour
- Sort column is automatically added (even if not in "col_selection")
- Set a few columns width
- "blank / non-blank" filtering was broken

### Added

- Other FORMAT columns (GQ, DP, AD) and compute AB (VAF)
- "1st_sample_GT" has tooltip with FORMAT values of other samples
- "bin/build_lake.sh" now use VEP/SnpEff ann/csq annotations by default (based on script "bin/nestedAnn_to_parquet.py")
- [pq_lake] Building lake compute variants occurrence, added as column (with list of samples supporting occurrence as tooltip)

<br>

## [0.5.1] - 2026-07-12

### Fixed

- Renamed columns with containing a dot '.', it is causing issues with Dash and/or Polars
- Can filter on columns, but only as "text" (except for "sort" column)
- [parquets_lake] GT format is now "0/0;0/1;1/1" and not "null;1;2"

### Changed

- [single_parquet] Remove "info_" prefix in colnames (coherent with "parquets_lake" now)
- [parquets_lake] Full join of GT now, not left join from 1st one
- Some performance improvements

<br>

## [0.5.0] - 2026-06-20

### Changed

- Previous parameter `-i/--input` turned into `-p/--parquet`
- Config not guessed ("sample.yaml") anymore, should be passed to `-c/--config`
- Previous argument `-l/--list_cols` (to list columns and exit) renamed as `-s/--show_cols`

### Added

- Run from a parquets lake built with [VariantPlaner](https://seqoia-it.github.io/variantplaner/) (`-l/--lake` + `-i/--input`)
- Example files + build script for 'parquets lake' usage

<br>

## [0.4.0] - 2026-06-11

### Added

- Columns selection through companion YAML
- New argument (`-l / --list_cols`) to list columns and exit (help for `col_selection`)
- Documentation for customization through companion YAML 

<br>

## [0.3.0] - 2026-06-10

### Added

- New "chr:pos:ref:alt" column with clickable link to Franklin

<br>

## [0.2.0] - 2026-06-08

### Added

- Support companion YAML for configuration (auto-detect "sample.yaml" near "sample.parquet")
- Allow to sort on a column (columns not sortable otherwise)
- Allow to define columns showing a tooltip, with data from other columns (eg: pop_freq)

### Fixed

- Modules splitting were incorrect

<br>

## [0.1.2] - 2026-06-04

### Changed

- Nothing concreat, only project structure (packaging + split functions)

<br>

## [0.1.1] - 2026-06-03

### Changed

- Auto-detect GT columns by their name
- Show all INFO columns by default (from their name too)

### Fixed

- `The real deal` section of README now works

<br>

## [0.1.0] - 2026-06-03

### Added

- Infinite scroll + polars backend works on million rows (tested on NIST's HG002 benchmark VCF)
- Filter on columns + cumulative filters (AND logic only)
- Colored genotypes colums
