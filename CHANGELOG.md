# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<br>

## [Not planned]

### Feature

- Let user select parquet file through page

### Reason

- Browser convert loaded file to base64, which can be slow on big file. Also feature not very relevant if someday app sits on a parquets lake

<br>

## [Unreleased]

### Added

- Build on a lake of parquets using [variantplaner](https://github.com/SeqOIA-IT/variantplaner)
- Add an equivalent of DataTables' [searchBuiler](https://datatables.net/extensions/searchbuilder/) (with OR logic too)

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
