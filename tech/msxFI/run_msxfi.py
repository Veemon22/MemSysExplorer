import sys
import os

# Add the parent directory of this script's location to the system path
# to allow for absolute imports of 'msxFI' components.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import argparse
import torch
import random

_USE_COLOR = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
RED = '\033[91m' if _USE_COLOR else ''
BOLD = '\033[1m' if _USE_COLOR else ''
RESET = '\033[0m' if _USE_COLOR else ''
FAULT_MARKER = '' if _USE_COLOR else ' (*)'


def print_matrix_sample(matrix, rows, cols, fault_mask=None):
    """Print a matrix sample, highlighting faulty cells in red (or with * marker)."""
    sub = matrix[:rows, :cols]
    if fault_mask is None or not np.any(fault_mask[:rows, :cols]):
        print(sub)
        return

    mask = fault_mask[:rows, :cols]
    col_widths = []
    for c in range(cols):
        w = max(len(f"{sub[r, c]: .8g}") for r in range(rows))
        col_widths.append(max(w, 10))

    for r in range(rows):
        cells = []
        for c in range(cols):
            val_str = f"{sub[r, c]: .8g}".rjust(col_widths[c])
            if mask[r, c]:
                cells.append(f"{RED}{BOLD}{val_str}{RESET}{FAULT_MARKER}")
            else:
                pad = ' ' * len(FAULT_MARKER)
                cells.append(f"{val_str}{pad}")
        prefix = "[[" if r == 0 else " ["
        suffix = "]]" if r == rows - 1 else "]"
        print(f"{prefix}{' '.join(cells)}{suffix}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run NVM/DRAM fault injection experiments.")
    parser.add_argument('--mode', type=str, default='rram_mlc', 
                        help="Memory model to use (rram_mlc, dram3t, dram1t, etc.). See fi_config.py for available models.")
    # DRAM specific
    parser.add_argument('--refresh_t', type=float,
                        help="DRAM refresh time in microseconds (used for DRAM modes).")
    parser.add_argument('--vth_sigma', type=float, default=50,
                        help="Standard deviation of threshold voltage (Vth) in mV for DRAM fault rate calculation (default: 50mV).")
    parser.add_argument('--vdd', type=float,
                        help="Custom vdd in volts for DRAM modes. If not provided, uses default vdd from pickle file.")
    parser.add_argument('--wwl_swing', type=float,
                        help="Custom WWL Swing in volts for DRAM modes. If not provided, uses default wwl_swing from pickle file.")
    parser.add_argument('--target_fr', type=float,
                        help="Target fault rate (in percentage, e.g., 0.1 for 0.1%%). Enables sweep mode for refresh_t, wwl_swing, and vdd.")
    # MLC specific
    parser.add_argument('--rep_conf', nargs='*', default=[8, 8],
                        help="Array of number of levels per cell used for storage per data value, e.g.: --rep_conf 8 8")

    # Quantization and fault injection
    parser.add_argument('--int_bits', type=int, default=None, 
                        help="Number of integer bits for data quantization (for fixed-point types like 'signed', 'afloat').")
    parser.add_argument('--frac_bits', type=int, default=None, 
                        help="Number of fractional bits for data quantization (for fixed-point types like 'signed', 'afloat').")
    parser.add_argument('--q_type', type=str, default='afloat', 
                        help="Quantization type (e.g., 'signed', 'afloat').")
    parser.add_argument('--seed', type=int, default=None, 
                        help="Random seed for fault injection. If not provided, a random seed will be used.")
    parser.add_argument('--matrix_size', type=int, default=1000, 
                        help="Size N for the NxN test matrix (for matrix FI modes).")

    # DNN evaluation
    parser.add_argument('--eval_dnn', action='store_true', default=False,
                        help="Enable DNN fault injection for the selected mode.")
    parser.add_argument('--model', type=str, default=None,
                        help="Path to the pre-trained DNN model (.pth file) for all DNN modes.")
    parser.add_argument('--model_def', type=str, default=None,
                        help="Path to the Python file containing the model class definition (required for DNN modes).")
    parser.add_argument('--model_class', type=str, default=None,
                        help="Name of the model class or constructor function in the model definition file.")
    parser.add_argument('--num_classes', type=int, default=10,
                        help="Number of output classes for model constructor (default: 10).")

    return parser.parse_args()

def parse_rep_conf(rep_conf_input):
    """Parse rep conf from space-separated integers."""
    if isinstance(rep_conf_input, list):
        if len(rep_conf_input) == 0:
            return [8, 8]
        if all(isinstance(x, int) for x in rep_conf_input):
            return rep_conf_input
        try:
            return [int(x) for x in rep_conf_input]
        except ValueError as e:
            raise ValueError(f"All rep_conf values must be integers. Error: {e}")
    else:
        raise ValueError(f"Unsupported rep_conf input type: {type(rep_conf_input)}")

def generate_output_filename(model_path, mem_model, args):
    """Generate output filename for faulty model."""
    original_filename = os.path.basename(model_path)
    base_name, ext = os.path.splitext(original_filename)

    float_types = ['float16', 'bfloat16', 'float32', 'float64']
    filename_parts = [base_name, mem_model, f"s{args.seed}", f"q{args.q_type}"]
    if args.q_type not in float_types:
        filename_parts.append(f"i{args.int_bits}")
        filename_parts.append(f"f{args.frac_bits}")

    if 'dram' in mem_model:
        filename_parts.append(f"rt{args.refresh_t}")
        if args.vdd is not None:
            filename_parts.append(f"vdd{args.vdd}")
        if args.wwl_swing is not None:
            filename_parts.append(f"wwl_swing{args.wwl_swing}")

    filename = "_".join(filename_parts) + ext

    return os.path.join(os.path.dirname(model_path), filename)

def main():
    args = parse_args()

    try:
        rep_conf_list = parse_rep_conf(args.rep_conf)
    except ValueError as e:
        print(f"Error: {e}")
        return

    import msxFI.fi_config as fi_config
    from msxFI.fi_utils import validate_config, sweep_dram_params, filter_top_configs_per_wwl_swing, get_q_type_bit_width
    from msxFI.data_transforms import convert_mlc_mat, convert_f_mat, get_afloat_bias

    if args.mode not in fi_config.mem_dict:
        print(f"Error: Unknown memory model '{args.mode}'")
        print(f"Available models: {list(fi_config.mem_dict.keys())}")
        return

    # Handle target_fr sweep mode
    if args.target_fr is not None:
        if 'dram' not in args.mode:
            print("Error: --target_fr is only supported for DRAM modes (dram3t, dram1t, dram333t)")
            return

        print(f"Running parameter sweep mode for target fault rate: {args.target_fr}%")
        results = sweep_dram_params(args.mode, args.target_fr, args.vth_sigma)

        if results:
            filtered = filter_top_configs_per_wwl_swing(results, args.target_fr, top_n=3)

            print(f"\nTop configurations (showing up to 3 closest matches per WWL Swing):")
            print(f"Total configurations found: {len(results)}, displaying: {len(filtered)}")
            print(f"\n{'WWL Swing (V)':<10}{'Refresh (us)':<15}{'Fault Rate (%)':<18}{'Error (%)':<12}")
            print("-" * 65)

            current_wwl_swing = None
            for rt, _, wwl_swing, fr in filtered:
                error = abs(fr - args.target_fr)
                if wwl_swing != current_wwl_swing:
                    if current_wwl_swing is not None:
                        print()
                    current_wwl_swing = wwl_swing

                print(f"{wwl_swing:<10.2f}{rt:<15.1f}{fr:<18.6f}{error:<12.6f}")
        else:
            print("\nNo configurations found matching the target fault rate.")
            print("Try adjusting the target fault rate or expanding the sweep ranges.")

        return

    if not validate_config(args, rep_conf_list):
        return

    fi_config.mem_model = args.mode
    print(f"Set memory model to: {fi_config.mem_model}")
    from msxFI import fault_injection

    if args.seed is None:
        args.seed = random.randint(0, 2**10)
        print(f"No seed provided, using randomly generated seed: {args.seed}")
    else:
        print(f"Using user-provided seed: {args.seed}")

    test_size = (args.matrix_size, args.matrix_size)

    base_params = {
        'seed': args.seed,
        'int_bits': args.int_bits,
        'frac_bits': args.frac_bits,
        'q_type': args.q_type
    }
    
    if 'dram' in args.mode:
        if args.refresh_t is None:
            raise ValueError("refresh_t is required for DRAM models")
        base_params['refresh_t'] = args.refresh_t * 1e-6
        base_params['vth_sigma'] = args.vth_sigma / 1000.0  # convert mV to V
        param_parts = [f"refresh_t={args.refresh_t}us", f"vth_sigma={args.vth_sigma}mV"]
        if args.vdd is not None:
            base_params['custom_vdd'] = args.vdd
            param_parts.append(f"vdd={args.vdd}V")
        if args.wwl_swing is not None:
            base_params['custom_wwl_swing'] = args.wwl_swing
            param_parts.append(f"wwl_swing={args.wwl_swing}V")
        param_info = ", ".join(param_parts)
    else:
        base_params['rep_conf'] = np.array(rep_conf_list)
        base_params['encode'] = 'dense'
        param_info = f"rep_conf={rep_conf_list}"

    if args.eval_dnn:
        print(f"Running {args.mode.upper()} DNN Fault Injection\n\n")

        if not all([args.model, args.model_def, args.model_class]):
            print("Error: For DNN fault injection, --model, --model_def, and --model_class must all be specified.")
            return
        
        base_params.update({
            'model_def_path': args.model_def,
            'model_path': args.model,
            'model_class_name': args.model_class,
            'num_classes': args.num_classes
        })
        print(f"Injecting {args.mode.upper()} faults into DNN model with seed {args.seed}, {param_info}...")
        
        try:
            faulty_model = fault_injection.dnn_fi(**base_params)
            print(f"{args.mode.upper()} DNN fault injection complete.")
        except Exception as e:
            print(f"Error during {args.mode.upper()} DNN fault injection: {e}")
            return

        save_path = generate_output_filename(args.model, args.mode, args)
        torch.save(faulty_model, save_path)
        print(f"Faulty {args.mode.upper()} DNN model saved to {save_path}")

    else:
        print(f"\nTest for {args.mode.upper()} single matrix fault generation\n")
        np.random.seed(args.seed)
        test_matrix = np.random.uniform(-1, 1, size=test_size)
        sample_rows = min(5, test_matrix.shape[0])
        sample_cols = min(5, test_matrix.shape[1])

        # Step 1: Original (unquantized) matrix
        print(f"Step 1 - Original matrix (sample):")
        print(test_matrix[:sample_rows, :sample_cols])

        # Step 2: Quantized matrix (before fault injection)
        flattened = torch.from_numpy(test_matrix.copy()).view(-1)
        if fi_config.pt_device == "cuda":
            flattened = flattened.to(torch.device(fi_config.pt_device))
        exp_bias = 0
        if args.q_type == 'afloat':
            exp_bias = get_afloat_bias(abs(flattened), args.frac_bits)
        if 'dram' in args.mode:
            bit_width = get_q_type_bit_width(args.q_type, args.int_bits, args.frac_bits)
            q_rep_conf = np.array([2] * bit_width)
        else:
            q_rep_conf = np.array(rep_conf_list)
        mlc_values, mask = convert_mlc_mat(flattened, q_rep_conf, args.int_bits, args.frac_bits, exp_bias, args.q_type)
        quantized_flat = convert_f_mat(mlc_values, q_rep_conf, args.int_bits, args.frac_bits, exp_bias, args.q_type, mask)
        quantized_matrix = np.reshape(quantized_flat.cpu().data.numpy(), test_matrix.shape)
        print(f"\nStep 2 - Quantized matrix ({args.q_type}, int={args.int_bits}, frac={args.frac_bits}):")
        print(quantized_matrix[:sample_rows, :sample_cols])

        # Step 3: Fault injection + summary
        faulty_matrix = fault_injection.mat_fi(test_matrix.copy(), **base_params)
        diff_matrix = faulty_matrix - quantized_matrix
        fault_rows, fault_cols = np.nonzero(diff_matrix)
        num_faults = len(fault_rows)
        marker = ' (*)' if not _USE_COLOR else ''
        print(f"\nStep 3 - Fault summary: {RED}{BOLD}{num_faults}{RESET} affected cells out of {test_matrix.size}")
        if num_faults > 0:
            print(f"\n  {'[row,col]':<12} {'Quantized':>12} {'Faulty':>12} {'Diff':>12}")
            print(f"  {'-' * 52}")
            max_show = 30
            for i in range(min(num_faults, max_show)):
                r, c = fault_rows[i], fault_cols[i]
                q_val = quantized_matrix[r, c]
                f_val = faulty_matrix[r, c]
                d_val = diff_matrix[r, c]
                print(f"  [{r:>3d},{c:>3d}]     {q_val:>12.6f} {RED}{f_val:>12.6f}{RESET}{marker} {d_val:>+12.6f}")
            if num_faults > max_show:
                print(f"  ... and {num_faults - max_show} more")

if __name__=="__main__":
    main()
