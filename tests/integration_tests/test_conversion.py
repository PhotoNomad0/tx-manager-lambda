# coding=utf-8
from __future__ import absolute_import, unicode_literals

import tempfile

import os
from unittest import TestCase

import requests
import shutil

import time

from aws_tools.s3_handler import S3Handler

from client.client_webhook import ClientWebhook

from bs4 import BeautifulSoup

COMMIT_LENGTH = 40

class TestConversions(TestCase):

    def tearDown(self):
        """Runs after each test."""
        # delete temp files
        if hasattr(self, 'temp_dir') and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def doWeWantToRunTest(self):
        branch = os.environ.get('TRAVIS_BRANCH',"")
        if branch == "": # if Travis variable is not set, then default to master for local testing
            branch = "master"
            print("Doing Local Testing")

        doTest = (branch == "master")
        if not doTest:
            print("Skip testing since not running in master branch but branch: " + branch)
        else:
            gogsUserToken = os.environ.get('GOGS_USER_TOKEN',"")
            self.assertTrue(len(gogsUserToken) > 0, "GOGS_USER_TOKEN is missing in environment")
        return doTest

    def test_usfm_bundle(self):
        if not self.doWeWantToRunTest():
            return # skip test if not running master branch

        # given
        baseUrl = "https://git.door43.org"
        user = "deva"
        repo = "kan-x-aruvu_act_text_udb"

        # when
        build_log_json, commitID, commitPath, commitSha, success = self.doConversionForRepo(baseUrl, user, repo)

        # then
        self.assertTrue(len(build_log_json) > 0)
        self.assertTrue(len(build_log_json['errors']) == 0, "Found errors: " + str(build_log_json['errors']))
        self.assertTrue(success)
        self.assertEqual(len(commitID), COMMIT_LENGTH)
        self.assertIsNotNone(commitSha)
        self.assertIsNotNone(commitPath)

    ## handlers

    def doConversionForRepo(self, baseUrl, user, repo):
        commitID, commitPath, commitSha = self.fetchCommitDataForRepo(baseUrl, repo, user)  # TODO: change this to use gogs API when finished
        commitLen = len(commitID)
        if commitLen == COMMIT_LENGTH:
            build_log_json, success = self.doConversionJob(baseUrl, commitID, commitPath, commitSha, repo, user)
        return build_log_json, commitID, commitPath, commitSha, success

    def doConversionJob(self, baseUrl, commitID, commitPath, commitSha, repo, user):
        gogsUserToken = os.environ.get('GOGS_USER_TOKEN',"")
        if len(gogsUserToken) == 0:
            print("GOGS_USER_TOKEN is missing in environment")

        webhookData = {
            "after": commitID,
            "commits": [
                {
                    "id": "b9278437b27024e07d02490400138d4fd7d1677c",
                    "message": "Fri Dec 16 2016 11:09:07 GMT+0530 (India Standard Time)\n",
                    "url": baseUrl + commitPath,
                }],
            "compare_url": "",
            "repository": {
                "name": repo,
                "owner": {
                    "id": 1234567890,
                    "username": user,
                    "full_name": user,
                    "email": "you@example.com"
                },
            },
            "pusher": {
                "id": 123456789,
                "username": "test",
                "full_name": "",
                "email": "you@example.com"
            },
        }
        env_vars = {
            'api_url': 'https://dev-api.door43.org',
            'pre_convert_bucket': 'dev-tx-webhook-client',
            'cdn_bucket': 'dev-cdn.door43.org',
            'gogs_url': 'https://git.door43.org',
            'gogs_user_token': gogsUserToken,
            'commit_data': webhookData
        }
        try:
            success = False
            cdn_handler = S3Handler(env_vars['cdn_bucket'])
            ClientWebhook(**env_vars).process_webhook()
        except Exception as e:
            message = "Exception: " + str(e)
            print(message)
            return None, False

        build_log_json, success = self.pollUntilJobFinished(cdn_handler, commitSha, repo, success, user)
        return build_log_json, success

    def pollUntilJobFinished(self, cdn_handler, commitSha, repo, success, user):
        for i in range(0, 60):  # poll for up to 300 seconds for job to complete or error
            build_log_json = self.getJsonFile(cdn_handler, commitSha, 'build_log.json', repo, user)
            self.assertTrue(len(build_log_json) > 0)
            if len(build_log_json['errors']) > 0:
                print("Found errors: " + str(build_log_json['errors']))
                break
            if build_log_json['ended_at'] != None:
                success = True
                break
            print("status at " + str(i) + ":\n" + str(build_log_json))
            time.sleep(5)

        if build_log_json != None:
            print("Final results:\n" + str(build_log_json))
        return build_log_json, success

    def getJsonFile(self, cdn_handler, commitSha, file, repo, user):
        key = 'u/{0}/{1}/{2}/{3}'.format(user, repo, commitSha, file)
        text = cdn_handler.get_json(key)
        return text

    def fetchCommitDataForRepo(self, baseUrl, repo, user):
        commitID = None
        commitSha = None
        commitPath = None
        data = self.readContentsOfRepo(baseUrl, user, repo)
        if len(data) > 10:
            commitID, commitSha, commitPath = self.findLastedCommitFromPage(data)
        return commitID, commitPath, commitSha

    def findLastedCommitFromPage(self, text):
        soup = BeautifulSoup(text, 'html.parser')
        table = soup.find('table')
        commitID = None
        commitSha = None
        commitPath = None
        if table != None:
            rows = table.findAll('tr')
            if (rows != None) and (len(rows) > 0):
                for row in rows:
                    commitCell = row.find('td', {"class": "sha"} )
                    if commitCell != None:
                        commitLink = commitCell.find('a')
                        if commitLink != None:
                            commitPath = commitLink['href']
                            commitSha = self.getContents(commitLink)
                            parts = commitPath.split('/')
                            commitID = parts[4];
                            break

        return commitID, commitSha, commitPath

    def makeFolder(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def readContentsOfRepo(self, baseUrl, user, repo):
        self.url = "{0}/{1}/{2}/commits/master".format(baseUrl, user, repo)
        ttr_response = requests.get(self.url)
        if ttr_response.status_code == 200:
            return ttr_response.text

        print("Failed to load: " + self.url)
        return None

    def getContents(self, item):
        if item != None:
            contents = item.stripped_strings
            for string in contents:
                text = string
                return text
        return None
