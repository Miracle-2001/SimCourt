
import json
import os
import random
import logging
import argparse
import gradio as gr
import datetime
import time
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from tqdm import trange

from LLM.offlinellm import OfflineLLM
from LLM.apillm import APILLM
from agent import Agent
from frontEnd import frontEnd
from main import CourtSimulation, parse_arguments

console = Console()

def main():
    print("In main..")
    args = parse_arguments()
    simulation = CourtSimulation(args.init_config, args.stage_prompt, args.case,  args.log_level, args.log_think,launch=False)
    
    simu_list=[1] #[1,2,3]
    data_source="video" # LJP
    print(f"simu_list: {simu_list}")

    model = "deepseek-v3-250324"
    for simu_id in simu_list:
        # try:
        print(f"----- simulation id = {simu_id} -----")
        simulation.start_simluation(None,None,None,None, model, model, model, model, model,simulation_id=simu_id,source=data_source)
        print(f"------- end  {simu_id} --------")

if __name__ == "__main__":
    main()