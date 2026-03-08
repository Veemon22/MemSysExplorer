import yaml
import re
import sys


def parse_output(path):
    with open(path) as f:
        text = f.read()

    result = {}

    # capacity
    m = re.search(r"Capacity\s*:\s*(\d+)(KB|MB|GB)", text)
    if m:
        result["capacity"] = int(m.group(1))
        result["capacity_unit"] = m.group(2)

    # associativity
    m = re.search(r"Cache Associativity:\s*(\d+)", text)
    if m:
        result["associativity"] = int(m.group(1))

    # cache line size
    m = re.search(r"Cache Line Size:\s*(\d+)Bytes", text)
    if m:
        result["cache_line_size"] = int(m.group(1))

    # local wire
    m = re.search(r"Local Wire:\n\s*- Wire Type : ([^\n]+)", text)
    if m:
        result["local_wire_type"] = m.group(1).strip()

    # global wire
    m = re.search(r"Global Wire:\n\s*- Wire Type : ([^\n]+)", text)
    if m:
        result["global_wire_type"] = m.group(1).strip()

    return result


def validate(config_path, output_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    out = parse_output(output_path)

    errors = []

    # capacity
    cap = config["Capacity"]["Value"]
    unit = config["Capacity"]["Unit"]

    if out.get("capacity") != cap or out.get("capacity_unit") != unit:
        errors.append(f"Capacity mismatch: config={cap}{unit}, output={out.get('capacity')}{out.get('capacity_unit')}")

    # associativity
    if config.get("Associativity") != out.get("associativity"):
        errors.append(
            f"Associativity mismatch: config={config.get('Associativity')}, output={out.get('associativity')}"
        )

    # cache line size
    expected_line = config["WordWidth"] // 8
    if expected_line != out.get("cache_line_size"):
        errors.append(
            f"Cache line size mismatch: config={expected_line}B, output={out.get('cache_line_size')}B"
        )

    # local wire
    local_wire = config["LocalWire"]["Type"].replace("Local", "Local ").replace("Global", "Global ")
    if out.get("local_wire_type") and local_wire.split()[0] not in out["local_wire_type"]:
        errors.append(
            f"Local wire type mismatch: config={config['LocalWire']['Type']}, output={out.get('local_wire_type')}"
        )

    # global wire
    global_wire = config["GlobalWire"]["Type"].replace("Local", "Local ").replace("Global", "Global ")
    if out.get("global_wire_type") and global_wire.split()[0] not in out["global_wire_type"]:
        errors.append(
            f"Global wire type mismatch: config={config['GlobalWire']['Type']}, output={out.get('global_wire_type')}"
        )

    if errors:
        print("❌ Validation FAILED")
        for e in errors:
            print(" -", e)
        return False
    else:
        print("✅ Validation PASSED")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_arraycharacterization_output.py config.yaml output.out")
        sys.exit(1)

    validate(sys.argv[1], sys.argv[2])