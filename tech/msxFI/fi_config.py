import torch
import numpy as np

# define different NVM fault models
mem_model = 'rram_mlc'

# provide paths to fault model distributions stored in mem_data directory
# for more information, please see nvmexplorer.seas.harvard.edu
mem_dict = {
    'rram_mlc': 'mlc_rram_args.p',
    'dram3t': 'dram3t_args.p',
    'dram1t': 'dram1t_args.p',
    'dram333t': 'dram333t_args.p',
    'fefet_mlc': 'mlc_fefet_args.p',
    'fefet_50d': 'slc_fefet_50dom.p',
    'fefet_100d': 'slc_fefet_100dom.p',
    'fefet_200d': 'slc_fefet_200dom.p',
    'fefet_300d': 'slc_fefet_300dom.p'
}

# Configuration parameters
temperature = 300  # Temperature in Kelvin (300K-400K)
feature_size = 22  # Feature size in nm
SS = 90  # Subthreshold Swing in mV/dec

# Default retention times for DRAM models (in microseconds)
default_retention_us = {
    'dram1t': 64000.0,   # 64ms for standard 1T DRAM
    'dram3t': 100.0,     # 100us for 3T DRAM
    'dram333t': 501.0,   # 501us for 333T eDRAM
}

# optional print statements during msxFI execution
Debug=False

# Configuration for afloat processing
true_con=True

if torch.cuda.is_available():
  pt_device = "cuda"
  if Debug:
    print("CUDA is available")
else:
  pt_device = "cpu"
