from profilers.FrontendInterface import FrontendInterface
import subprocess
import re
import os

class DrioProfilers(FrontendInterface):
    def __init__(self, **kwargs):
        """
        Initialize the profiler with user-specified configuration.

        Parameters
        ----------
        **kwargs : dict
            Dictionary that may contain:
            
            - executable : list
              A list including the executable and its arguments.
            - action : str
              One of "profiling", "extract_metrics", or "both".
            - config_file : str, optional
              Path to memcount configuration file.

        """
        
        super().__init__(**kwargs)
        self.executable_cmd = " ".join(self.config.get("executable", []))
        self.action = self.config.get("action")
        self.config_file = self.config.get("config")

        #Get the directory of this script 
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.client = os.path.join(base_dir, "build", "libmemcount.so")

        # Locate DynamoRIO installation dynamically
        dynamorio_install = os.path.join(base_dir, "dynamorio_install")
        dynamorio_dirs = [d for d in os.listdir(dynamorio_install) if d.startswith("DynamoRIO-")]

        if not dynamorio_dirs:
            raise FileNotFoundError("No DynamoRIO installation found in dynamorio_install/")

        self.dynamorio_home = os.path.join(dynamorio_install, dynamorio_dirs[0])
        self.run = os.path.join(self.dynamorio_home, "build", "bin64", "drrun")

        #Original Line
        #self.run = f"{os.path.expandvars('$DYNAMORIO_HOME')}/bin64/drrun" 
        #self.client = f"{os.path.expandvars('$APPS_HOME')}/profilers/dynamorio/build/libmemcount.so"
        
        self.output = ""
        self.report = None
        self.data = {}

    # validate if client has correct path 
    def validate_paths(self):
        """
        (Disabled) Validate the path of the executable, client, and drrun binary.

        This method is currently unused but can be enabled for strict validation.
        """

        # FIXME: rewrite this code
        # if not self.executable_cmd:
        #     raise ValueError("Executable path is required.")
        # executable = self.executable_cmd.split()[1]
        # if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
        #     raise FileNotFoundError(f"'{self.executable_cmd}' is not valid or not executable.")
        
        # # check environmental variables
        # if not os.path.isfile(self.client):
        #     raise FileNotFoundError(f"{self.client} is not valid. Check $APPS_HOME environmental variable.")
        # if not os.path.isfile(self.run):
        #     raise FileNotFoundError(f"{self.run} is not valid. Check $DYNAMORIO_HOME environmental variable.")
        pass
    
    def constuct_command(self):
        """
        Construct the full DynamoRIO instrumentation command.

        Returns
        -------
        tuple
            - list of command components for subprocess.run()
            - str: report name (derived from executable)
        """
        executable_with_args = self.executable_cmd.split()
        report = os.path.basename(executable_with_args[0]) 
        drio_command = [
            self.run,
            "-c",
            self.client,
        ]
        
        # Add config file if specified
        if self.config_file:
            drio_command.extend(["-config", self.config_file])
        
        drio_command.append("--")
        drio_command.extend(executable_with_args)
        return drio_command, report

    # collect all the data that will be stored in a log file
    def profiling(self, **kwargs):
        """
        Run the profiler using the constructed DynamoRIO command.

        Captures stdout from the profiler and stores it in a `.drio-rep` file
        if the action is "profiling".

        Raises
        ------
        subprocess.CalledProcessError
            If the command execution fails.
        """
        # self.validate_paths()
        drio_command, report = self.constuct_command() 
        try:
            print(f"Executing: {' '.join(drio_command)}")
            profiler_data = subprocess.run(drio_command, check=True, text=True, stdout=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            raise 
        self.output = profiler_data.stdout

        # store output to file
        if self.action == "profiling":
            self.report = f"{report}.drio-rep"
            with open(self.report, 'w') as drio_report:
                drio_report.write(f"Profiling output:\n {self.output}")
            print(f"Output written to file {report}.drio-rep")

    def extract_metrics(self, report_file=None, **kwargs):
        """
        Extract memory access metrics from profiling output.

        Parameters
        ----------
        report_file : str, optional
            File to read from if `action == "extract_metrics"`.

        Returns
        -------
        dict
            Extracted metrics including:
            - read_freq
            - write_freq
            - total_reads
            - total_writes
            - workingset_size

        Raises
        ------
        AttributeError
            If expected patterns are not found in the report.
        """
        toparse = ""
        if self.action == "extract_metrics":
            with open(report_file) as file:
                 toparse = file.read()
        if self.action == "both":
            toparse = self.output
        
        print(toparse)

        # Extract the memory statistics
        try:
            memory_refs = re.search(r"saw (\d+) memory references", toparse).group(1)
            reads = re.search(r"number of reads: (\d+)", toparse).group(1)
            writes = re.search(r"number of writes: (\d+)", toparse).group(1)
            working_set_size = re.search(r"working set size: (\d+)", toparse).group(1)
            
            # Note: DynamoRIO memcount doesn't provide execution time, so we'll use a placeholder
            # or calculate frequency differently
            total_memory_refs = int(memory_refs)

            # Update the data dictionary with the extracted values
            self.data.update({
                "total_memory_refs": total_memory_refs,
                "total_reads": int(reads),
                "total_writes": int(writes),
                "workingset_size": int(working_set_size),
                # Without execution time, we can't calculate frequency, so omit these fields
                # or set them to 0 if required by downstream code
            })
            
            return self.data
        except AttributeError as e:
            print(f"Failed to extract data: {e}")
            raise

    @classmethod
    def required_profiling_args(cls):
        """
        Declare required arguments for `profiling()`.

        Returns
        -------
        list
            Required argument names (["executable", "config"]).
        """
        return ["executable", "config"] 

    @classmethod
    def required_extract_args(cls, action):
        """
        Declare required arguments for `extract_metrics()`.

        Parameters
        ----------
        action : str
            The command-line action ("extract_metrics" or "both").

        Returns
        -------
        list
            Required argument names depending on the action.
        """
        if action == "extract_metrics":
            return ["report_file"]
        else:
            return [] 
