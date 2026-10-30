# AGENTS.md

Guidance for AI coding agents working in **HydroMT-FIAT**. Keep changes small,
follow the conventions below, and verify with the commands listed here.

## 1. What this repo is

HydroMT-FIAT is a [HydroMT](https://deltares.github.io/hydromt/stable) **plugin** that builds
[Delft-FIAT](https://deltares.github.io/Delft-FIAT/stable) flood-impact models from raw
data described in a HydroMT data catalog. It prepares exposure, hazard and
vulnerability data, and writes a FIAT model (a `settings.toml` plus data files).

- Python `>=3.12` (CI tests 3.12, 3.13, 3.14). License GPL-3.0-or-later. Beta status.
- Default branch: `main` (the PR template still says `master`; target `main`).
- Docs: <https://deltares.github.io/hydromt_fiat/latest>.

## 2. Repository structure

```
src/hydromt_fiat/
  fiat.py          FIATModel (HydroMT Model subclass): wires components, I/O, clip/reproject/move/set_*
  utils.py         Global string constants (CONFIG, GEOM, GRID, HAZARD, EXPOSURE_GEOM_FILE, ...) + pint helpers
  readers.py       read_config / read_geoms / read_grid / ... (file reading helpers)
  writers.py       write_geoms / write_grid / ... (file writing helpers)
  errors.py        Custom exceptions (e.g. MissingRegionError)
  version.py       __version__ (single source of the package version)
  components/      HydroMT ModelComponents holding model data; contain the user-facing create*/read/write steps
  workflows/       Pure data-manipulation functions called by components (no model/state access)
  settings/        Pydantic models for the FIAT settings.toml (geom vs. grid variants)
  gis/             Vector/raster helpers (raster.py, vector.py, *_utils.py)
  drivers/         Custom HydroMT drivers + URI resolvers (OSMDriver, resolvers.py)
  data/            fetch_data() (MinIO download of test/example data), registry.json
tests/             Mirrors src layout (components/, workflows/, settings/, gis/, drivers/, data/)
                   plus integration/ and system/
docs/              Sphinx docs (rst); changelog in docs/changelog.rst
examples/          data_catalog.yml (+ notebooks, stripped by nbstripout)
.github/           CI workflows, PR + issue templates
```

Entry points (in `pyproject.toml`): `hydromt.models` -> `hydromt_fiat.fiat`,
`hydromt.drivers` -> `hydromt_fiat.drivers`, `hydromt.uri_resolvers` -> `hydromt_fiat.drivers.resolvers`.

## 3. Architecture

Three layers; keep logic in the lowest layer that makes sense:

1. **`FIATModel`** ([fiat.py](src/hydromt_fiat/fiat.py)): thin. Registers components, orchestrates
   `read` / `write` / `clip` / `reproject` / `move` / `clear`, and holds the model type
   (`"geom"` or `"grid"`) set through `set_type`. Do not put data logic here.
2. **Components** ([components/](src/hydromt_fiat/components)): store data and expose HydroMT steps
   (`@hydromt_step`). A component fetches input via `self.model.data_catalog.get_*`, calls a
   **workflow function**, then stores the result with `self.set(...)`. Each component also implements
   `read`/`write` (filename defaults are class-level; hierarchy: argument > settings file > default).
3. **Workflows** ([workflows/](src/hydromt_fiat/workflows)): functions receive real data objects
   (`GeoDataFrame`, `DataFrame`, `xr.Dataset`), never catalog keys, and return data. Exported via
   `workflows/__init__.py`.

Components on `FIATModel` (attribute -> class -> data type):

| Attribute | Class | Data |
|---|---|---|
| `config` | `ConfigComponent` | pydantic settings (`GeomSettings` / `GridSettings`) |
| `region` | `RegionComponent` | one `GeoDataFrame` geometry (union on add, or replace) |
| `exposure_geoms` | `ExposureGeomsComponent` | dict of named `GeoDataFrame`s (`.fgb`) |
| `exposure_grid` | `ExposureGridComponent` | `xr.Dataset` |
| `hazard` | `HazardComponent` | `xr.Dataset` (`hazard.nc`) |
| `vulnerability` | `VulnerabilityComponent` | `VulnerabilityData(curves, identifiers)` `xr.Dataset` (`curves.nc`) |
| `output_geoms`, `output_grid` | `OutputGeomsComponent`, `OutputGridComponent` | FIAT results; `_build = False`, read via `model.read_output()` |

Model type matters: geom-only components return early (`_assert_model_type(GEOM, error=False)`)
when the model is a grid model, and vice versa.

Settings ([settings/](src/hydromt_fiat/settings)): pydantic v2 models mirror FIAT's `settings.toml`.
`Settings` is a discriminated union on `type` (`geom` | `grid`). Paths are serialized relative to the
config directory through `FileContext`. Add new config keys as typed `Field(..., description=...)`.

## 4. Main API

Typical build (see [tests/integration/test_build.py](tests/integration/test_build.py) for the canonical flow):

```python
from hydromt_fiat import FIATModel
from hydromt_fiat.utils import GEOM, DAMAGE, FLOOD_LEVEL

model = FIATModel(root=path, mode="w+", data_libs=[catalog_a, catalog_b])
model.set_config(method=FLOOD_LEVEL)
model.set_region(region_geojson_or_gdf)
model.set_type(GEOM)                                  # "geom" or "grid"
model.vulnerability.create("jrc_curves", "jrc_curves_link", unit="m", continent="europe")
model.hazard.create("flood_event")
model.exposure_geoms.create(exposure_fname="buildings", exposure_link_fname="buildings_link",
                            exposure_object_type_column="gebruiksdoel")
model.exposure_geoms.create_link(exposure_name="buildings", impact_type=DAMAGE)
model.exposure_geoms.create_max_value(exposure_name="buildings", impact_type=DAMAGE,
                                      exposure_cost_table_fname="jrc_damage", country="Netherlands")
model.exposure_geoms.update_column(exposure_name="buildings", columns=["ref", "method"],
                                   values=[0, "centroid"])
model.write()
```

- Model-level steps: `read`, `read_output`, `write`, `clear`, `clip`, `move`, `reproject`,
  `set_config`, `set_region`, `set_type`.
- Component steps: `<component>.create*`, `.update_*`, `.read`, `.write`, `.clip`, `.reproject`.
  Inspect the component file for the exact method list before adding or calling one.
- Every user-facing method is decorated with `@hydromt_step` so it works from HydroMT YAML workflows
  and the `hydromt` CLI.
- Public exports: `FIATModel`, `__version__` (top-level); each module defines `__all__`.

## 5. Data

| Kind | Format / type | Where |
|---|---|---|
| Raw inputs | Described in a HydroMT **data catalog** YAML (`GeoDataFrame`, `DataFrame`, `RasterDataset`); loaded by catalog name, never hard-coded paths | `examples/data_catalog.yml`, test catalogs |
| Exposure (geom) | Vector `.fgb` (FlatGeobuf); key columns such as `object_id`, `object_type`, `fn_damage_*`, `max_damage_*`, `ref`, `method`, `elevation` | `exposure/{name}.fgb` |
| Exposure (grid) | NetCDF via xarray | `exposure/spatial.nc` |
| Hazard | NetCDF `xr.Dataset` (events or return periods) | `hazard.nc` |
| Vulnerability | | NetCDF via xarray + identifiers (link) table | `curves.nc` |
| Region | GeoJSON | `region.geojson` |
| Settings | TOML (`tomlkit`), validated by pydantic | `settings.toml` |
| OSM data | Custom `OSMDriver` (osmnx) | `drivers/osm_driver.py` |

Units use `pint`. CRS handling uses `pyproj`; use `crs_representation` from `gis/utils.py` when
writing CRS to settings. Column and config key names are constants in
[utils.py](src/hydromt_fiat/utils.py): reuse/extend them instead of inlining string literals.

Test/example data is downloaded by `hydromt_fiat.data.fetch_data(name, cache_dir=...)` from a Deltares
MinIO bucket (checked against `data/registry.json`), cached in `.cache/` in the repo (tests) or
`~/.cache/hydromt-fiat`. Tests that need it require network access (`check_connection` in
`tests/conftest.py` fails or skips on connection errors). Never commit or print the contents of
`src/hydromt_fiat/data/*.key`.

## 6. Environment and commands

Use **pixi** (see `pyproject.toml` `[tool.pixi.*]`); do not use pip/conda/venv directly.
`pixi task list` is the authoritative list of all tasks; the table below is only a summary.

| Goal | Command |
|---|---|
| Unit tests with coverage (no integration/system) | `pixi run test-cov` |
| All tests | `pixi run test` |
| Last failed only | `pixi run test-lf` |
| Integration / system tests | `pixi run test-integration` / `pixi run test-system` |
| Specific env / Python | `pixi run -e test-py312 test` (`test-py312`, `-py313`, `-py314`) |
| Lint + format (pre-commit: ruff, ruff-format, whitespace, nbstripout) | `pixi run lint` |
| Type check | `pixi run mypy` |
| Docs (warnings are errors) | `pixi run docs-html` |
| Install git hooks | `pixi run install` |

Run the smallest relevant test first (e.g. `pixi run pytest tests/workflows/test_hazard.py`), then
widen. Pytest markers: `integration`, `system`, `serial`.

## 7. Code conventions

- **Style**: ruff, line length 88, `ruff format`. Lint rules: `E, F, I, PT, D`.
- **Docstrings**: numpy convention, required on public modules/classes/functions (tests exempt).
  Document every parameter, including defaults ("By default ...").
- **Typing**: modern syntax (`X | None`, `list[str]`), annotate signatures. mypy runs with the
  pydantic and numpy plugins and `disallow_any_generics`.
- **Imports**: absolute (`from hydromt_fiat.x import y`), isort order; define `__all__` in modules.
- **Logging**: `logger = logging.getLogger(f"hydromt.{__name__}")`; log user-relevant steps with
  `logger.info`, skipped/empty cases with `logger.warning`. No `print`.
- **Paths**: `pathlib.Path`; use `.as_posix()` when logging or formatting filenames.
- **Naming**: `snake_case` functions, `PascalCase` classes; constants in `utils.py` are
  `UPPER_CASE` (double underscore in the name = `_`-joined string, e.g. `COST__TYPE = "cost_type"`).
- **Errors**: raise specific exceptions with an actionable message (`MissingRegionError`,
  `FileNotFoundError`, `TypeError`, `ValueError`). Existing `# TODO Replace with custom error class`
  markers are fine to resolve when touching that code.
- **Components**: subclass the closest HydroMT component; implement `read`/`write` with the
  hierarchy argument > settings > default; call `self.root._assert_read_mode()` /
  `_assert_write_mode()`; use `_assert_model_type(...)`; set `_build = False` for output components.
- **Workflows**: pure, no `self`, no catalog lookups; return new data instead of mutating inputs.
- **Docstring/comment policy**: comment only what needs clarification.

## 8. Testing conventions

- Tests mirror the source tree: `tests/<subpackage>/test_<module>.py`; each folder has a `conftest.py`.
- Use **pytest** style (`PT` rules), `pytest-mock` and `responses` for mocking, `tmp_path` for files.
- Shared, session-scoped fixtures in [tests/conftest.py](tests/conftest.py) provide downloaded data
  (`build_data_catalog_path`, `model_data_path`, `hazard`, `exposure_vector`, ...). Prefer these over new
  downloads.
- Mark slow end-to-end builds `@pytest.mark.integration`; runs with the actual FIAT kernel
  (`delft_fiat`) are `system`.
- New behavior needs a unit test next to the module's existing tests; bug fixes need a regression test.

## 9. Contributing workflow

- Branch from `main`, open a PR against `main` using
  [.github/pull_request_template.md](.github/pull_request_template.md) (issue addressed, explanation,
  checklist: tests, up to date, tests + pre-commit pass, docs).
- Before pushing: `pixi run lint` and `pixi run test-cov`; for changes touching building or I/O also
  `pixi run test-integration`.
- Update [docs/changelog.rst](docs/changelog.rst) and docs/API (`docs/api.rst`) for user-visible changes.
- Dependencies live in `pyproject.toml` (`dependencies` + extras `dev`, `docs`, `examples`, `test`);
  `pixi.lock` is regenerated, not hand-edited. Update the README attribution list when adding a runtime dependency.
- Version lives only in `src/hydromt_fiat/version.py`.
- CI (`.github/workflows/`): lint, test matrix (ubuntu/windows x py312-314), docs, SonarQube, PyPI, wheel.
- Contributor guide upstream: <https://deltares.github.io/hydromt/latest/dev/contributing>.

## 10. Agent behaviour rules

Do:
- Read the relevant component/workflow and its tests before changing it; follow existing patterns.
- Keep changes surgical and scoped to the request; do not refactor or reformat unrelated code.
- Add or update tests and docstrings together with code changes.
- Run `pixi run lint` and the smallest relevant test selection before reporting work as done, and
  report the actual results.
- Ask before: adding or upgrading dependencies, changing public API signatures or `settings.toml`
  keys, changing CI workflows, or editing `pixi.lock`.

Do not:
- Read, print, edit or commit `src/hydromt_fiat/data/access.key` / `secret.key`, or any credentials.
- Hand-edit generated or cached artifacts: `pixi.lock`, `hydromt-fiat-sbom.json`, `.cache/`,
  `docs/_build`, `docs/_generated`.
- Commit downloaded test data, notebook outputs (nbstripout strips them) or large files.
- Bypass hooks (`--no-verify`) or silence linters/mypy with blanket ignores.
- Add logic to `FIATModel` that belongs in a component or workflow.
- Hard-code data paths or catalog keys inside workflows; go through the data catalog in components.
- Use pip, conda or venv; use pixi.

## 11. Known inconsistencies (verify before relying on them)

- PR template says `master`; the real default branch is `main`.
- `docs/user_guide`, `docs/setup_guide` and `docs/changelog.rst` are mostly empty stubs.
