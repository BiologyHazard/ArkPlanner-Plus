import ArkPlanner

if __name__ == '__main__':
    ap = ArkPlanner.ArkPlanner(update=ArkPlanner.auto_update())
    req_dct = ap.get_requirements(ArkPlanner.requirements_path)
    ap.get_plan(req_dct, show_history=False,
                min_times=0, byproduct_rate_coefficient=1.8, print_output=True)
