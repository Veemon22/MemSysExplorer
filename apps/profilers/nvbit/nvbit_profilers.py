import re
import os
import sys
import argparse
import subprocess
import pandas as pd
from profilers.FrontendInterface import FrontendInterface
from profilers.nvbit.nvbit_PatternConfig import NVBitConfig

class NVBitProfilers(FrontendInterface):
    def __init__(self, **kwargs):
        """
        Initialize the NVBitProfiler with provided configuration.

        Parameters
        ----------
        executable : list
            Executable command (with arguments) to profile.
        """
        super().__init__(**kwargs)
        self.executable_cmd = " ".join(self.config.get("executable", []))
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.lib_path = os.path.join(self.script_dir, "lib", "nvbit.so")
        self.metrics = None

    def validate_paths(self):
        """
        Ensure the paths for the NVBit shared object and the executable are valid.
        """
        if not os.path.isfile(self.lib_path):
            raise FileNotFoundError(f"NVBit shared object not found at {self.lib_path}")

        if not self.executable_cmd.strip():
            raise ValueError("No executable specified. Use --executable <path>")

        executable = self.executable_cmd.split()[0]
        if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
            raise FileNotFoundError(f"'{executable}' is not valid or not executable.")
    
    def set_ld_preload(self):
        """
        Set LD_PRELOAD to inject the NVBit instrumentation layer at runtime.
        """
        os.environ["LD_PRELOAD"] = self.lib_path
        print(f"LD_PRELOAD set to: {self.lib_path}")

    def construct_command(self):
        """
        Construct the full executable command as a list for subprocess.

        Returns
        -------
        list
            Command split for subprocess execution.
        """
        return self.executable_cmd.split()

    def profiling(self, **kwargs):
        """
        Run the GPU executable with NVBit instrumentation injected via LD_PRELOAD.

        This assumes that `lib/nvbit.so` is already built and compatible with the
        target application binary.
        """
        self.validate_paths()
        self.set_ld_preload()
        command = self.construct_command()
        try:
            print(f"Executing: {' '.join(command)}")
            subprocess.run(command, check=True, text=True, env=os.environ)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            raise
        except FileNotFoundError:
            print("Error: executable not found.")
            raise
    def extract_metrics(self, report_file="global_summary.txt", **kwargs):
        """
        Parse the NVBit profiler output report and extract memory access statistics.

        Parameters
        ----------
        report_file : str
            Path to the NVBit output file (default: "global_summary.txt").

        Returns
        -------
        dict
            Parsed metrics including read/write counts, frequencies, and working set size.
        """
        try:
            report_data = {}
            with open(report_file, "r") as f:
                for line in f:
                    if match := re.match(r"Global Load Count:\s+(\d+)", line):
                        report_data["total_reads"] = int(match.group(1))
                    elif match := re.match(r"Global Store Count:\s+(\d+)", line):
                        report_data["total_writes"] = int(match.group(1))
                    elif match := re.match(r"Execution Time \(sec\):\s+([\d\.]+)", line):
                        report_data["execution_time"] = float(match.group(1))
                    elif match := re.match(r"Working Set Size \(bytes\):\s+(\d+)", line):
                        report_data["workingset_size"] = int(match.group(1))
                    elif match := re.match(r"Access Word Size .*:\s+(\d+)", line):
                        report_data["read_size"] = int(match.group(1))
                        report_data["write_size"] = int(match.group(1))

            # Set read/write freq to null
            report_data["read_freq"] = None
            report_data["write_freq"] = None

            self.metrics = NVBitConfig.populating(report_data)
            print("NVBit metrics successfully loaded.")
            return report_data
        except Exception as e:
            print(f"Failed to extract NVBit metrics: {e}")
            raise

    @classmethod
    def required_profiling_args(cls):
        """
        Return the list of required arguments to run profiling.

        Returns
        -------
        list
            Required keys (["executable"]).
        """
        return ["executable"]

    @classmethod
    def required_extract_args(cls, action):
        """
        Return the required arguments for the extract_metrics method.

        Parameters
        ----------
        action : str
            Either 'extract_metrics' or 'both'.

        Returns
        -------
        list
            Required arguments (e.g., ["report_file"]).
        """        
        if action == "extract_metrics":
            return ["report_file"]
        else:
            return []    
