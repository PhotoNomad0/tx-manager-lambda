# coding=utf-8
from __future__ import absolute_import, unicode_literals

import os
from unittest import TestCase

import requests
from bs4 import BeautifulSoup


class TestConversions(TestCase):

    def test_usfm_bundle(self):
        baseUrl = "https://git.door43.org"
        user = "deva"
        repo = "kan-x-aruvu_act_text_udb"

        commitID, commitPath, commitSha = self.fetchCommitDataForRepo(baseUrl, repo, user)

        self.assertIsNotNone(commitID)
        self.assertIsNotNone(commitSha)
        self.assertIsNotNone(commitPath)

        print("Loaded: " + self.url)

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
