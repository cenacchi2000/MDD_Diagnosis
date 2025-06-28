"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""
import json
from pathlib import Path
import os
import os.path as osp




class Activity:
    def on_start(self):
        self.inspect_functions_json()
        pass

    def on_stop(self):
        pass

    def inspect_functions_json(self):
        functions_path = Path(__file__).parent / "profiles_function_description.json"
        print(f'path file: {Path(__file__)}| parent: {Path(__file__).parent}')
        path_exists = osp.exists(functions_path)
        print(f'function paths exists? {path_exists}')
        sys_functions_path = Path(__file__).parent / "../../../HB3/chat/knowledge/profiles_function_description.json"
        sys_func_folder = osp.join(Path(__file__).parent, "../../../HB3/chat/knowledge")
        print(f'sys func folder exists: {osp.exists(sys_func_folder)}, {sys_func_folder}')
        if osp.exists(sys_func_folder):
            os.listdir(sys_func_folder)
        print(f'sys functions path exists: {osp.exists(sys_functions_path)}')
        with open(sys_functions_path) as fd:
            FUNCTIONS = json.load(fd)
        print(f'type functions{type(FUNCTIONS)}; len funcs: {len(FUNCTIONS)} \n {FUNCTIONS}')
        for func in FUNCTIONS:
            print(func)

    @system.tick(fps=10)
    def on_tick(self):
        pass
