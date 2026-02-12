from profilers.PatternConfig import PatternConfig

class NVBitConfig(PatternConfig):
    @classmethod
    def populating(cls, report_data, metadata=None):
        """
        Populate the NVBit pattern configuration from raw profiler data.

        Parameters
        ----------
        report_data : dict
            Dictionary with keys like 'total_reads', 'read_freq', etc.
        metadata : BaseMetadata, optional
            System-level metadata (e.g., GPU, CPU info).

        Returns
        -------
        NVBitConfig
            An instance of the configuration with memory behavior attributes.
        """
        unit_override = {
            "total_read": "count",
            "total_read": "count",
            "read_freq": "count/s",
            "write_freq": "count/s"
        } 

        return cls(
            exp_name="NVBitProfilers",
            benchmark_name=report_data.get("benchmark", "Unnamed"),
            read_freq=report_data.get("read_freq"),
            total_reads=report_data.get("total_reads"),
            write_freq=report_data.get("write_freq"),
            total_writes=report_data.get("total_writes"),
            workingset_size=report_data.get("workingset_size"),
            execution_time=report_data.get("execution_time"),
            read_size=report_data.get("read_size", 4),  # default 4B
            write_size=report_data.get("write_size", 4),
            unit=unit_override,
            metadata=metadata
        )

