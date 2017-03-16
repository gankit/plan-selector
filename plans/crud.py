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


crud = Blueprint('crud', __name__)

# [START start]
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
    print(family)
    return render_template("start.html", family=family)

# [END start]

# [START plans]
@crud.route("/plans")
def plans():
    family_id = request.args.get('family', None)
    if family_id:
        family_id = family_id.encode('utf-8')
    plans, family = get_model().plans(family_id=family_id)
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

    plan_id = request.args.get('plan', None)
    if plan_id:
        plan_id = plan_id.encode('utf-8')
    plan = get_model().item('Plan', id=plan_id)

    return render_template("addplan.html", family=family, plan=plan)
# [END addplan]


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
