#!/usr/bin/env python3
"""
msxFI Demo Tutorial
===================
A guided walkthrough of core msxFI capabilities.

Run:
    python demo_tutorial.py
    python demo_tutorial.py --help
    python demo_tutorial.py --quick

This script demonstrates:
1. Matrix Fault Injection (NVM: RRAM MLC)
2. Matrix Fault Injection (DRAM: eDRAM 333T)
3. DNN Accuracy Degradation (LeNet + MNIST)
4. DRAM Parameter Sweep (target fault rate driven)
5. eDRAM Trace Analysis (WWL Swing - refresh table + cell fault rate from trace)
"""

import subprocess
import sys
import os
import argparse
import shutil
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACE_ANALYSIS_DIR = os.path.join(SCRIPT_DIR, 'trace_analysis')


def print_header(title: str, char: str = '='):
    """Print a formatted section header."""
    width = 70
    print()
    print(char * width)
    print(f" {title}")
    print(char * width)
    print()


def print_subheader(title: str):
    """Print a subsection header."""
    print(f"\n--- {title} ---\n")


def check_dependencies(include_torchvision: bool = False) -> bool:
    """Check if required dependencies are installed."""
    print_header("Environment Check")
    
    required = ['numpy', 'scipy', 'torch', 'pandas']
    if include_torchvision:
        required.append('torchvision')
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"  [OK] {pkg}")
        except ImportError:
            print(f"  [MISSING] {pkg}")
            missing.append(pkg)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("\nAll dependencies satisfied.")
    return True


def run_command(cmd: list, cwd: str = None, show_output: bool = True,
                on_captured_output=None) -> int:
    """Run a command and optionally display output."""
    # Display command with simplified python path
    display_cmd = [('python' if c == sys.executable else c) for c in cmd]
    if cwd:
        print(f"$ cd {os.path.relpath(cwd, SCRIPT_DIR)}")
    print(f"$ {' '.join(display_cmd)}")
    print()
    sys.stdout.flush()

    # Set up environment with MKL fix for Linux clusters
    env = os.environ.copy()
    env['MKL_THREADING_LAYER'] = 'GNU'

    result = subprocess.run(
        cmd,
        cwd=cwd or SCRIPT_DIR,
        capture_output=not show_output,
        text=True,
        env=env
    )

    if not show_output and on_captured_output is not None and result.stdout:
        on_captured_output(result.stdout)

    if not show_output and result.returncode != 0:
        print(f"Error: {result.stderr}")
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")

    print()
    return result.returncode


def run_step(title: str, cmd: list, cwd: str = None, required: bool = True) -> bool:
    """Run one demo step and print a concise status line."""
    rc = run_command(cmd, cwd=cwd)
    if rc == 0:
        return True
    print(f"[FAILED] {title}")
    if required:
        print("Skipping remaining actions in this demo.")
    return False


def run_step_compact(title: str, cmd: list, cwd: str = None, required: bool = True,
                     output_handler=None) -> bool:
    """Run one step with captured output and custom presentation."""
    rc = run_command(cmd, cwd=cwd, show_output=False, on_captured_output=output_handler)
    if rc == 0:
        return True
    print(f"[FAILED] {title}")
    if required:
        print("Skipping remaining actions in this demo.")
    return False


def print_compact_dnn_injection_log(stdout_text: str):
    key_patterns = [
        "Set memory model to:",
        "Using user-provided seed:",
        "Running DRAM333T DNN Fault Injection",
        "Injecting DRAM333T faults into DNN model",
        "Loading model class from",
        "Loading DNN model from",
        "Loaded DNN model from",
        "Using DRAM model",
        "DRAM Params:",
        "DRAM333T DNN fault injection complete.",
        "Faulty DRAM333T DNN model saved to",
    ]

    generated_faults = []
    affected_pairs = []

    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(p in line for p in key_patterns):
            print(line)
            continue

        m_gen = re.match(r"Number of generated faults:\s*(\d+)", line)
        if m_gen:
            generated_faults.append(int(m_gen.group(1)))
            continue

        m_aff = re.match(r"Number of affected data values:\s*(\d+)\s*\(out of\s*(\d+)\)", line)
        if m_aff:
            affected_pairs.append((int(m_aff.group(1)), int(m_aff.group(2))))

    if generated_faults:
        total_generated = sum(generated_faults)
        tensors_with_faults = sum(1 for n in generated_faults if n > 0)
        print("Fault injection tensor summary:")
        print(f"  Tensors processed: {len(generated_faults)}")
        print(f"  Tensors with faults: {tensors_with_faults}")
        print(f"  Total generated faults: {total_generated}")

    if affected_pairs:
        total_affected = sum(a for a, _ in affected_pairs)
        total_values = sum(v for _, v in affected_pairs)
        print(f"  Total affected data values: {total_affected} (out of {total_values})")


def demo_nvm_matrix_fi():
    """Demonstrate NVM (RRAM MLC) matrix fault injection."""
    print_header("Demo 1: NVM Matrix Fault Injection (RRAM MLC)")
    
    print("""
This demo injects faults into a random matrix using an RRAM MLC model.
The fault model is based on physical device characteristics.

Key parameters:
  --mode rram_mlc    : Use RRAM multi-level cell model
  --q_type afloat    : AdaptivFloat quantization
  --int_bits 2       : 2 integer bits
  --frac_bits 4      : 4 fractional bits (total 6 bits)
  --rep_conf 8 8     : 2 cells, 3 bits each (log2(8)=3, matches 6-bit data)
  --seed 42          : Fixed seed for reproducibility
  --matrix_size 100  : 100x100 test matrix
""")
    
    run_step("Demo 1 main run", [
        sys.executable, 'run_msxfi.py',
        '--mode', 'rram_mlc',
        '--q_type', 'afloat',
        '--int_bits', '2',
        '--frac_bits', '4',
        '--rep_conf', '8', '8',
        '--seed', '42',
        '--matrix_size', '100'
    ])


def demo_dram_matrix_fi():
    """Demonstrate DRAM matrix fault injection."""
    print_header("Demo 2: DRAM Matrix Fault Injection (eDRAM 333T)")
    
    print("""
This demo injects faults into a matrix using a 333T-eDRAM model.
Fault probability depends on refresh time and voltage parameters.

Key parameters:
  --mode dram333t    : Use 333T eDRAM model
  --refresh_t 501    : 501 microsecond refresh time
  --vth_sigma 50     : 50mV threshold voltage variation
  --q_type signed    : Signed fixed-point quantization
  --int_bits 3       : 3 integer bits
  --frac_bits 5      : 5 fractional bits
  --seed 7           : Different seed from Demo 1 for clearer comparison
""")
    
    run_step("Demo 2 main run", [
        sys.executable, 'run_msxfi.py',
        '--mode', 'dram333t',
        '--refresh_t', '501',
        '--vth_sigma', '50',
        '--q_type', 'signed',
        '--int_bits', '3',
        '--frac_bits', '5',
        '--seed', '7',
        '--matrix_size', '100'
    ])


def demo_dnn_accuracy_degradation():
    """Demonstrate DNN accuracy degradation from fault injection."""
    print_header("Demo 3: DNN Accuracy Degradation (LeNet + MNIST)")

    print("""
This demo shows how memory faults affect neural network accuracy.
We inject faults into LeNet weights and measure accuracy on MNIST.

Workflow:
1. Check for pre-trained model (train if missing)
2. Inject DRAM retention faults into model weights
3. Evaluate accuracy before and after fault injection

Key parameters:
  --mode dram333t     : Use 333T eDRAM model
  --eval_dnn          : Enable DNN evaluation mode
  --refresh_t 1000      : 1000us refresh time
  --q_type int        : INT8 quantization
""")

    example_nn_dir = os.path.join(SCRIPT_DIR, 'example_nn', 'lenet')
    model_path = os.path.join(example_nn_dir, 'checkpoints', 'lenet.pth')
    data_dir = os.path.join(example_nn_dir, 'data')
    train_script = os.path.join(example_nn_dir, 'train.py')

    # Check if model exists, if not, train it
    if not os.path.exists(model_path):
        print_subheader("Pre-trained model not found - Training LeNet")
        print(f"Model path: {model_path}")
        print("This will download MNIST (~10MB) and train for 5 epochs.")
        print()

        if not os.path.exists(train_script):
            print(f"Training script not found: {train_script}")
            print("Skipping this demo.")
            return

        # Run training script
        if not run_step("Train LeNet", [sys.executable, 'train.py'], cwd=example_nn_dir):
            return

        # Verify model was created
        if not os.path.exists(model_path):
            print("Training failed - model not created.")
            print("Skipping this demo.")
            return

        print()
    elif not os.path.exists(data_dir):
        # Model exists but data missing - download data
        print_subheader("Dataset not found - Downloading MNIST")
        download_script = """
import torchvision
import torchvision.transforms as transforms
transform = transforms.Compose([transforms.ToTensor()])
torchvision.datasets.MNIST(root='data', train=False, download=True, transform=transform)
print('MNIST dataset downloaded.')
"""
        download_path = os.path.join(example_nn_dir, '_download_data.py')
        with open(download_path, 'w') as f:
            f.write(download_script)
        run_step("Download MNIST", [sys.executable, '_download_data.py'], cwd=example_nn_dir, required=False)
        if os.path.exists(download_path):
            os.remove(download_path)

    # Run fault injection on DNN (paths relative to SCRIPT_DIR)
    print_subheader("Injecting DRAM Faults into Model Weights")
    if not run_step_compact("Inject faults into LeNet", [
        sys.executable, 'run_msxfi.py',
        '--mode', 'dram333t',
        '--eval_dnn',
        '--model', 'example_nn/lenet/checkpoints/lenet.pth',
        '--model_def', 'example_nn/lenet/model.py',
        '--model_class', 'LeNet',
        '--seed', '0',
        '--q_type', 'int',
        '--int_bits', '8',
        '--frac_bits', '0',
        '--refresh_t', '1000',
        '--vth_sigma', '50'
    ], output_handler=print_compact_dnn_injection_log):
        return

    # Evaluate both models
    print_subheader("Evaluating Original vs Faulty Model")

    eval_script = """
import sys
import platform
import torch
import torchvision
import torchvision.transforms as transforms

# Add model directory to path
sys.path.insert(0, 'example_nn/lenet')
from model import LeNet

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device: {device}')

# Platform-specific num_workers (macOS spawn issue)
num_workers = 2 if platform.system() == 'Linux' else 0

# Load MNIST test set
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,)),
])
testset = torchvision.datasets.MNIST(
    root='example_nn/lenet/data', train=False, download=False, transform=transform)
testloader = torch.utils.data.DataLoader(testset, batch_size=1000, shuffle=False, num_workers=num_workers)

def evaluate(model):
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in testloader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    return 100 * correct / total

# Evaluate original model
print('\\nLoading original model...')
original = torch.load('example_nn/lenet/checkpoints/lenet.pth', map_location=device, weights_only=False).to(device)
orig_acc = evaluate(original)
print(f'Original model accuracy: {orig_acc:.2f}%')

# Evaluate faulty model
print('\\nLoading faulty model...')
faulty_path = 'example_nn/lenet/checkpoints/lenet_dram333t_s0_qint_i8_f0_rt1000.0.pth'
faulty = torch.load(faulty_path, map_location=device, weights_only=False).to(device)
faulty_acc = evaluate(faulty)
print(f'Faulty model accuracy: {faulty_acc:.2f}%')

print(f'\\nAccuracy degradation: {orig_acc - faulty_acc:.2f}%')
"""
    # Write and run eval script from SCRIPT_DIR
    eval_script_path = os.path.join(SCRIPT_DIR, '_demo_eval_tmp.py')
    with open(eval_script_path, 'w') as f:
        f.write(eval_script)

    run_step("Evaluate original and faulty model", [sys.executable, '_demo_eval_tmp.py'], required=False)

    # Cleanup
    if os.path.exists(eval_script_path):
        os.remove(eval_script_path)


def demo_dram_parameter_sweep():
    """Demonstrate DRAM parameter sweep for target fault rate."""
    print_header("Demo 4: DRAM Parameter Sweep")
    
    print("""
This demo finds DRAM operating parameters (WWL_Swing, refresh time) that achieve
a target fault rate. Useful for design space exploration.

Key parameters:
  --mode dram333t    : Use 333T eDRAM model
  --target_fr 0.01   : Target 0.01% fault rate
""")
    
    run_step("Demo 4 parameter sweep", [
        sys.executable, 'run_msxfi.py',
        '--mode', 'dram333t',
        '--target_fr', '0.01'
    ])


def demo_trace_analysis():
    """Demonstrate eDRAM trace analysis: WWL_Swing-refresh table + cell fault rate."""
    print_header("Demo 5: eDRAM Trace Analysis")

    print("""
This demo answers two questions:

  Step 1: WWL_Swing --> Required Refresh Interval  (physics model)
          At a given WWL_Swing, what refresh interval is needed to meet
          a target cell fault rate?

  Step 2: Cell Fault Rate from Address Trace
          Given a refresh interval, how many cells in the trace
          are expected to fault?

Fault model:
  Per-bit retention follows a DRAM-physics log-normal distribution.
  Between writes, explicit refreshes cap the longest unrefreshed gap
  to the refresh period. The expected faulty bit-cell count per row
  is the retention CDF evaluated at the worst-case gap.
  retention: the retention reference that anchors the distribution.
    Larger retention means lower fault risk.
  refresh_interval: explicit refresh period.
    Shorter interval means lower fault risk.
  Metric: cell_fault_rate = expected faulty cells / tracked cells.
""")

    trace_file = os.path.join(TRACE_ANALYSIS_DIR, 'traces', 'dnn_trace.csv')

    # =========================================================================
    # Step 1: WWL_Swing-Refresh Physics Table
    # =========================================================================
    print_subheader("Step 1: WWL_Swing --> Required Refresh Interval (Physics Model)")

    print("""
Build the mapping: WWL_Swing (wordline voltage swing) --> Required refresh interval

Physics basis:
  DRAM cells lose charge through access transistor leakage (Ioff).
  Matched Ion with higher WWL_Swing (e.g., from increased gate underdrive) reduces Ioff exponentially,
  which means slower charge loss and longer data retention.

Output:
  The FR columns show the required refresh interval to keep the cell
  fault rate at or below each target.
  Use these values as --refresh-interval in Step 2.
""")

    run_step("Step 1 physics table", [
        sys.executable, 'find_refresh_times.py',
        '--wwl_swing-step', '0.1'
    ], cwd=TRACE_ANALYSIS_DIR, required=False)

    # =========================================================================
    # Step 2: Trace-Based Cell Fault Rate
    # =========================================================================
    print_subheader("Step 2: Cell Fault Rate from Address Trace")

    print("""
Run trace simulation to measure cell fault rate under different conditions.

Step 1 and Step 2 are complementary:
  Step 1 provides the WWL_Swing to refresh-interval table.
  Step 2 applies the interval rule on a concrete address trace.

We apply the interval fault rule and show three scenarios:

  A) WWL_Swing=1.40V, refresh=500us (small fault rate)
  B) WWL_Swing=1.40V, refresh=800us (longer period, faults increase)
  C) WWL_Swing=1.42V, refresh=800us (same refresh, increase WWL_Swing to reduce leakage and faults)

Metric: cell_fault_rate = faulty cells / tracked cells

Fault statistics in Step 2:
  tracked_cells: bit-cells in rows reached by writes.
  faulty_cells: expected faulty bit-cells.
  fault_events: expected fault occurrences across intervals, same bit-cell can contribute multiple times.
""")

    if os.path.exists(trace_file):
        print_subheader("Scenario A: WWL_Swing=1.40V, refresh=500us")
        run_step("Step 2 Scenario A", [
            sys.executable, 'address_mapping.py',
            '--trace', 'traces/dnn_trace.csv',
            '--mem-model', 'dram333t',
            '--refresh-interval', '500'
        ], cwd=TRACE_ANALYSIS_DIR, required=False)

        print_subheader("Scenario B: WWL_Swing=1.40V, refresh=800us")
        run_step("Step 2 Scenario B", [
            sys.executable, 'address_mapping.py',
            '--trace', 'traces/dnn_trace.csv',
            '--mem-model', 'dram333t',
            '--refresh-interval', '800'
        ], cwd=TRACE_ANALYSIS_DIR, required=False)

        print_subheader("Scenario C: WWL_Swing=1.42V, refresh=800us")
        run_step("Step 2 Scenario C", [
            sys.executable, 'address_mapping.py',
            '--trace', 'traces/dnn_trace.csv',
            '--mem-model', 'dram333t',
            '--refresh-interval', '800',
            '--wwl_swing', '1.42'
        ], cwd=TRACE_ANALYSIS_DIR, required=False)
    else:
        print(f"Trace file not found: {trace_file}")
        print("Skipping Step 2.")


def print_summary():
    """Print a summary of what was demonstrated."""
    print_header("Tutorial Complete", char='*')

    print("""
You have seen the main capabilities of msxFI:

1. NVM Fault Injection
   - Inject faults using RRAM, FeFET, and other NVM models
   - Configure MLC levels via --rep_conf

2. DRAM Fault Injection
   - Inject faults based on refresh time and voltage
   - Uses 333T eDRAM model optimized for retention

3. DNN Accuracy Degradation
   - Inject faults into neural network weights
   - Measure accuracy impact on real models (LeNet + MNIST)

4. Parameter Sweep
   - Find operating points for target fault rates
   - Useful for design space exploration

5. eDRAM Trace Analysis
   - Step 1: WWL_Swing-refresh interval physics table
   - Step 2: Cell fault rate from address trace

For more details, see:
  - README.md for full documentation
  - example_nn/ for DNN fault injection examples
  - trace_analysis/ for trace-based analysis tools

To run individual demos:
  python demo_tutorial.py --demo 1    # NVM matrix FI (RRAM MLC)
  python demo_tutorial.py --demo 2    # DRAM matrix FI (333T eDRAM)
  python demo_tutorial.py --demo 3    # DNN accuracy degradation
  python demo_tutorial.py --demo 4    # DRAM parameter sweep
  python demo_tutorial.py --demo 5    # eDRAM trace analysis (WWL_Swing-refresh table + cell fault rate)
""")


def main():
    parser = argparse.ArgumentParser(
        description='msxFI Demo Tutorial',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_tutorial.py              # Run all demos
  python demo_tutorial.py --quick      # Quick demo (core features only)
  python demo_tutorial.py --demo 1     # Run specific demo
  python demo_tutorial.py --demo 5     # Run eDRAM trace analysis
  python demo_tutorial.py --list       # List available demos
"""
    )
    parser.add_argument('--quick', action='store_true',
                        help='Run quick demo (demos 1, 2, 5)')
    parser.add_argument('--demo', nargs='+', type=int,
                        help='Run specific demo(s) by number')
    parser.add_argument('--list', action='store_true',
                        help='List available demos')
    parser.add_argument('--skip-check', action='store_true',
                        help='Skip dependency check')
    
    args = parser.parse_args()
    
    demos = {
        1: ('NVM Matrix Fault Injection (RRAM MLC)', demo_nvm_matrix_fi),
        2: ('DRAM Matrix Fault Injection (eDRAM 333T)', demo_dram_matrix_fi),
        3: ('DNN Accuracy Degradation (LeNet + MNIST)', demo_dnn_accuracy_degradation),
        4: ('DRAM Parameter Sweep', demo_dram_parameter_sweep),
        5: ('eDRAM Trace Analysis', demo_trace_analysis),
    }
    
    if args.list:
        print("\nAvailable demos:")
        for num, (name, _) in demos.items():
            print(f"  {num}. {name}")
        print("\nRun with: python demo_tutorial.py --demo <number(s)>")
        return
    
    if args.demo:
        invalid = [num for num in args.demo if num not in demos]
        if invalid:
            print(f"\nUnknown demo number(s): {invalid}")
            print("Use --list to see valid demo numbers.")
            return
        selected = args.demo
    elif args.quick:
        selected = [1, 2, 5]
    else:
        selected = list(demos.keys())

    print_header("msxFI Demo Tutorial", char='*')
    print(__doc__)

    if not args.skip_check:
        include_torchvision = 3 in selected
        if not check_dependencies(include_torchvision=include_torchvision):
            print("\nPlease install missing dependencies and try again.")
            return
    
    for num in selected:
        _, func = demos[num]
        try:
            func()
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user.")
            break
        except Exception as e:
            print(f"\nError in demo {num}: {e}")
            continue
    
    print_summary()


if __name__ == '__main__':
    main()
