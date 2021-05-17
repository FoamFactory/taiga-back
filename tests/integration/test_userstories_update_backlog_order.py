# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

import uuid
import csv
import pytz

from datetime import datetime, timedelta
from urllib.parse import quote

from unittest import mock
from django.urls import reverse

from taiga.base.utils import json
from taiga.permissions.choices import MEMBERS_PERMISSIONS, ANON_PERMISSIONS
from taiga.projects.occ import OCCResourceMixin
from taiga.projects.userstories import services, models

from .. import factories as f

import pytest
pytestmark = pytest.mark.django_db(transaction=True)


##############################
## Move to no swimlane
##############################


def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_to_the_begining(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  |       |         |   MOVE: us2, us3   |    us2  |       |
    #   us2  |       |         |   TO: no-milestone |    us3  |       |
    #   us3  |       |         |   AFTER: bigining  |    us1  |       |
    #        |       |         |                    |         |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us2 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us3 = f.create_userstory(project=project, backlog_order=3, milestone=None)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": None,
        "bulk_userstories": [us2.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us2.id,
        us3.id,
        us1.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    assert us2.backlog_order == 1
    assert us2.milestone_id == None
    assert us3.backlog_order == 2
    assert us3.milestone_id == None
    assert us1.backlog_order == 3
    assert us1.milestone_id == None


def test_api_update_orders_in_bulk_succeeds_moved_in_the_backlog_to_the_middle(client):
    #
    #   BLG  |  ML1  |  ML2    |                    |    BLG  |  ML1  |  ML2
    # -------|-------|-------  |                    |  -------|-------|-------
    #   us1  |  us2  |         |   MOVE: us2, us3   |    us4  | us2   |
    #   us4  |  us3  |         |   TO: no-milestone |    us1  |       |
    #   us5  |       |         |   AFTER: bigining  |    us3  |       |
    #        |       |         |                    |    us5  |       |
    #        |       |         |                    |         |       |

    project = f.create_project()
    f.MembershipFactory.create(project=project, user=project.owner, is_admin=True)
    ml1 = f.MilestoneFactory.create(project=project)
    ml2 = f.MilestoneFactory.create(project=project)
    us1 = f.create_userstory(project=project, backlog_order=1, milestone=None)
    us4 = f.create_userstory(project=project, backlog_order=2, milestone=None)
    us5 = f.create_userstory(project=project, backlog_order=3, milestone=None)
    us2 = f.create_userstory(project=project, sprint_order=1, milestone=ml1)
    us3 = f.create_userstory(project=project, sprint_order=2, milestone=ml1)

    url = reverse("userstories-bulk-update-backlog-order")

    data = {
        "project_id": project.id,
        "after_userstory_id": None,
        "after_userstory_id": us4.id,
        "bulk_userstories": [us1.id,
                             us3.id]
    }

    client.login(project.owner)

    response = client.json.post(url, json.dumps(data))
    assert response.status_code == 200, response.data

    updated_ids = [
        us1.id,
        us3.id,
        us5.id,
    ]
    res = (project.user_stories.filter(id__in=updated_ids)
                               .values("id", "milestone", "backlog_order")
                               .order_by("backlog_order", "id"))
    assert response.json() == list(res)

    us1.refresh_from_db()
    us2.refresh_from_db()
    us3.refresh_from_db()
    us4.refresh_from_db()
    us5.refresh_from_db()
    assert us4.backlog_order == 2
    assert us4.milestone_id == None
    assert us1.backlog_order == 3
    assert us1.milestone_id == None
    assert us3.backlog_order == 4
    assert us3.milestone_id == None
    assert us5.backlog_order == 5
    assert us5.milestone_id == None
    assert us2.sprint_order == 1
    assert us2.milestone_id == ml1.id

