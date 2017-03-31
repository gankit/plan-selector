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
import requests

crud = Blueprint('crud', __name__)
# [START index]
@crud.route("/", methods=['GET', 'POST'])
def index():
    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')

    family = get_model().item('Family', id=family_id)

    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        print(data)
        print(family)
        if family:
            return redirect(url_for('.start', family=family_id))
        else:
            #create a family
            family = get_model().update('Family', data=data, id=None)
            return redirect(url_for('.start', family=family['id']))

    else:    
        return render_template("index.html", family=family)
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
            return redirect(url_for('.plans', family=family['id']))

    family_id = request.args.get('family', None)


    if family_id:
        family_id = family_id.encode('utf-8')
    else:
        return redirect(url_for('.index'))

    family = get_model().item('Family', id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.index'))
    
    if family:
        send_welcome_email(family)
    
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

    # When family information is incomplete
    if not ('me_age' in family) and family_id:
        return redirect(url_for('.start', family=family_id))

    print(family)

    display_coverage_type = 'ee'
    display_coverage_type_text = 'yourself'
    if family['marital_status'] == 'married':
        display_coverage_type = 'ee_spouse'
        display_coverage_type_text = 'you and your spouse'
    if int(family['children']) > 0 :
        display_coverage_type = 'ee_children'
        display_coverage_type_text = 'you and your children'
    if family['marital_status'] == 'married' and int(family['children']) > 0:
        display_coverage_type = 'ee_family'
        display_coverage_type_text = 'you and your family'

    plans_display_data = []
    for plan in plans:
        new_plan = {}
        new_plan['plan_name'] = plan['plan_name']
        new_plan['insurer_name'] = plan['insurer_name']
        new_plan['employer_name'] = plan['employer_name']
        plan_id = plan.key.id
        new_plan['key'] = {'id':plan_id}
        new_plan['cost_cycle'] = plan['ee_cost_cycle']
        new_plan['hsa_qualified'] = plan['hsa_qualified']
        new_plan['oon_coverage_included'] = plan['oon_coverage_included']
        new_plan['annual_premium'] = get_annual_premiums(plan, [display_coverage_type])[display_coverage_type]
        new_plan['deductible'] = get_deductibles(plan, [display_coverage_type])[display_coverage_type]
        new_plan['oop_max'] = get_oop(plan, [display_coverage_type])[display_coverage_type]
        new_plan['er_funding'] = get_er_fundings(plan, [display_coverage_type])[display_coverage_type]
        plans_display_data.append(new_plan)
    plans_display_data.sort(key=lambda x:float(x['annual_premium']));

    return render_template(
        "plans.html",
        family=family,
        plans=plans,
        display_coverage_type=display_coverage_type,
        display_coverage_type_text=display_coverage_type_text,
        plans_display_data=plans_display_data)
# [END plans]


@crud.route('/<id>')
def view_plan(id):
    try:
        plan = get_model().item('Plan', id=id)
        return redirect(url_for('.addplan', family=plan['family_id'], plan=id))
    except:
        family_id = request.args.get('family', None)
        if family_id:
            family_id = family_id.encode('utf-8')

            family = get_model().item('Family', id=family_id)

            # Edge case when an incorrect family_id is supplied
            if not family:
                return redirect(url_for('.start'))

            # When family information is incomplete
            if not 'me_age' in family:
                return redirect(url_for('.start', family=family_id))
        return redirect(url_for('.start'))


# [START addplan]
@crud.route('/addplan', methods=['GET', 'POST'])
def addplan():
    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')
    family = get_model().item('Family', id=family_id)

    # Edge case when an incorrect family_id is supplied
    if not family and family_id:
        return redirect(url_for('.start'))

    # When family information is incomplete
    if not ('me_age' in family) and family_id:
        return redirect(url_for('.start', family=family_id))

    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        plan_id = None
        if 'plan_id' in data:
            plan_id = data['plan_id']
        plan = get_model().update('Plan', data=data, id=plan_id)

        if 'save' in request.form:
            return redirect(url_for('.addplan', family=plan['family_id'], plan=plan['id']))
        elif 'save_and_continue_later' in request.form:
            send_plan_link_email(family, plan)
            return redirect(url_for('.addplan', family=plan['family_id'], plan=plan['id']))
        else:
            return redirect(url_for('.plans', family=plan['family_id']))

    plan_id = request.args.get('plan', None)
    if plan_id:
        plan_id = plan_id.encode('utf-8')
    plan = get_model().item('Plan', id=plan_id)

    medicaid_plans = ['Medicaid', 'Individual exchange', 'VA / Tricare']
    if int(family['me_age']) >= 65 or ('spouse_age' in family and int(family['spouse_age']) >= 65):
        medicaid_plans.append('Medicare / Medicare Advantage')

    # Edge case when an incorrect plan_id is supplied
    if not plan and plan_id:
        return redirect(url_for('.plans', family=family_id))

    return render_template("addplan.html", family=family, plan=plan, medicaid_plans=medicaid_plans)
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

    # When family information is incomplete
    if not ('me_age' in family) and family_id:
        return redirect(url_for('.start', family=family_id))

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
    # print(coverage_types)
    with urllib.request.urlopen(url) as response:
        obj = response.read().decode('utf8')
        data = json.loads(obj)
        utilization_dataset = data['values']
        me_employer = None
        spouse_employer = None
        # print(comparison_dataset)
        price = {}
        for plan in plans:
            plan_id = str(plan.key.id)
            if plan_id not in price:
                price[plan_id] = {}
            premiums = get_annual_premiums(plan=plan, coverage_types=coverage_types)
            deductibles = get_deductibles(plan=plan, coverage_types=coverage_types)
            oops = get_oop(plan=plan, coverage_types=coverage_types)
            er_fundings = get_er_fundings(plan=plan, coverage_types=coverage_types)
            wellness_benefits = get_wellness_benefits(plan=plan, coverage_types=coverage_types)
            for coverage_type in coverage_types:
                price[plan_id][coverage_type] = premiums[coverage_type] - er_fundings[coverage_type] - wellness_benefits[coverage_type]
        # print(price)
        # print("---------------------")
        for plan in plans:
            plan_id = str(plan.key.id)
            if plan_id not in price:
                price[plan_id] = {}
            deductibles = get_deductibles(plan=plan, coverage_types=coverage_types)
            oops = get_oop(plan=plan, coverage_types=coverage_types)
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
                    if plan['plan_source'] == 'employer':
                        age = str(family['me_age'])
                        gender = str(family['me_gender'])
                        utilization = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    elif plan['plan_source'] == 'spouse_employer':
                        age = str(family['spouse_age'])
                        gender = str(family['spouse_gender'])
                        utilization = expected_utilization(data=utilization_dataset, age=age, gender=gender)

                if coverage_type == 'ee_spouse':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization_1 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    age = str(family['spouse_age'])
                    gender = str(family['spouse_gender'])
                    utilization_2 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + utilization_2[util]
                if coverage_type == 'ee_children':
                    utilization_1 = {}
                    if plan['plan_source'] == 'employer':
                        age = str(family['me_age'])
                        gender = str(family['me_gender'])
                        utilization_1 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    elif plan['plan_source'] == 'spouse_employer':
                        age = str(family['spouse_age'])
                        gender = str(family['spouse_gender'])
                        utilization_1 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    utilization_2 = expected_utilization(data=utilization_dataset, age='Child', gender='Child')
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + int(family['children'])*utilization_2[util]
                if coverage_type == 'ee_family':
                    age = str(family['me_age'])
                    gender = str(family['me_gender'])
                    utilization_1 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    utilization_2 = expected_utilization(data=utilization_dataset, age='Child', gender='Child')
                    age = str(family['spouse_age'])
                    gender = str(family['spouse_gender'])
                    utilization_3 = expected_utilization(data=utilization_dataset, age=age, gender=gender)
                    for util in utilization_1:
                        utilization[util] = utilization_1[util] + int(family['children'])*utilization_2[util] + utilization_3[util]
                # print(utilization)
                comparison_table[employer][coverage_type][plan_id] = utilization
                for util in utilization:
                    cost = 0
                    eu = utilization[util]
                    xyz = 0
                    oop = oops[coverage_type]
                    deductible = deductibles[coverage_type]
                    if eu < deductible:
                        xyz = eu
                    else:
                        xyz = min(deductible + 0.2 * (eu - deductible), oop)
                    cost = price[plan_id][coverage_type] + xyz
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
                    r_plans = {}
                    r_costs = {}
                    for employer in split_type:        
                        coverage = split_type[employer]
                        plan_id = best_plans[util][coverage][employer]
                        r_plans[employer] = plan_id
                        plan_cost = comparison_table[employer][coverage][plan_id][util]
                        cost += plan_cost
                        r_costs[employer] = plan_cost
                    if cost < min_cost:
                        min_cost = cost
                        recommended_plans[util] = r_plans
                        recommended_plans_cost[util] = r_costs
                        recommended_coverage_split[util] = split_type

    human_readable = {}
    for util in recommended_coverage_split:
        split = recommended_coverage_split[util]
        r_plans = recommended_plans[util]
        r_cost = recommended_plans_cost[util]
        overall_text = ""
        recs = []
        overall_cost = 0
        option_id = ''
        for employer in split:
            is_spouse = False
            if employer == spouse_employer:
                is_spouse = True
            split_type = split[employer]
            plan_id = r_plans[employer]
            option_id += employer+":"+split_type+":"+plan_id
            cost = r_cost[employer]
            plan = get_plan_by_id(plans=plans, plan_id=plan_id)
            text = capitalize_first(get_human_readable_split(split_type, is_spouse) + " should be on the plan " + plan['plan_name'] +" offered by "+employer)
            overall_text += "Plan for "+ get_human_readable_split(split_type, is_spouse) + " - " + plan['plan_name'] +" offered by "+ employer +" costing you $"+"{0:.2f}".format(cost)+". "
            rec = {}
            rec['text'] = text
            rec['plan'] = plan
            rec['cost'] = cost
            rec['price'] = price[plan_id][split_type]
            recs.append(rec)
            overall_cost += cost
        human_readable[util] = {}
        human_readable[util]['option_id'] = option_id
        human_readable[util]['text'] = overall_text
        human_readable[util]['recs'] = recs
        human_readable[util]['cost'] = overall_cost

    options = {'low':[], 'med':[], 'high':[]}
    if me_employer is not None and spouse_employer is None:
        top_coverage = coverage_types[len(coverage_types) - 1]
        for util in options:
            for plan in plans:
                employer = plan['employer_name']
                plan_id = str(plan.key.id)
                option_id = employer+':'+top_coverage+":"+plan_id;
                is_spouse = False
                if employer == spouse_employer:
                    is_spouse = True
                text = capitalize_first(get_human_readable_split(top_coverage, is_spouse) + " on " +plan['insurer_name'] + " - " + plan['plan_name'] +" offered by " + plan['employer_name'])
                cost = comparison_table[employer][top_coverage][plan_id][util]
                rec = {}
                rec['option_id'] = option_id
                if option_id == human_readable[util]['option_id']:
                    rec['recommended'] = 'yes'

                rec['text'] = text
                rec['cost'] = cost
                rec['savings'] = cost - human_readable[util]['cost']
                rec['price'] = price[plan_id][top_coverage]
                options[util].append(rec)
    elif me_employer is not None and spouse_employer is not None:
        if int(family['children']) > 0 :
            coverage_split_types = [{me_employer:'ee_family'}, {me_employer:'ee', spouse_employer:'ee_children'}, {me_employer:'ee_children', spouse_employer:'ee'}, {spouse_employer:'ee_family'}]
        else:
            coverage_split_types = [{me_employer:'ee_spouse'}, {me_employer:'ee', spouse_employer:'ee'}, {spouse_employer:'ee_spouse'}]
        for util in options:
            for split_type in coverage_split_types:
                text = ''
                cost = 0
                p = 0
                option_id = '';
                for employer in split_type:
                    coverage_type = split_type[employer]
                    plan_id = best_plans[util][coverage_type][employer]
                    option_id += employer+":"+coverage_type+":"+plan_id
                    plan = get_plan_by_id(plans, plan_id)
                    is_spouse = False
                    if employer == spouse_employer:
                        is_spouse = True

                    text += capitalize_first(get_human_readable_split(coverage_type, is_spouse) + " on " + plan['insurer_name'] + " - " + plan['plan_name'] +" offered by " + plan['employer_name'] + ". ")
                    cost += comparison_table[employer][coverage_type][plan_id][util]
                    p += price[plan_id][coverage_type]
                rec = {}
                rec['option_id'] = option_id
                if option_id == human_readable[util]['option_id']:
                    rec['recommended'] = 'yes'
                rec['text'] = text
                rec['cost'] = cost
                rec['savings'] = cost - human_readable[util]['cost']
                rec['price'] = p
                options[util].append(rec)
    # print(options)
    # print(human_readable)
    # recommendation[text, plan, cost]
    # low_recomentation[text, cost, components=[recommendation]]
    send_recommendation_email(family)

    return render_template(
        "recommendation.html",
        family=family,
        plans=plans,
        recommendation=human_readable,
        options=options)
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

def get_premiums(plan, coverage_types):
    premiums = {}
    for coverage_type in coverage_types:
        premium = 0
        if coverage_type + '_cost' in plan:
            if coverage_type == 'ee':
                premium = float(plan['ee_cost'])
            elif coverage_type == 'ee_spouse':
                premium = float(plan['ee_spouse_cost'])
            elif coverage_type == 'ee_children':
                premium = float(plan['ee_children_cost'])
            elif coverage_type == 'ee_family':
                premium = float(plan['ee_family_cost'])
        premiums[coverage_type] = premium
    return premiums

def get_annual_premiums(plan, coverage_types):
    premiums = {}
    for coverage_type in coverage_types:
        premium = 0
        if coverage_type + '_cost' in plan:
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
        elif cycle == "Bi-Weekly (Once every two weeks)":
            premium *= 26
        elif cycle == "Bi-Monthly (Twice a month)":
            premium *= 24
        if cycle == "Monthly":
            premium *= 12
        premiums[coverage_type] = premium
    return premiums

def get_deductibles(plan, coverage_types):
    deductibles = {}
    for coverage_type in coverage_types:
        deductible = 0
        if coverage_type + '_deductible' in plan:
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
        if coverage_type + '_oop_max' in plan:
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
        if coverage_type + '_er_funding' in plan:
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
        if coverage_type + '_wellness_benefits' in plan:
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

def get_human_readable_split(coverage_type, is_spouse=False):
    if coverage_type == 'ee':
        if is_spouse:
            return "your spouse"
        else:
            return "you"
    elif coverage_type == 'ee_spouse':
        if is_spouse:
            return "you and your spouse"
        else:
            return "you and your spouse"
    elif coverage_type == 'ee_children':
        if is_spouse:
            return "your spouse and your children"
        else:
            return "you and your children"
    elif coverage_type == 'ee_family':
        if is_spouse:
            return "you and your family"
        else:
            return "you and your family"

def get_plan_by_id(plans, plan_id):
    for p in plans:
        if str(p.key.id) == plan_id:
            return p

def capitalize_first(text):
    return text[0].capitalize() + text[1:]

MAILGUN_DOMAIN_NAME = 'mail.plan.guide'
MAILGUN_API_KEY = 'key-ead29a6a186d7b7b472a39b2e7777597'
def send_welcome_email(family):
    subject = 'Welcome to Plan Guide'
    text = "Hey there! Welcome to Plan Guide, the smartest way to find a health plan optimized for your entire family."
    text += "\n\n"
    text += "You can always visit your personalized dashboard by clicking this link: http://plan.guide/plans/plans?family="+str(family.key.id)
    text += "\n\n"
    text += "Once you have all the information at hand, you will need ~20 mins to add all your plans and get a recommendation from our trusted algorithms."
    text += "\n\n"
    text += "Feel free to reach out if you have any questions or feedback for us."
    text += "\n\n"
    text += "Best,"
    text += "\n"
    text += "The Plan Guide Team"
    text += "\n"
    send_email(to=family['email'], subject=subject, text=text)

def send_recommendation_email(family):
    print(family)
    subject = 'Your personalized recommendation from Plan Guide'
    text = "Hello,"
    text += "\n\n"
    text += "Thank you for using Plan Guide, the smartest way to find a health plan optimized for your entire family."
    text += "\n\n"
    text += "Visit your personalized recommendations by clicking this link: http://plan.guide/plans/recommendation?family="+str(family.key.id)
    text += "\n\n"
    text += "If you like our site, please share it with your friends, family and the world :)"
    text += "\n\n"
    text += "Also, we would love to hear from you - any feedback (good or bad) makes us better."
    text += "\n\n"
    text += "Best,"
    text += "\n"
    text += "The Plan Guide Team"
    text += "\n"
    send_email(to=family['email'], subject=subject, text=text)

def send_plan_link_email(family, plan):
    subject = 'Plan Guide: Pick up where you left ...'
    text = "Hello,"
    text += "\n\n"
    text += "Thank you for using Plan Guide, the smartest way to find a health plan optimized for your entire family."
    text += "\n\n"
    text += "The plan you just entered is saved. You can update the plan via this link: http://plan.guide/plans/addplan?family="+str(family.key.id)+"&plan="+str(plan.key.id)
    text += "\n\n"
    text += "Visit your personalized dashboard by clicking this link: http://plan.guide/plans/plans?family="+str(family.key.id)
    text += "\n\n"
    text += "If you like our site, please share it with your friends, family and the world :)"
    text += "\n\n"
    text += "Best,"
    text += "\n"
    text += "The Plan Guide Team"
    text += "\n"
    send_email(to=family['email'], subject=subject, text=text)

def send_email(to, subject, text):
    try:
        url = 'https://api.mailgun.net/v3/{}/messages'.format(MAILGUN_DOMAIN_NAME)
        auth = ('api', MAILGUN_API_KEY)
        data = {
            'from': 'Plan Guide <admin@plan.guide>',
            'to': to,
            'subject': subject,
            'text': text
        }

        response = requests.post(url, auth=auth, data=data)
        response.raise_for_status()
    except:
        return
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