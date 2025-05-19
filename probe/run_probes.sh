#!/bin/bash
#SBATCH -p gpu               
#SBATCH --gres=gpu:1         
#SBATCH -N 1                 
#SBATCH -n 4                 
#SBATCH --mem=63G            
#SBATCH -t 24:00:00          
#SBATCH -J probe_experiment  
#SBATCH -e logs/probe/0z8f51y4/probe_experiment_0z8f51y4-%j.err  
#SBATCH -o logs/probe/0z8f51y4/probe_experiment_0z8f51y4-%j.out  

# Activate your environment
source ~/.bashrc
source ~/miniconda3/etc/profile.d/conda.sh
conda activate syntheory

# Run the probing script with the sweep_id and wandb project
python -m probe.main --sweep_id ahn5cshr --wandb_project music-theory-crepe

echo "syntheory"

