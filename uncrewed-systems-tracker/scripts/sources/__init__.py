# Source connectors for the regulatory tracker. Each module exposes
#   fetch(keys: dict) -> common.SourceResult
# and must never raise; problems are reported via SourceResult.status/detail.
