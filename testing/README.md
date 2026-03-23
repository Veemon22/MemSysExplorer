# Tests

The tests in this folder help validate the outputs of profilers to aid in development and testing of the software.

## Validate ArrayCharacterization Results
### `run_all_arraycharacterization_samples.sh`

This script runs `./msxac` on all of the configs in the `/sample_configs` directory and saves the results to `/msxac_results`.

Usage: `./run_all_array_characterization_samples.sh`

---

### `validate_arraycharacterization_output.py`

This script validates that an msxAC output file correctly reflects the configuration specified in a YAML input file. It performs consistency checks between key parameters in the msxAC configuration (.yaml) and the generated msxAC output (.out).

Checks:
- `Capacity`
- `Associativity`
- `Cache Line Size`
- `Local Wire Type`
- `Global Wire Type`

Usage: python3 validate_arraycharacterization_output.py <config.yaml> <output.out>

Dependency: pyyaml

Install with `pip install pyyaml`

## Validate E2E Results
### `validate_drio_memsyspattern.py`

Validates general memory system pattern statistics.

Checks:
- `read_size` and `write_size` are **powers of two**
- `read_frequency == total_reads / execution_time`
- `write_frequency == total_writes / execution_time`

Usage: `python3 validate_drio_memsyspattern_config.py <path_to_json_file>`

---

### `validate_sniper_memsyspattern.py`

Validates memory system pattern data against the Sniper configuration.

Checks:
- `read_size` and `write_size` **match the configuration values**
- **Number of cores** matches the configuration
- **Per-core write histograms** sum to `total_writes`

Usage: `python3 validate_sniper_memsyspattern <config_file> <output_json_file>"`