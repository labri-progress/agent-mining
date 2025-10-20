import glob
import os
import json
from heuristic import Heuristic, from_json

from github_query_helper import count_matching, set_rate_limit_logging


def load_heuristics(folder: str) -> dict[str, list[Heuristic]]:
    dico = {}
    for file in glob.glob(os.path.join(folder, "*.json")):
        heuristics_list = [
            el for el in load_heuristic_for_agent(file) if el.is_active()
        ]
        agent_name = os.path.basename(file)[:-5]
        dico[agent_name] = heuristics_list
    return dico


def load_heuristic_for_agent(file: str) -> list[Heuristic]:
    todo = []
    with open(file) as fd:
        ser_heuristics_list = json.load(fd)
        if not isinstance(ser_heuristics_list, list):
            ser_heuristics_list = [ser_heuristics_list]
            todo.append(ser_heuristics_list)
    if todo:
        with open(file, "w") as fd:
            json.dump(ser_heuristics_list, fd)
    return [from_json(el) for el in ser_heuristics_list]


# Example usage:
if __name__ == "__main__":
    set_rate_limit_logging(True)
    for agent, heuristics in load_heuristics("./agents").items():
        print("agent:", agent)
        for h in heuristics:
            if h.is_active():
                for k, v in count_matching(h, token=os.environ.get("GITHUB_TOKEN")):
                    print(f"\t{k}: {v}")
