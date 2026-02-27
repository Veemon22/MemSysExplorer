#!/bin/bash

MODES=(
    "rram_mlc"
    "fefet_mlc"
    "fefet_50d"
    "fefet_100d"
    "fefet_200d"
    "fefet_300d"
)

for mode in "${MODES[@]}"; do
    echo ">>> Processing mode: $mode"

    case "$mode" in
        # These are the Multi-Level Cell models (6-bit support)
        rram_mlc|fefet_mlc)
            I_BITS=2
            F_BITS=4
            REP_1=8
            REP_2=8
            ;;
        # These are the Domain/SLC models (2-bit support)
        fefet_*d)
            I_BITS=1
            F_BITS=1
            REP_1=2
            REP_2=2
            ;;
        # Default fallback just in case
        *)
            I_BITS=2
            F_BITS=4
            REP_1=8
            REP_2=8
            ;;
    esac

    python run_msxfi.py \
      --mode "$mode" \
      --q_type afloat \
      --int_bits "$I_BITS" \
      --frac_bits "$F_BITS" \
      --rep_conf "$REP_1" "$REP_2"

    echo ">>> Finished $mode"
    echo "---------------------------------------"
done