#!/bin/zsh

python3 generate_oracle_vals.py normal
python3 generate_oracle_vals.py zipf
python3 assign_val_to_de.py
python3 graph_comp_oracles.py 
