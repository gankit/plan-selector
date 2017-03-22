# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from plans import get_model
from flask import Blueprint, redirect, render_template, request, url_for
import logging
import json
import urllib.request

crud = Blueprint('crud', __name__)
# [START index]
@crud.route("/")
def index():
    return render_template("index.html")
# [END index]

@crud.route("/start", methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        id = None
        if 'id' in data:
            id = data['id']
        family = get_model().update('Family', data=data, id=id)
        if 'save' in request.form:
            return redirect(url_for('.start', family=family['id']))
        else:
            return redirect(url_for('.addplan', family=family['id']))

    family_id = request.args.get('family', None)


    if family_id:
        family_id = family_id.encode('utf-8')

    family = get_model().item('Family', id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.start'))

    return render_template("start.html", family=family)

# [END start]

# [START plans]
@crud.route("/plans")
def plans():
    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')

    plans, family = get_model().plans(family_id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.start'))

    return render_template(
        "plans.html",
        family=family,
        plans=plans)
# [END plans]


@crud.route('/<id>')
def view_plan(id):
    plan = get_model().item('Plan', id=id)
    return redirect(url_for('.addplan', family=plan['family_id'], plan=id))


# [START addplan]
@crud.route('/addplan', methods=['GET', 'POST'])
def addplan():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        plan_id = None
        if 'plan_id' in data:
            plan_id = data['plan_id']
        plan = get_model().update('Plan', data=data, id=plan_id)

        if 'save' in request.form:
            return redirect(url_for('.addplan', family=plan['family_id'], plan=plan['id']))
        else:
            return redirect(url_for('.plans', family=plan['family_id']))

    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')
    family = get_model().item('Family', id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.start'))

    plan_id = request.args.get('plan', None)
    if plan_id:
        plan_id = plan_id.encode('utf-8')
    plan = get_model().item('Plan', id=plan_id)

    # Edge case when an incorrect plan_id is supplied
    if not plan and plan_id:
        return redirect(url_for('.plans', family=family_id))

    return render_template("addplan.html", family=family, plan=plan)
# [END addplan]

# [START recommendation]
@crud.route("/recommendation")
def recommendation():
    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')

    plans, family = get_model().plans(family_id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.start'))

    spreadsheetId = '1PDdMliNoxzSJONZJnKg9AwyR5HAPu1_UWxMqib3JyAg'
    rangeName = 'Utilization data!A2:E'
    url = 'https://sheets.googleapis.com/v4/spreadsheets/1PDdMliNoxzSJONZJnKg9AwyR5HAPu1_UWxMqib3JyAg/values/Util%20clean%21A2%3AE?alt=json&key=AIzaSyBFcYOZ_jRwEsh377d7WRzFer-_rLggucI'
    comparison_table = {}
    coverage_types = ['ee']
    if family['marital_status'] == 'married':
        coverage_types.append('ee_spouse') 
    if int(family['children']) > 0 :
        coverage_types.append('ee_children')
    if family['marital_status'] == 'married' and int(family['children']) > 0:
        coverage_types.append('ee_family')
    print(coverage_types)
    with urllib.request.urlopen(url) as response:
        obj = response.read().decode('utf8')
        data = json.loads(obj)
        comparison_dataset = data['values']
        me_employer = None
        spouse_employer = None
        # print(comparison_dataset)
        for plan in plans:
            plan_id = str(plan.key.id)
            premiums = get_annual_premiums(plan=plan, coverage_types=coverage_types)
            deductibles = get_deductibles(plan=plan, coverage_types=coverage_types)
            oops = get_oop(plan=plan, coverage_types=coverage_types)
            er_fundings = get_er_fundings(plan=plan, coverage_types=coverage_types)
            wellness_benefits = get_wellness_benefits(plan=plan, coverage_types=coverage_types)
            employer = plan['employer_name']
            if plan['plan_source'] == 'employer':
                me_employer = employer
            elif plan['plan_source'] == 'spouse_employer':
                spouse_employer = employer

            if employer not in comparison_table:
                comparison_table[employer] = {}
            for coverage_type in coverage_types:
                if coverage_type not in comparison_table[employer]:
                    comparison_table[employer][coverage_type] = {}
                if plan_id not in comparison_table[employer][coverage_type]:
                    comparison_table[employer][coverage_type][plan_id] = {}
                utilization = {}
                if coverage_type == 'ee':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                if coverage_type == 'ee_spouse':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization_1 = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                    age = str(family['spouse_age'])
                    gender = str(family['spouse_gender'])
                    utilization_2 = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + utilization_2[util]
                if coverage_type == 'ee_children':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization_1 = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                    utilization_2 = expected_utilization(data=comparison_dataset, age='Child', gender='Child')
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + int(family['children'])*utilization_2[util]
                if coverage_type == 'ee_family':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization_1 = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                    utilization_2 = expected_utilization(data=comparison_dataset, age='Child', gender='Child')
                    age = str(family['spouse_age'])
                    gender = str(family['spouse_gender'])
                    utilization_3 = expected_utilization(data=comparison_dataset, age=age, gender=gender)
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + int(family['children'])*utilization_2[util] + utilization_3[util]

                comparison_table[employer][coverage_type][plan_id] = utilization
                for util in utilization:
                    cost = 0
                    eu = utilization[util]
                    xyz = 0
                    premium = premiums[coverage_type]
                    oop = oops[coverage_type]
                    deductible = deductibles[coverage_type]
                    er_funding = er_fundings[coverage_type]
                    wellness_benefit = wellness_benefits[coverage_type]
                    if eu < deductible:
                        xyz = eu
                    else:
                        xyz = min(deductible + 0.2 * (eu - deductible), oop)
                    cost = premium + xyz - er_funding - wellness_benefit
                    comparison_table[employer][coverage_type][plan_id][util] = cost

        # print(comparison_table)
        best_plans = {'low':{}, 'med':{}, 'high':{}}
        for coverage_type in coverage_types:
            if coverage_type not in best_plans['low']:
                for util in best_plans:
                    best_plans[util][coverage_type] = {}
            for employer in comparison_table:
                min_cost = {'low':10000000, 'med':10000000, 'high':10000000}
                for plan_id in comparison_table[employer][coverage_type]:
                    for util in comparison_table[employer][coverage_type][plan_id]:
                        cost = comparison_table[employer][coverage_type][plan_id][util]
                        if cost < min_cost[util]:
                            min_cost[util] = cost
                            best_plans[util][coverage_type][employer] = plan_id

        # print(best_plans)
        print(me_employer)
        print(spouse_employer)
        recommended_plans = {'low':{}, 'med':{}, 'high':{}}
        recommended_plans_cost = {'low':{}, 'med':{}, 'high':{}}
        recommended_coverage_split = {'low':{}, 'med':{}, 'high':{}}
        if me_employer is not None and spouse_employer is None:
            top_coverage = coverage_types[len(coverage_types) - 1]
            for util in best_plans:
                top_plan_id = best_plans[util][top_coverage][me_employer]
                recommended_plans[util][me_employer] = top_plan_id
                recommended_plans_cost[util][me_employer] = comparison_table[me_employer][top_coverage][top_plan_id][util]
                recommended_coverage_split[util][me_employer] = top_coverage
        elif me_employer is not None and spouse_employer is not None:
            if int(family['children']) > 0 :
                coverage_split_types = [{me_employer:'ee_family'}, {me_employer:'ee', spouse_employer:'ee_children'}, {me_employer:'ee_children', spouse_employer:'ee'}, {spouse_employer:'ee_family'}]
            else:
                coverage_split_types = [{me_employer:'ee_spouse'}, {me_employer:'ee', spouse_employer:'ee'}, {spouse_employer:'ee_spouse'}]
            for util in best_plans:
                min_cost = 1000000
                top_employer = None
                top_plan_id = None
                for split_type in coverage_split_types:
                    cost = 0
                    plans = split_type
                    costs = split_type
                    for employer in split_type:        
                        coverage = split_type[employer]           
                        plan_id = best_plans[util][coverage][employer]
                        plans[employer] = plan_id
                        plan_cost = comparison_table[employer][coverage][plan_id][util]
                        cost += plan_cost
                        costs[employer] = plan_cost
                    if cost < min_cost:
                        min_cost = cost
                        recommended_plans[util] = plans
                        recommended_plans_cost[util] = plan_cost
                        recommended_coverage_split[util] = split_type

        print(recommended_plans)
        print(recommended_plans_cost)
        print(recommended_coverage_split)

    return render_template(
        "recommendation.html",
        family=family,
        plans=plans)
# [END recommendation]

def expected_utilization(data, age, gender):
    g = 'Child'
    if gender == 'male':
        g = 'M'
    elif gender == 'female':
        g = 'F'
    utilization = {'low':0, 'med':0, 'high':0}
    for item in data:
        if (g == 'Child' and item[1] == 'Child') or (item[0] == age and item[1] == g):
            utilization['low'] = 0 if item[2] == '.' else float(item[2])
            utilization['med'] = 0 if item[3] == '.' else float(item[3])
            utilization['high'] = 0 if item[4] == '.' else float(item[4])
            break
    return utilization

def get_annual_premiums(plan, coverage_types):
    premiums = {}
    for coverage_type in coverage_types:
        premium = 0
        if coverage_type == 'ee':
            premium = float(plan['ee_cost'])
        elif coverage_type == 'ee_spouse':
            premium = float(plan['ee_spouse_cost'])
        elif coverage_type == 'ee_children':
            premium = float(plan['ee_children_cost'])
        elif coverage_type == 'ee_family':
            premium = float(plan['ee_family_cost'])
        cycle = plan['ee_cost_cycle']
        if cycle == "Weekly":
            premium *= 52
        elif cycle == "Bi-Weekly (Twice a month)":
            premium *= 26
        if cycle == "Monthly":
            premium *= 12
        if cycle == "Semi-Annually":
            premium *= 2
        premiums[coverage_type] = premium
    return premiums

def get_deductibles(plan, coverage_types):
    deductibles = {}
    for coverage_type in coverage_types:
        deductible = 0
        if coverage_type == 'ee':
            deductible = float(plan['ee_deductible'])
        elif coverage_type == 'ee_spouse':
            deductible = float(plan['ee_spouse_deductible'])
        elif coverage_type == 'ee_children':
            deductible = float(plan['ee_children_deductible'])
        elif coverage_type == 'ee_family':
            deductible = float(plan['ee_family_deductible'])
        deductibles[coverage_type] = deductible
    return deductibles

def get_oop(plan, coverage_types):
    oops = {}
    for coverage_type in coverage_types:
        oop = 0
        if coverage_type == 'ee':
            oop = float(plan['ee_oop_max'])
        elif coverage_type == 'ee_spouse':
            oop = float(plan['ee_spouse_oop_max'])
        elif coverage_type == 'ee_children':
            oop = float(plan['ee_children_oop_max'])
        elif coverage_type == 'ee_family':
            oop = float(plan['ee_family_oop_max'])
        oops[coverage_type] = oop
    return oops

def get_er_fundings(plan, coverage_types):
    er_fundings = {}
    for coverage_type in coverage_types:
        er_funding = 0
        if coverage_type == 'ee':
            er_funding = float(plan['ee_er_funding'])
        elif coverage_type == 'ee_spouse':
            er_funding = float(plan['ee_spouse_er_funding'])
        elif coverage_type == 'ee_children':
            er_funding = float(plan['ee_children_er_funding'])
        elif coverage_type == 'ee_family':
            er_funding = float(plan['ee_family_er_funding'])
        er_fundings[coverage_type] = er_funding
    return er_fundings

def get_wellness_benefits(plan, coverage_types):
    wellness_benefitss = {}
    for coverage_type in coverage_types:
        wellness_benefits = 0
        if coverage_type == 'ee':
            wellness_benefits = float(plan['ee_wellness_benefits'])
        elif coverage_type == 'ee_spouse':
            wellness_benefits = float(plan['ee_spouse_wellness_benefits'])
        elif coverage_type == 'ee_children':
            wellness_benefits = float(plan['ee_children_wellness_benefits'])
        elif coverage_type == 'ee_family':
            wellness_benefits = float(plan['ee_family_wellness_benefits'])
        wellness_benefitss[coverage_type] = wellness_benefits
    return wellness_benefitss

# @crud.route('/<id>/edit', methods=['GET', 'POST'])
# def edit(id):
#     book = get_model().read(id)

#     if request.method == 'POST':
#         data = request.form.to_dict(flat=True)

#         book = get_model().update(data, id)

#         return redirect(url_for('.view', id=book['id']))

#     return render_template("form.html", action="Edit", book=book)


# @crud.route('/<id>/delete')
# def delete(id):
#     get_model().delete(id)
#     return redirect(url_for('.list'))