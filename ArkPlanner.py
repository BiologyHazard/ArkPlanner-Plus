import json
import os
import time
import urllib.request
import numpy as np
import scipy.optimize

penguin_url = 'https://penguin-stats.io/PenguinStats/api/v2/'
matrix_url = 'result/matrix?show_closed_zones=true'
stages_url = 'stages'
matrix_path = 'matrix.json'
stages_path = 'stages.json'

item_table_path = 'data/item_table.json'
formulas_path = 'data/formulas.json'
shop_path = 'data/shop.json'
full_requirements_path = 'data/full_requirements.json'
requirements_path = 'requirements.txt'

time_path = 'cache/last_update_time.txt'
headers = {'User-Agent': 'ArkPlanner+'}


class ArkPlanner(object):
    def __init__(self, url=penguin_url, path='cache/', update=False):
        self.ctime = time.time()
        self.get_items(item_table_path)
        self.get_formulas(formulas_path)
        self.get_shop(shop_path)
        self.get_full_requirements(full_requirements_path)
        self.get_data(url, path, update)

    def get_items(self, item_table_path):
        self.items_dct = load_data(item_table_path)
        self.items_name_to_id = {
            item['name']: item_id for item_id, item in self.items_dct.items()}
        self.items_id_to_idx = {item_id: index for index,
                                item_id in enumerate(self.items_dct)}
        self.items_lst = [item_id for item_id,
                          item_dct in self.items_dct.items()]

    def get_formulas(self, formulas_path):
        self.formulas = load_data(formulas_path)

    def get_shop(self, shop_path):
        self.shop = load_data(shop_path)

    def get_full_requirements(self, full_requirements_path):
        self.full_requirements = load_data(full_requirements_path)

    def get_data(self, url=penguin_url, path='cache/', from_web=False):
        if not from_web:
            try:
                self.drop_matrix = load_data(path + matrix_path)
                self.stages = load_data(path + stages_path)
                self.updated = False
            except:
                self.update_data(url, path)
        else:
            self.update_data(url, path)

        if self.updated:
            with open(time_path, 'w', encoding='utf-8') as f:
                f.write('%f\n%s' % (self.ctime, time.strftime(
                    '%Y/%m/%d %H:%M:%S', time.localtime(self.ctime))))

    def update_data(self, url=penguin_url, path='cache/'):
        self.drop_matrix = request_data(url + matrix_url)
        self.stages = request_data(url + stages_url)
        save_data(self.drop_matrix, path + matrix_path)
        save_data(self.stages, path + stages_path)
        self.updated = True

    def get_requirements(self, requirements_path=requirements_path):
        req_dct = {}
        with open(requirements_path, 'r', encoding='utf-8') as fr:
            for line in fr.readlines():
                l = line.split()
                name = l[0]
                item_id = self.items_name_to_id[name]
                req = int(
                    l[1]) if l[1] != '-1' else self.full_requirements[item_id]
                try:
                    req -= int(l[2])
                    try:
                        c_req == int(
                            l[3]) if l[3] != '-1' else self.full_requirements[item_id] - int(l[2])
                    except:
                        c_req = req
                except:
                    c_req = req
                req_dct[item_id] = {'req': req, 'cal': c_req}
        return req_dct

    def process_data(self,
                     min_times=200,
                     blacklist=None,
                     contains_activity=True,
                     show_history=False,
                     byproduct_rate_coefficient=1.8):
        t1 = time.time()
        if blacklist == None:
            blacklist = []
        self.stages_id_to_name = {stage['stageId']: stage['code']
                                  for stage in self.stages}
        self.stages_name_to_id = {name: stage_id for stage_id,
                                  name in self.stages_id_to_name.items()}
        self.idx_in_stages = {stage['stageId']: idx for idx,
                              stage in enumerate(self.stages)}

        self.stages_lst = []
        for drop in self.drop_matrix['matrix']:
            sid = drop['stageId']
            if ((sid not in self.stages_lst) and  # 未在self.stages_lst中
                # 理智消耗不为0
                (self.stages[self.idx_in_stages[sid]]['apCost'] > 0) and
                # 不在黑名单中
                (self.stages_id_to_name[sid] not in blacklist) and
                # 掉落统计量满足要求
                (drop['times'] >= min_times) and
                # 判断是否需要排除活动图
                (contains_activity or self.stages[self.idx_in_stages[sid]]['stageType']
                 != 'ACTIVITY') and
                # 排除物资补给
                (self.stages[self.idx_in_stages[sid]]['zoneId'] != 'gachabox') and
                # 判断是否需要排除已经关闭的图
                    (show_history or 'end' not in drop or drop['end'] >= self.ctime*1000)):
                self.stages_lst.append(sid)

        # 字典，将stage_id转为index
        self.stages_id_to_idx = {
            stage_id: stage_idx for stage_idx, stage_id in enumerate(self.stages_lst)}

        # 字典，作战的理智消耗
        self.stages_ap_cost = dict()
        for stage in self.stages:
            if stage['stageId'] in self.stages_lst:
                self.stages_ap_cost[stage['stageId']] = stage['apCost']

        # 二维列表，A[i][j] 表示进行一次i转化获得j物品的量
        self.droprate_matrix = [
            [0.0 for j in range(len(self.items_dct))] for i in range(len(self.stages_lst))]
        for drop in self.drop_matrix['matrix']:
            sid = drop['stageId']
            iid = drop['itemId']
            if sid in self.stages_lst and iid in self.items_dct:
                # and iid != 'furni' and iid != '4001_1000' and iid != '4001_1500' and iid != '4001_2000':
                self.droprate_matrix[self.stages_id_to_idx[sid]][self.items_id_to_idx[iid]] = (
                    drop['quantity'] / drop['times'])

        # 添加龙门币获取
        for stage_id, stage_idx in self.stages_id_to_idx.items():
            self.droprate_matrix[stage_idx][self.items_id_to_idx['4001']
                                            ] = self.stages_ap_cost[stage_id] * 12
        self.update_stages()

        # 添加formula
        self.update_formulas()
        self.formulas_matrix = []
        for formula in self.formulas:
            formula_vector = [0.0 for i in range(len(self.items_dct))]
            formula_vector[self.items_id_to_idx[formula['itemId']]
                           ] += formula['count']
            formula_vector[self.items_id_to_idx['4001']] -= formula['goldCost']
            for cost in formula['costs']:
                formula_vector[self.items_id_to_idx[cost['id']]
                               ] -= cost['count']
            byproduct_rate = (formula['extraOutcomeRate']
                              * byproduct_rate_coefficient)
            total_weight = formula['totalWeight']
            for extra_outcome in formula['extraOutcomeGroup']:
                formula_vector[self.items_id_to_idx[extra_outcome['itemId']]] += (
                    extra_outcome['weight'] * extra_outcome['itemCount'] / total_weight * byproduct_rate)
            self.formulas_matrix.append(formula_vector)

        # 添加shop
        self.shop_matrix = []
        self.shop_bounds = []
        for deal in self.shop:
            deal_vector = [0.0 for i in range(len(self.items_dct))]
            deal_vector[self.items_id_to_idx[deal['id']]] += 1
            for cost in deal['costs']:
                deal_vector[self.items_id_to_idx[cost['id']]] -= cost['count']
            if 'availCount' in deal:
                bound = (0, deal['availCount'])
            else:
                bound = (0, None)
            self.shop_matrix.append(deal_vector)
            self.shop_bounds.append(bound)

        assert len(self.items_name_to_id) == len(self.items_lst) == len(
            self.items_dct) == len(self.items_id_to_idx)
        assert len(self.stages_ap_cost) == len(self.stages_lst) == len(
            self.stages_id_to_idx)

    def update_stages(self):
        self.update_stage({'4001': 3480}, 'sub_04-2-3', 'S4-6', 21)
        self.update_stage({'4001': 1700}, 'wk_melee_1', 'CE-1', 10)
        self.update_stage({'4001': 2800}, 'wk_melee_2', 'CE-2', 15)
        self.update_stage({'4001': 4100}, 'wk_melee_3', 'CE-3', 20)
        self.update_stage({'4001': 5700}, 'wk_melee_4', 'CE-4', 25)
        self.update_stage({'4001': 7500}, 'wk_melee_5', 'CE-5', 30)
        # self.update_stage({'4006': 21}, 'wk_toxic_1', 'AP-1', 10)
        # self.update_stage({'4006': 21}, 'wk_toxic_2', 'AP-2', 15)
        # self.update_stage({'4006': 21}, 'wk_toxic_3', 'AP-3', 20)
        # self.update_stage({'4006': 21}, 'wk_toxic_4', 'AP-4', 25)
        self.update_stage({'4006': 21, '4001': 360}, 'wk_toxic_5', 'AP-5', 30)
        self.update_stage({'3113': 0.5, '3114': 3, '4001': 360},
                          'wk_armor_5', 'SK-5', 30)
        self.update_stage({'2002': 1, '2003': 1, '2004': 3,
                           '4001': 360}, 'wk_kc_5', 'LS-5', 30)

        self.update_stage(
            {'3231': 0.5, '3261': 0.5, '4001': 216}, 'pro_a_1', 'PR-A-1', 18)
        self.update_stage(
            {'3241': 0.5, '3251': 0.5, '4001': 216}, 'pro_b_1', 'PR-B-1', 18)
        self.update_stage(
            {'3211': 0.5, '3271': 0.5, '4001': 216}, 'pro_c_1', 'PR-C-1', 18)
        self.update_stage(
            {'3221': 0.5, '3281': 0.5, '4001': 216}, 'pro_d_1', 'PR-D-1', 18)
        self.update_stage(
            {'3232': 0.5, '3262': 0.5, '4001': 432}, 'pro_a_2', 'PR-A-2', 36)
        self.update_stage(
            {'3242': 0.5, '3252': 0.5, '4001': 432}, 'pro_b_2', 'PR-B-2', 36)
        self.update_stage(
            {'3212': 0.5, '3272': 0.5, '4001': 432}, 'pro_c_2', 'PR-C-2', 36)
        self.update_stage(
            {'3222': 0.5, '3282': 0.5, '4001': 432}, 'pro_d_2', 'PR-D-2', 36)

    def update_stage(self, drop_dct, stage_id=None, stage_name=None, ap_cost=None):
        if stage_id == None:
            stage_id = self.stages_name_to_id[stage_name]
        if stage_name == None:
            stage_name = self.stages_id_to_name[stage_id]
        if ap_cost == None:
            ap_cost = self.stages_ap_cost[stage_id]

        if stage_id not in self.stages_lst:
            stage_idx = len(self.stages_lst)
            self.stages_lst.append(stage_id)
            self.stages_id_to_idx[stage_id] = stage_idx
            self.stages_name_to_id[stage_name] = stage_id
            self.stages_id_to_name[stage_id] = stage_name
            self.stages_ap_cost[stage_id] = ap_cost
            self.droprate_matrix.append(
                [0.0 for i in range(len(self.items_dct))])
        else:
            stage_idx = self.stages_id_to_idx[stage_id]
        for item_id, count in drop_dct.items():
            self.droprate_matrix[stage_idx][self.items_id_to_idx[item_id]] = count

    def update_formulas(self):
        self.update_formula('EXP', 200, 0, [{'id': '2001', 'count': 1}])
        self.update_formula('EXP', 400, 0, [{'id': '2002', 'count': 1}])
        self.update_formula('EXP', 1000, 0, [{'id': '2003', 'count': 1}])
        self.update_formula('EXP', 2000, 0, [{'id': '2004', 'count': 1}])
        self.update_formula('2003', 1, 0, [{'id': 'BASE_CAP', 'count': 10800}])
        self.update_formula('3003', 1, 0, [{'id': 'BASE_CAP', 'count': 4320}])
        self.update_formula('BASE_CAP', 10.8, 0, [{'id': 'EXP', 'count': 1}])
        self.update_formula('BASE_CAP', 4320, 0, [{'id': '3003', 'count': 1}])
        self.update_formula('3213', 1, 0, [{'id': '3212', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3223', 1, 0, [{'id': '3222', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3233', 1, 0, [{'id': '3232', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3243', 1, 0, [{'id': '3242', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3253', 1, 0, [{'id': '3252', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3263', 1, 0, [{'id': '3262', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3273', 1, 0, [{'id': '3272', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])
        self.update_formula('3283', 1, 0, [{'id': '3282', 'count': 2}, {
                            'id': '32001', 'count': 1}, {'id': 'BASE_CAP', 'count': 3600}])

    def update_formula(self, item_id, count=1, gold_cost=0, costs=None,
                       extra_outcome_rate=0, extra_outcome_group=None):
        if costs == None:
            costs = []
        if extra_outcome_group == None:
            extra_outcome_group = []

        formula = dict()
        formula['itemId'] = item_id
        formula['count'] = count
        formula['goldCost'] = gold_cost
        formula['costs'] = costs
        formula['extraOutcomeRate'] = extra_outcome_rate
        formula['extraOutcomeGroup'] = extra_outcome_group
        total_weight = 0
        for dct in extra_outcome_group:
            total_weight += dct['weight']
        formula['totalWeight'] = total_weight
        self.formulas.append(formula)

    def get_plan(self,
                 req_dct=None,
                 print_output=True,
                 min_times=200,
                 blacklist=None,
                 contains_activity=True,
                 show_history=False,
                 byproduct_rate_coefficient=1.8):
        self.process_data(min_times=min_times,
                          blacklist=blacklist,
                          contains_activity=contains_activity,
                          show_history=show_history,
                          byproduct_rate_coefficient=byproduct_rate_coefficient)
        b_stage_1 = [0 for i in range(len(self.items_dct))]
        b_stage_2 = [0 for i in range(len(self.items_dct))]
        for item_id, req in req_dct.items():
            iidx = self.items_id_to_idx[item_id]
            b_stage_1[iidx] = req['cal']
            b_stage_2[iidx] = req['req']
        formulas_start = len(self.droprate_matrix)
        shop_start = formulas_start + len(self.formulas_matrix)
        end = shop_start+len(self.shop_matrix)
        A_T = self.droprate_matrix + self.formulas_matrix + self.shop_matrix
        A = turn(A_T)
        c = [1e-4 for i in range(len(A_T))]
        for stage_id, ap_cost in self.stages_ap_cost.items():
            c[self.stages_id_to_idx[stage_id]] = ap_cost
        # 求解线性规划
        stage_1_solution = scipy.optimize.linprog(c=c,
                                                  A_ub=negative(A),
                                                  b_ub=negative(b_stage_1),
                                                  method='revised simplex')
        assert stage_1_solution.status == 0, stage_1_solution.message
        c_stage_2 = c[:]
        for cidx, count in enumerate(stage_1_solution.x):
            if count < 0.001:
                c_stage_2[cidx] = 1e10
        primal_solution = scipy.optimize.linprog(c=c_stage_2,
                                                 A_ub=negative(A),
                                                 b_ub=negative(b_stage_2),
                                                 method='revised simplex')
        assert primal_solution.status == 0, stage_1_solution.message
        dual_solution = scipy.optimize.linprog(c=negative(b_stage_2),
                                               A_ub=A_T,
                                               b_ub=c_stage_2,
                                               method='revised simplex')
        assert dual_solution.status == 0, stage_1_solution.message

        # print(stage_1_solution)
        # print(primal_solution)
        # print(dual_solution)
        primal_x = primal_solution.x
        dual_x = dual_solution.x

        stages = dict()
        syntheses = []
        shop = []
        items_value = dict()
        efficiency = []

        for cidx in range(formulas_start):
            stages[self.stages_lst[cidx]] = primal_x[cidx]
        for cidx in range(formulas_start, shop_start):
            syntheses.append(primal_x[cidx])
        for cidx in range(shop_start, end):
            shop.append(primal_x[cidx])
        for iidx, item_id in enumerate(self.items_lst):
            items_value[item_id] = dual_x[iidx]
        for cidx in range(formulas_start):
            gp = gn = 0
            for iidx, value in enumerate(dual_x):
                if A_T[cidx][iidx] > 0:
                    gp += A_T[cidx][iidx] * value
                elif A_T[cidx][iidx] < 0:
                    gn -= A_T[cidx][iidx] * value
            efficiency.append(gp / (gn + c[cidx]))

        res = {
            'apCost': primal_solution.fun,
            'stages': stages,
            'syntheses': syntheses,
            'shop': shop,
            'itemsValue': items_value,
            'efficiency': efficiency
        }
        # print(res)

        # 输出结果
        if print_output:
            self.print_result(res)
            '''
            print(stage_1_solution.fun)
            print(primal_solution.fun)
            print(-dual_solution.fun)
            print('转化：')
            for cidx, count in enumerate(primal_x):
                if abs(count) > 0.0001:
                    if cidx < formulas_start:
                        print('刷图：%s %.2f 次' % (
                            self.stages_id_to_name[self.stages_lst[cidx]], count))
                    elif cidx < shop_start:
                        print('合成：%s (%s) %.2f 次' % (
                            self.items_dct[self.formulas[cidx - formulas_start]['itemId']]['name'], self.items_dct[self.formulas[cidx - formulas_start]['costs'][0]['id']]['name'], count))
                    else:
                        print('购买：%s %.2f 次' % (
                            self.items_dct[self.shop[cidx - shop_start]['id']]['name'], count))

            print('\n材料价值：')
            for iidx, value in enumerate(dual_x):
                if abs(value) >= 0.001:
                    print(
                        self.items_dct[self.items_lst[iidx]]['name'], round(value, 5))

            print('\n转化效率：')
            for cidx in range(len(A_T)):
                gp = gn = 0
                for iidx, value in enumerate(dual_x):
                    if A_T[cidx][iidx] >= 0:
                        gp += A_T[cidx][iidx] * value
                    else:
                        gn -= A_T[cidx][iidx] * value
                if cidx < formulas_start:
                    print(self.stages_id_to_name[self.stages_lst[cidx]], round(
                        gp / (gn + c[cidx]), 3))
                elif cidx < shop_start:
                    print(
                        self.items_dct[self.formulas[cidx - shop_start]['itemId']]['name'], round(gp / gn, 3))
                        '''

        return res

    def print_result(self, res):
        print('最少消耗理智：%.0f' % res['apCost'])
        print('刷图：')
        '''for stage in self.stages:
            stage_id = stage['stageId']
            if stage_id in self.stages_lst:
                times = res['stages'][stage_id]
                if times > 0.0001:
                    get = []
                    for item_idx, droprate in enumerate(self.droprate_matrix[self.stages_id_to_idx[stage_id]]):
                        if droprate > 0 and self.items_lst[item_idx] != '4001':
                            get.append('%s(%.2f)' %
                                       (self.items_dct[self.items_lst[item_idx]]['name'], droprate * times))
                    print('%s (%.0f次，消耗%.0f理智) ===> ' % (
                        self.stages_id_to_name[stage_id], times, self.stages_ap_cost[stage_id]*times) + '、'.join(get))'''

        stage_output_lst = []
        for stage_id, times in res['stages'].items():
            if times > 0.0001:
                get = []
                for item_idx, droprate in enumerate(self.droprate_matrix[self.stages_id_to_idx[stage_id]]):
                    if droprate > 0:  # and self.items_lst[item_idx] != '4001':
                        get.append('%s(%.2f)' %
                                   (self.items_dct[self.items_lst[item_idx]]['name'], droprate * times))
                stage_output_lst.append('%s (%.0f次，消耗%.0f理智) ===> ' % (
                    self.stages_id_to_name[stage_id], times, self.stages_ap_cost[stage_id]*times) + '、'.join(get))
        print('\n'.join(sorted(stage_output_lst)))

        print('\n合成：')
        for formula_idx, times in enumerate(res['syntheses']):
            if times > 0.0001:
                costs = []
                for cost in self.formulas[formula_idx]['costs']:
                    costs.append('%s(%.0f)' % (
                        self.items_dct[cost['id']]['name'], cost['count'] * times))
                print('%s(%.0f次，消耗%.0f龙门币) <=== ' % (
                    self.items_dct[self.formulas[formula_idx]['itemId']]['name'], times, self.formulas[formula_idx]['goldCost']) + '、'.join(costs))

        print('\n物品价值：')
        for item_id, value in res['itemsValue'].items():
            if value > 1:
                print('%s：%.3f' %
                      (self.items_dct[item_id]['name'], value))
            elif value > 0.0000001:
                print('%s：%.5f' %
                      (self.items_dct[item_id]['name'], value))

        print('\n转化效率')
        for cidx, eff in enumerate(res['efficiency']):
            if cidx < len(self.stages_lst):
                print('%s：%.4f' %
                      (self.stages_id_to_name[self.stages_lst[cidx]], eff))

    def _print(self):  # 用于调试
        dct = dict()
        ddct = dict()
        for sidx, sid in enumerate(self.stages_lst):
            sdct = dict()
            sdct['id'] = sid
            sdct['理智消耗'] = self.stages_ap_cost[sid]
            sdct['类型'] = self.stages[self.idx_in_stages[sid]]['stageType']
            sdct['区域'] = self.stages[self.idx_in_stages[sid]]['zoneId']
            sdct['掉落'] = dict()
            for iidx, iid in enumerate(self.items_lst):
                if self.droprate_matrix[sidx][iidx] != 0.0:
                    sdct['掉落'][self.items_dct[iid]['name']
                               ] = round(self.droprate_matrix[sidx][iidx], 3)
            ddct[self.stages_id_to_name[sid]] = sdct
        fdct = dict()
        for fidx, formula in enumerate(self.formulas_matrix):
            sdct = dict()
            sdct['idx'] = fidx
            for iidx, iid in enumerate(self.items_lst):
                if formula[iidx] != 0.0:
                    sdct[self.items_dct[iid]['name']
                         ] = formula[iidx]
            fdct['合成：' + self.formulas[fidx]['name']] = sdct

        dct['刷图'] = ddct
        dct['合成'] = fdct
        json.dump(dct, f, ensure_ascii=False, indent=4)


def save_data(data, path):
    try:
        os.makedirs(os.path.dirname(path))
    except:
        pass
    with open(path, 'w', encoding='utf-8') as fw:
        json.dump(data, fw, ensure_ascii=False, indent=4)


def load_data(path):
    with open(path, 'r', encoding='utf-8') as fr:
        return json.load(fr)


def request_data(url, print_process=True):
    if print_process:
        print(f'Requesting data from {url} ...')
    req = urllib.request.Request(url, None, headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if print_process:
                print('Done!')
            return json.loads(response.read().decode())
    except urllib.error.URLError as err:
        raise TimeoutError(
            f'Timed out when requesting data from {url}.\nPlease try again.')


def auto_update(secs=86400, path=time_path):
    try:
        os.makedirs(os.path.dirname(path))
    except:
        pass
    try:
        with open(path, 'r', encoding='utf-8') as f:
            last_update_time = float(f.readline())
        if time.time() - last_update_time <= secs:
            update = False
    except:
        update = True
    return update


def turn(mat):  # 求转置矩阵
    if mat == []:
        return []
    rows = len(mat)
    cols = len(mat[0])
    if cols == 0:
        return []
    '''res = []
    for i in range(cols):
        line = []
        for j in range(rows):
            line.append(mat[j][i])'''

    return [[mat[j][i] for j in range(rows)] for i in range(cols)]


def negative(mat):  # 求负矩阵 / 向量
    if type(mat) != list:
        return - mat
    res = []
    for line in mat:
        res.append(negative(line))
    return(res)


if __name__ == "__main__":
    # f = open('output.json', 'w', encoding='utf-8')
    ap = ArkPlanner(update=False)
    req_dct = ap.get_requirements(requirements_path)
    ap.get_plan(req_dct, show_history=False,
                min_times=0, byproduct_rate_coefficient=1.8, print_output=True)
    # f.close()
