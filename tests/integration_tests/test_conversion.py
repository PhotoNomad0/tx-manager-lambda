# coding=utf-8
from __future__ import absolute_import, unicode_literals

import tempfile

import os
from unittest import TestCase

import requests
import shutil

import time

from manager.manager import TxManager

from general_tools.file_utils import unzip

from aws_tools.s3_handler import S3Handler

from client.client_webhook import ClientWebhook

from bs4 import BeautifulSoup

COMMIT_LENGTH = 40

class TestConversions(TestCase):

    def setUp(self):
        self.api_url = 'https://dev-api.door43.org'
        self.pre_convert_bucket = 'dev-tx-webhook-client'
        self.gogs_url = 'https://git.door43.org'
        self.cdn_bucket = 'dev-cdn.door43.org'
        self.job_table_name = 'dev-tx-job'
        self.module_table_name = 'dev-tx-module'
        self.cdn_url = 'https://dev-cdn.door43.org'

    def tearDown(self):
        """Runs after each test."""
        # delete temp files
        if hasattr(self, 'temp_dir') and os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_usfm_mat_bundle(self):
        # given
        if not self.doWeWantToRunTest(): return # skip test if integration test not enabled
        baseUrl = "https://git.door43.org"
        user = "vedhanthavijay"
        repo = "kpb_mat_text_udb"
        expectedOutputName = "41-MAT"

        # when
        build_log_json, commitID, commitPath, commitSha, success = self.doConversionForRepo(baseUrl, user, repo)

        # then
        self.validateBible(user, repo, success, build_log_json, commitID, commitSha, commitPath, expectedOutputName)

    def test_usfm_acts_bundle(self):
        # given
        if not self.doWeWantToRunTest(): return # skip test if integration test not enabled
        baseUrl = "https://git.door43.org"
        user = "lversaw"
        repo = "awa_act_text_reg"
        expectedOutputName = "45-ACT"

        # when
        build_log_json, commitID, commitPath, commitSha, success = self.doConversionForRepo(baseUrl, user, repo)

        # then
        self.validateBible(user, repo, success, build_log_json, commitID, commitSha, commitPath, expectedOutputName)

    def test_usfm_acts2_bundle(self):
        # given
        if not self.doWeWantToRunTest(): return # skip test if integration test not enabled
        baseUrl = "https://git.door43.org"
        user = "deva"
        repo = "kan-x-aruvu_act_text_udb"
        expectedOutputName = "45-ACT"

        # when
        build_log_json, commitID, commitPath, commitSha, success = self.doConversionForRepo(baseUrl, user, repo)

        # then
        self.validateBible(user, repo, success, build_log_json, commitID, commitSha, commitPath, expectedOutputName)

    ##
    ## handlers
    ##

    def doWeWantToRunTest(self):
        test = os.environ.get('TEST_DEPLOYED',"")
        doTest = (test == "test_deployed")
        if not doTest:
            print("Skip testing since TEST_DEPLOYED is not set")
        else:
            gogsUserToken = os.environ.get('GOGS_USER_TOKEN',"")
            self.assertTrue(len(gogsUserToken) > 0, "GOGS_USER_TOKEN is missing in environment")
        return doTest

    def validateBible(self, user, repo, success, build_log_json, commitID, commitSha, commitPath, expectedOutputName):
        self.assertTrue(len(build_log_json) > 0)
        self.assertTrue(len(build_log_json['errors']) == 0, "Found errors: " + str(build_log_json['errors']))
        self.assertTrue(success)
        self.temp_dir = tempfile.mkdtemp(prefix='testing_')
        self.downloadAndCheckZipFile(self.s3_handler, expectedOutputName + ".usfm", self.getPreconvertS3Key(commitSha),
                                     "preconvert")
        # this gets deleted after conversion:
        # self.downloadAndCheckZipFile(self.cdn_handler, expectedOutputName + ".html", self.getTxOutputS3Key(commitID), "output")
        self.checkDestinationFiles(self.cdn_handler, expectedOutputName + ".html",
                                   self.getDestinationS3Key(commitSha, repo, user))
        self.assertEqual(len(commitID), COMMIT_LENGTH)
        self.assertIsNotNone(commitSha)
        self.assertIsNotNone(commitPath)

    def downloadAndCheckZipFile(self, handler, expectedOutputFile, key, type):
        zipPath = os.path.join(self.temp_dir, type + ".zip")
        handler.download_file(key, zipPath)
        temp_sub_dir = tempfile.mkdtemp(dir=self.temp_dir, prefix=type + "_")
        unzip(zipPath, temp_sub_dir)
        self.assertTrue(os.path.exists(os.path.join(temp_sub_dir, expectedOutputFile)))
        self.assertTrue(os.path.exists(os.path.join(temp_sub_dir, "manifest.json"))
                        or os.path.exists(os.path.join(temp_sub_dir, "manifest.yaml")))

    def checkDestinationFiles(self, handler, expectedOutputFile, key):
        output = handler.get_file_contents(os.path.join(key, expectedOutputFile) )
        self.assertTrue(len(output) > 0)
        manifest = handler.get_file_contents(os.path.join(key, "manifest.json") )
        if manifest == None:
            manifest = handler.get_file_contents(os.path.join(key, "manifest.yaml") )
        self.assertTrue(len(manifest) > 0)

    def doConversionForRepo(self, baseUrl, user, repo):
        build_log_json = None
        success = False
        self.cdn_handler = S3Handler(self.cdn_bucket)
        commitID, commitPath, commitSha = self.fetchCommitDataForRepo(baseUrl, repo, user)  # TODO: change this to use gogs API when finished
        commitLen = len(commitID)
        if commitLen == COMMIT_LENGTH:
            self.deletePreconvertZipFile(commitSha)
            self.deleteTxOutputZipFile(commitID)
            self.emptyDestinationFolder(commitSha, repo, user)
            build_log_json, success = self.doConversionJob(baseUrl, commitID, commitPath, commitSha, repo, user)

        return build_log_json, commitID, commitPath, commitSha, success

    def emptyDestinationFolder(self, commitSha, repo, user):
        destination_key = self.getDestinationS3Key(commitSha, repo, user)
        for obj in self.cdn_handler.get_objects(prefix=destination_key):
            print("deleting destination file: " + obj.key)
            self.cdn_handler.delete_file(obj.key)

    def deletePreconvertZipFile(self, commitSha):
        self.s3_handler = S3Handler(self.pre_convert_bucket)
        preconvert_key = self.getPreconvertS3Key(commitSha)
        if self.s3_handler.key_exists(preconvert_key):
            print("deleting preconvert file: " + preconvert_key)
            self.s3_handler.delete_file(preconvert_key, catch_exception=True)

    def deleteTxOutputZipFile(self, commitID):
        txOutput_key = self.getTxOutputS3Key(commitID)
        if self.cdn_handler.key_exists(txOutput_key):
            print("deleting tx output file: " + txOutput_key)
            self.cdn_handler.delete_file(txOutput_key, catch_exception=True)

    def getTxOutputS3Key(self, commitID):
        output_key = 'tx/job/{0}.zip'.format(commitID)
        return output_key

    def getDestinationS3Key(self, commitSha, repo, user):
        destination_key = 'u/{0}/{1}/{2}'.format(user, repo, commitSha)
        return destination_key

    def getPreconvertS3Key(self, commitSha):
        preconvert_key = "preconvert/{0}.zip".format(commitSha)
        return preconvert_key

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
            'api_url': self.api_url,
            'pre_convert_bucket': self.pre_convert_bucket,
            'cdn_bucket': self.cdn_bucket,
            'gogs_url': self.gogs_url,
            'gogs_user_token': gogsUserToken,
            'commit_data': webhookData
        }
        try:
            build_log_json = ClientWebhook(**env_vars).process_webhook()
        except Exception as e:
            message = "Exception: " + str(e)
            print(message)
            return None, False

        success = self.pollUntilJobFinished(build_log_json['job_id'])
        build_log_json = self.getJsonFile(commitSha, 'build_log.json', repo, user)
        if build_log_json != None:
            print("Final results:\n" + str(build_log_json))
        return build_log_json, success

    def pollUntilJobFinished(self, job_id):
        success = False

        env_vars = {
            'api_url': self.api_url,
            'gogs_url': self.gogs_url,
            'cdn_url': self.cdn_url,
            'job_table_name':  self.job_table_name,
            'module_table_name': self.module_table_name,
            'cdn_bucket': self.cdn_bucket
        }
        tx_manager = TxManager(**env_vars)

        pollingTimeout = 5 * 60 # poll for up to 5 minutes for job to complete or error
        sleepInterval = 5 # how often to check for completion
        startMaxWaitCount = 30 / sleepInterval # maximum count to wait for conversion to start (sec/interval)
        for i in range(0, pollingTimeout / sleepInterval):
            job = tx_manager.get_job(job_id)
            self.assertIsNotNone(job)
            print("job status at " + str(i) + ":\n" + str(job.log))

            if len(job.errors) > 0:
                print("Found errors: " + str(job.errors))
                break

            if job.ended_at != None:
                success = True
                break

            if (i > startMaxWaitCount) and (job.started_at == None):
                success = False
                print("Conversion Failed to start")
                break

            time.sleep(sleepInterval)

        return success

    def getJsonFile(self, commitSha, file, repo, user):
        key = 'u/{0}/{1}/{2}/{3}'.format(user, repo, commitSha, file)
        text = self.cdn_handler.get_json(key)
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
                            commitID = parts[4]
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