#!/usr/bin/env python2
# coding: utf-8

import os
import mimetypes
import json
import logging
import datetime
import pytz
from os.path import splitext, basename, abspath
from tzlocal import get_localzone

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient
from requests_toolbelt.multipart.encoder import MultipartEncoder

import utils

PEERTUBE_SECRETS_FILE = 'peertube_secret'
PEERTUBE_PRIVACY = {
    "public": 1,
    "unlisted": 2,
    "private": 3
}


def get_authenticated_service(secret):
    peertube_url = str(secret['peertube_url']).rstrip("/")

    oauth_client = LegacyApplicationClient(
        client_id=str(secret['client_id'])
    )
    try:
        oauth = OAuth2Session(client=oauth_client)
        oauth.fetch_token(
            token_url=str(peertube_url + '/api/v1/users/token'),
            # lower as peertube does not store uppercase for pseudo
            username=str(secret['username'].lower()),
            password=str(secret['password']),
            client_id=str(secret['client_id']),
            client_secret=str(secret['client_secret'])
        )
    except Exception as e:
        if hasattr(e, 'message'):
            logging.error("Peertube: Error: " + str(e.message))
            exit(1)
        else:
            logging.error("Peertube: Error: " + str(e))
            exit(1)
    return oauth


def get_default_playlist(user_info):
    return user_info['videoChannels'][0]['id']


def get_playlist_by_name(user_info, options):
    for playlist in user_info["videoChannels"]:
        if playlist['displayName'].encode('utf8') == str(options['playlist']):
            return playlist['id']


def create_playlist(oauth, url, options):
    template = ('Peertube: Playlist %s does not exist, creating it.')
    logging.info(template % (str(options['playlist'])))
    playlist_name = utils.cleanString(str(options['playlist']))
    # Peertube allows 20 chars max for playlist name
    playlist_name = playlist_name[:19]
    data = '{"name":"' + playlist_name +'", \
            "displayName":"' + str(options['playlist']) +'", \
            "description":null}'

    headers = {
        'Content-Type': "application/json"
    }
    try:
        response = oauth.post(url + "/api/v1/video-channels/",
                       data=data,
                       headers=headers)
    except Exception as e:
        if hasattr(e, 'message'):
            logging.error("Error: " + str(e.message))
        else:
            logging.error("Error: " + str(e))
    if response is not None:
        if response.status_code == 200:
            jresponse = response.json()
            jresponse = jresponse['videoChannel']
            return jresponse['id']
        if response.status_code == 409:
            logging.error('Peertube: Error: It seems there is a conflict with an existing playlist, please beware '
                          'Peertube internal name is compiled from 20 firsts characters of playlist name.'
                          ' Please check your playlist name an retry.')
            exit(1)
        else:
            logging.error(('Peertube: The upload failed with an unexpected response: '
                           '%s') % response)
            exit(1)


def upload_video(oauth, secret, options):

    def get_userinfo():
        str_response = oauth.get(url+"/api/v1/users/me").content.decode('utf-8')
        return json.loads(str_response)
        #return json.loads(oauth.get(url+"/api/v1/users/me").content)

    def get_file(path):
        mimetypes.init()
        return (basename(path), open(abspath(path), 'rb'),
                mimetypes.types_map[splitext(path)[1]])

    path = options['file']
    url = str(secret['peertube_url']).rstrip('/')
    user_info = get_userinfo()

    # We need to transform fields into tuple to deal with tags as
    # MultipartEncoder does not support list refer
    # https://github.com/requests/toolbelt/issues/190 and
    # https://github.com/requests/toolbelt/issues/205
    fields = [
        ("name", options['name'] or splitext(basename(options['file']))[0]),
        ("licence", "1"),
        ("description", " "),
        ("nsfw", "0"),
        ("videofile", get_file(path))
    ]


        # if no category, set default to 2 (Films)
    fields.append(("category", "2"))

    if options['language']:
        fields.append(("language", str(utils.getLanguage(options['language'], "peertube"))))
    else:
        # if no language, set default to 1 (English)
        fields.append(("language", "en"))


    fields.append(("commentsEnabled", "1"))

    privacy = None

    
    fields.append(("privacy", str(PEERTUBE_PRIVACY["public"])))

    playlist_id = get_default_playlist(user_info)
    fields.append(("channelId", str(playlist_id)))

    multipart_data = MultipartEncoder(fields)

    headers = {
        'Content-Type': multipart_data.content_type
    }
    response = oauth.post(url + "/api/v1/videos/upload",
                          data=multipart_data,
                          headers=headers)
    if response is not None:
        if response.status_code == 200:
            jresponse = response.json()
            jresponse = jresponse['video']
            uuid = jresponse['uuid']
            idvideo = str(jresponse['id'])
            logging.info('Peertube : Video was successfully uploaded.')
            template = '%s/videos/watch/%s'
            logging.info(template % (url, uuid))
            print(template % (url, uuid))
            return template % (url, uuid)
        else:
            logging.error(('Peertube: The upload failed with an unexpected response: '
                           '%s') % response)
            exit(1)


def run(options):
    secret = RawConfigParser()
    try:
        secret.read(PEERTUBE_SECRETS_FILE)
    except Exception as e:
        logging.error("Peertube: Error loading " + str(PEERTUBE_SECRETS_FILE) + ": " + str(e))
        exit(1)
    oauth = get_authenticated_service(secret)
    try:
        logging.info('Peertube: Uploading video...')
        upload_video(oauth, secret, options)
    except Exception as e:
        if hasattr(e, 'message'):
            logging.error("Peertube: Error: " + str(e.message))
        else:
            logging.error("Peertube: Error: " + str(e))
