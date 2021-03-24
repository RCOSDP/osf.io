# -*- coding: utf-8 -*-
from flask import request
import logging
import requests
import json
import time
import pytz
from django.utils.timezone import make_aware
from datetime import date, datetime, timedelta
from addons.integromat import SHORT_NAME, FULL_NAME
from django.db import transaction
from django.db.models import Min
from addons.base import generic_views
from framework.auth.decorators import must_be_logged_in
from addons.integromat.serializer import IntegromatSerializer
from osf.models import ExternalAccount
from django.core.exceptions import ValidationError
from framework.exceptions import HTTPError
from rest_framework import status as http_status
from osf.utils.tokens import process_token_or_pass
from website.util import api_url_for
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_be_addon_authorizer,
    must_have_permission,
)
from website.ember_osf_web.views import use_ember_app
from addons.integromat import settings

from addons.integromat import models
from osf.models.rdm_integromat import RdmWebMeetingApps, RdmWorkflows
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from framework.auth.core import Auth

logger = logging.getLogger(__name__)

integromat_account_list = generic_views.account_list(
    SHORT_NAME,
    IntegromatSerializer
)

integromat_get_config = generic_views.get_config(
    SHORT_NAME,
    IntegromatSerializer
)

integromat_import_auth = generic_views.import_auth(
    SHORT_NAME,
    IntegromatSerializer
)

integromat_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

integromat_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    IntegromatSerializer,
    ''
)

@must_be_logged_in
def integromat_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""

    try:
        access_token = request.json.get('integromat_api_token')
        webhook_url = request.json.get('integromat_webhook_url')

    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    #integromat auth
    integromatUserInfo = authIntegromat(access_token, settings.H_SDK_VERSION)

    if not integromatUserInfo:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    else:
        integromat_userid = integromatUserInfo['id']
        integromat_username = integromatUserInfo['name']

    user = auth.user

    try:
        account = ExternalAccount(
            provider=SHORT_NAME,
            provider_name=FULL_NAME,
            display_name=integromat_username,
            oauth_key=access_token,
            provider_id=integromat_userid,
            webhook_url=webhook_url,
        )
        account.save()
    except ValidationError:
        # ... or get the old one
        account = ExternalAccount.objects.get(
            provider='integromat', provider_id=integromat_userid
        )
        if account.oauth_key != access_token:
            account.oauth_key = access_token
            account.save()

        if account.webhook_url != webhook_url:
            account.webhook_url = webhook_url
            account.save()

    if not user.external_accounts.filter(id=account.id).exists():

        user.external_accounts.add(account)

    user.get_or_add_addon('integromat', auth=auth)

    user.save()

    return {}

def authIntegromat(access_token, hSdkVersion):

    message = ''
    token = 'Token ' + access_token
    payload = {}
    headers = {
        'Authorization': token,
        'x-imt-apps-sdk-version': hSdkVersion
    }

    response = requests.request('GET', settings.INTEGROMAT_API_WHOAMI, headers=headers, data=payload)
    status_code = response.status_code
    userInfo = response.json()

    if status_code != 200:

        if userInfo.viewkeys() >= {'message'}:
            message = userInfo['message']

        logger.info('Failed to authenticate Integromat account' + '[' + str(status_code) + ']' + ':' + message)

        userInfo.clear()

    return userInfo

# ember: ここから
@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def project_integromat(**kwargs):
    return use_ember_app()

@must_be_logged_in
@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def integromat_get_config_ember(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    user = auth.user

    qsUserGuid = user._prefetched_objects_cache['guids'].only()
    userGuidSerializer = serializers.serialize('json', qsUserGuid, ensure_ascii=False)
    userGuidJson = json.loads(userGuidSerializer)
    userGuid = userGuidJson[0]['fields']['_id']
    microsoftTeamsOrganizerId = ''

    try:
        organizer = models.Attendees.objects.get(node_settings_id=addon.id, user_guid=userGuid)
        microsoftTeamsOrganizerId = organizer.microsoft_teams_user_object
    except ObjectDoesNotExist:
        logger.info('object des not exist1')
        pass

    appMicrosoftTeams = RdmWebMeetingApps.objects.get(app_name='MicrosoftTeams')

    workflows = RdmWorkflows.objects.all()
    microsoftTeamsMeetings = models.AllMeetingInformation.objects.filter(node_settings_id=addon.id, app_id=appMicrosoftTeams.id).order_by('start_datetime').reverse()
    upcomingMicrosoftTeamsMeetings = models.AllMeetingInformation.objects.filter(node_settings_id=addon.id, app_id=appMicrosoftTeams.id, start_datetime__gte=datetime.today()).order_by('start_datetime')
    previousMicrosoftTeamsMeetings = models.AllMeetingInformation.objects.filter(node_settings_id=addon.id, app_id=appMicrosoftTeams.id, start_datetime__lt=datetime.today()).order_by('start_datetime').reverse()
    microsoftTeamsAttendees = models.Attendees.objects.filter(node_settings_id=addon.id)

    logger.info('datetime.today:' + str(datetime.today()))
    logger.info('datetime.now:' + str(datetime.now()))
    logger.info('datetime.now aware:' + str(make_aware(datetime.now())))

    microsoftTeamsAttendeesJson = serializers.serialize('json', microsoftTeamsAttendees, ensure_ascii=False)
    workflowsJson = serializers.serialize('json', workflows, ensure_ascii=False)
    microsoftTeamsMeetingsJson = serializers.serialize('json', microsoftTeamsMeetings, ensure_ascii=False)
    upcomingMicrosoftTeamsMeetingsJson = serializers.serialize('json', upcomingMicrosoftTeamsMeetings, ensure_ascii=False)
    previousMicrosoftTeamsMeetingsJson = serializers.serialize('json', previousMicrosoftTeamsMeetings, ensure_ascii=False)

    return {'data': {'id': node._id, 'type': 'integromat-config',
                     'attributes': {
                         'node_settings_id': addon._id, 
                         'webhook_url': addon.external_account.webhook_url,
                         'microsoft_teams_meetings': microsoftTeamsMeetingsJson,
                         'upcoming_microsoft_teams_meetings': upcomingMicrosoftTeamsMeetingsJson,
                         'previous_microsoft_teams_meetings': previousMicrosoftTeamsMeetingsJson,
                         'microsoft_teams_attendees': microsoftTeamsAttendeesJson,
                         'workflows': workflowsJson,
                         'app_name_microsoft_teams': settings.MICROSOFT_TEAMS,
                         'microsoft_teams_organizer_id': microsoftTeamsOrganizerId
                     }}}

#api for Integromat action
def integromat_api_call(*args, **kwargs):

    logger.info('integromat called integromat_api_call.GRDM-Integromat connection test scceeeded.:')
    logger.info('kwargs' + str(dict(kwargs)))
    logger.info('args' + str(dict(args)))
    logger.info('headers' + str(dict(request.headers)))
    auth = Auth.from_kwargs(request.args.to_dict(), kwargs)
    logger.info('auth:' + str(auth))
    logger.info('auth:' + str(auth.user))

    return {'user': str(auth.user)}

@must_be_logged_in
def integromat_create_meeting_info(**kwargs):

    logger.info('integromat called integromat_create_meeting_info')
    logger.info('headers' + str(dict(request.headers)))
    auth = Auth.from_kwargs(request.args.to_dict(), kwargs)
    logger.info('auth:' + str(auth))

    nodeId = request.get_json().get('nodeId')
    appName = request.get_json().get('meetingAppName')
    subject = request.get_json().get('subject')
    organizer = request.get_json().get('organizer')
    attendees = request.get_json().get('attendees')
    startDatetime = request.get_json().get('startDate')
    endDatetime = request.get_json().get('endDate')
    location = request.get_json().get('location')
    content = request.get_json().get('content')
    joinUrl = request.get_json().get('microsoftTeamsJoinUrl')
    meetingId = request.get_json().get('microsoftTeamsMeetingId')

    try:
        node = models.NodeSettings.objects.get(_id=nodeId)
    except:
        logger.error('nodesettings _id is invalid.')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    try:
        webApp = RdmWebMeetingApps.objects.get(app_name=appName)
    except:
        logger.error('web app name is invalid.')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():

        meetingInfo = models.AllMeetingInformation(
            subject=subject,
            organizer=organizer,
            start_datetime=startDatetime,
            end_datetime=endDatetime,
            location=location,
            content=content,
            join_url=joinUrl,
            meetingid=meetingId,
            app_id=webApp.id,
            node_settings_id=node.id,
        )
        meetingInfo.save()

        attendeeIds = []

        for attendeeMail in attendees:

            qsAttendee = models.Attendees.objects.get(node_settings_id=node.id, microsoft_teams_mail=attendeeMail)
            attendeeId = qsAttendee.id
            attendeeIds.append(attendeeId)

        meetingInfo.attendees = attendeeIds
        meetingInfo.save()

    return {}

def integromat_update_meeting_info(**kwargs):

    nodeId = request.get_json().get('nodeId')
    appName = request.get_json().get('meetingAppName')
    subject = request.get_json().get('subject')
    attendees = request.get_json().get('attendees')
    startDatetime = request.get_json().get('startDate')
    endDatetime = request.get_json().get('endDate')
    location = request.get_json().get('location')
    content = request.get_json().get('content')
    meetingId = request.get_json().get('microsoftTeamsMeetingId')
    logger.info('meetingId::' + str(meetingId))
    qsUpdateMeetingInfo = models.AllMeetingInformation.objects.get(meetingid=meetingId)

    qsUpdateMeetingInfo.subject = subject
    qsUpdateMeetingInfo.start_datetime = startDatetime
    qsUpdateMeetingInfo.end_datetime = endDatetime
    qsUpdateMeetingInfo.location = location
    qsUpdateMeetingInfo.content = content

    try:
        node = models.NodeSettings.objects.get(_id=nodeId)
    except:
        logger.error('nodesettings _id is invalid.')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    attendeeIds = []

    for attendeeMail in attendees:

        qsAttendee = models.Attendees.objects.get(node_settings_id=node.id, microsoft_teams_mail=attendeeMail)
        attendeeId = qsAttendee.id
        attendeeIds.append(attendeeId)

    qsUpdateMeetingInfo.attendees = attendeeIds

    qsUpdateMeetingInfo.save()

    return {}

def integromat_delete_meeting_info(**kwargs):

    nodeId = request.get_json().get('nodeId')
    appName = request.get_json().get('meetingAppName')
    meetingId = request.get_json().get('microsoftTeamsMeetingId')
    logger.info('meetingId:' + str(meetingId))

    qsDeleteMeeting = models.AllMeetingInformation.objects.get(meetingid=meetingId)
    qsDeleteMeeting.delete()

    return {}


@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def integromat_add_microsoft_teams_user(**kwargs):

    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)

    userGuid = request.get_json().get('user_guid')
    microsoftTeamsUserObject = request.get_json().get('microsoft_teams_user_object')
    microsoftTeamsMail = request.get_json().get('microsoft_teams_mail')

    nodeSettings = models.NodeSettings.objects.get(_id=addon._id)
    nodeNum = nodeSettings.id
    if models.Attendees.objects.filter(node_settings_id=nodeNum, user_guid=userGuid).exists():
        logger.info('user_guid duplicate.')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    if models.Attendees.objects.filter(node_settings_id=nodeNum, microsoft_teams_user_object=microsoftTeamsUserObject).exists():
        attendee = models.Attendees.objects.get(node_settings_id=nodeNum, microsoft_teams_user_object=microsoftTeamsUserObject)
        logger.info('Microsoft User Object ID duplicate with ' + attendee.user_guid)
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    if models.Attendees.objects.filter(node_settings_id=nodeNum, microsoft_teams_mail=microsoftTeamsMail).exists():
        attendee = models.Attendees.objects.get(node_settings_id=nodeNum, microsoft_teams_mail=microsoftTeamsMail)
        logger.info('Microsoft Teams Sign-in Address duplicate with ' + attendee.user_guid)
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    microsoftTeamsUserInfo = models.Attendees(
        user_guid=userGuid,
        microsoft_teams_user_object=microsoftTeamsUserObject,
        microsoft_teams_mail=microsoftTeamsMail,
        node_settings=nodeSettings,
    )

    microsoftTeamsUserInfo.save()

    return {}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def integromat_delete_microsoft_teams_user(**kwargs):

    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)

    userGuid = request.get_json().get('user_guid')

    nodeSettings = models.NodeSettings.objects.get(_id=addon._id)
    nodeNum = nodeSettings.id
    qsMicrosoftTeamsUserInfo = models.Attendees.objects.filter(node_settings_id=nodeNum, user_guid=userGuid)

    qsMicrosoftTeamsUserInfo.delete()

    return {}

def integromat_start_scenario(**kwargs):

    logger.info('integromat_start_scenario start')
    nodeId = request.json['nodeId']
    timestamp = request.json['timestamp']
    webhook_url = request.json['webhook_url']

    integromatMsg = ''
    node = models.NodeSettings.objects.get(_id=nodeId)

    logger.info('request:' + str(request))
    logger.info('request:' + str(request.get_data()))
    logger.info('request.json:' + str(request.json))

    response = requests.post(webhook_url, data=request.get_data(), headers={'Content-Type': 'application/json'})

    for i in range(0, 10):
        time.sleep(1)
        logger.info(str(i))
        try:
            wem = models.workflowExecutionMessages.objects.filter(node_settings_id=node.id, timestamp=timestamp, notified=False).earliest('created')
            logger.info('wem:' + str(wem))
            integromatMsg = wem.integromat_msg
            wem.notified = True
            wem.save()
            break
        except ObjectDoesNotExist:
            logger.info('object des not exist1')
            pass

    if not integromatMsg:
        integromatMsg = 'integromat.error.didNotStart'

    logger.info('integromatMsg:' + integromatMsg)

    logger.info('integromat_start_scenario end')

    return {'nodeId': nodeId,
            'integromatMsg': integromatMsg,
            'timestamp': timestamp
            }

def integromat_req_next_msg(**kwargs):

    logger.info('integromat_req_next_msg start')

    time.sleep(1)

    nodeId = request.json['nodeId']
    timestamp = request.json['timestamp']
    notify = False

    integromatMsg = ''
    node = models.NodeSettings.objects.get(_id=nodeId)

    try:
        wem = models.workflowExecutionMessages.objects.filter(node_settings_id=node.id, timestamp=timestamp, notified=False).earliest('created')
        logger.info('wem:' + str(wem))
        integromatMsg = wem.integromat_msg
        wem.notified = True
        wem.save()
    except ObjectDoesNotExist:
        logger.info('object des not exist2')
        pass

    if integromatMsg:
        notify = True

    logger.info('integromat_req_next_msg end')

    return {'nodeId': nodeId,
            'integromatMsg': integromatMsg,
            'timestamp': timestamp,
            'notify': notify,
            }

def integromat_info_msg(**kwargs):

    logger.info('integromat_info_msg start')
    logger.info('integromat_info_msg 1')
    msg = request.json['notifyType']
    nodeId = request.json['nodeId']
    timestamp = request.json['timestamp']

    node = models.NodeSettings.objects.get(_id=nodeId)

    wem = models.workflowExecutionMessages(
        integromat_msg=msg,
        timestamp=timestamp,
        node_settings_id=node.id,
    )
    wem.save()

    logger.info('integromat_info_msg end')

    return {}

def integromat_error_msg(**kwargs):

    logger.info('integromat_error_msg start')

    msg = request.json['notifyType']
    nodeId = request.json['nodeId']
    timestamp = request.json['timestamp']

    node = models.NodeSettings.objects.get(_id=nodeId)

    wem = models.workflowExecutionMessages(
        integromat_msg=msg,
        timestamp=timestamp,
        node_settings_id=node.id,
    )
    wem.save()

    logger.info('integromat_error_msg end')

    return {}

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def integromat_get_meetings(**kwargs):

    logger.info('integromat_get_meetings start')

    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)

    


    amiToday = models.AllMeetingInformation.objects.filter(node_settings_id=addon.id, start_datetime__date=date.today()).order_by('start_datetime')
    amiTomorrow = models.AllMeetingInformation.objects.filter(node_settings_id=addon.id, start_datetime__date=date.today() + timedelta(days=1)).order_by('start_datetime')
    logger.info('today:' + str(date.today()))
    amiTodayJson = serializers.serialize('json', amiToday, ensure_ascii=False)
    amiTomorrowJson = serializers.serialize('json', amiTomorrow, ensure_ascii=False)
    amiTodayDict = json.loads(amiTodayJson)
    amiTomorrowDict = json.loads(amiTomorrowJson)
    logger.info('integromat_get_meetings end')

    return {'todaysMeetings': amiTodayDict,
            'tomorrowsMeetings': amiTomorrowDict,
            }
