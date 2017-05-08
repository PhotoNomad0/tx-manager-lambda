master:

.. image:: https://travis-ci.org/unfoldingWord-dev/tx-manager-lambda.svg?branch=master
    :alt: Build Status
    :target: https://travis-ci.org/unfoldingWord-dev/tx-manager-lambda

.. image:: https://coveralls.io/repos/github/unfoldingWord-dev/tx-manager-lambda/badge.svg?branch=master
    :alt: Coveralls
    :target: https://coveralls.io/github/unfoldingWord-dev/tx-manager-lambda?branch=master

develop:

.. image:: https://travis-ci.org/unfoldingWord-dev/tx-manager-lambda.svg?branch=develop
    :alt: Build Status
    :target: https://travis-ci.org/unfoldingWord-dev/tx-manager-lambda

.. image:: https://coveralls.io/repos/github/unfoldingWord-dev/tx-manager-lambda/badge.svg?branch=develop
    :alt: Coveralls
    :target: https://coveralls.io/github/unfoldingWord-dev/tx-manager-lambda?branch=develop


**NOTE: High level Architecture documentation is at** http://tx-manager.readthedocs.io/en/latest/readme.html#tx-architecture.



tx-manager-lambda
=================

Lambda functions for tx Manager. Requires the [tx-manager library] (https://github.com/unfoldingWord-dev/tx-manager).

Project description at https://github.com/unfoldingWord-dev/door43.org/wiki/tX-Development-Architecture#tx-manager-lambda-module.

Issue for its creation at https://github.com/unfoldingWord-dev/door43.org/issues/53


Setting up as deployed in virtual environment
=============================================

In IntelliJ terminal, first switch to virtual environment (replace `<path_to_venv>` with path to your virtualenv).

    **source ~/<path_to_venv>/bin/activate**

Next install requirements:

    **cd ~/Projects/tx-manager-lambda**

    **./install-requirements.sh**


Deploying your branch of tx-manager to AWS
==========================================
For developing the tx-manager library which this repo uses for every function, you can deploy your code to a test AWS
environment with apex by doing the following:

* Copy **project.test.json.sample** to **project.test.json**
* Edit **project.test.json** and change <username> and <branch> to your tx-manager branch
* Install apex from http://apex.run/#installation
* Set up your AWS credentials as specified at http://apex.run/#aws-credentials
* Run **apex deploy --env test** to deploy all functions to **test-api.door43.org**; or do **apex deploy --env test [function-name]** to deploy a single function

For more information on using **--env** to specify a project json file, see https://github.com/apex/apex/blob/master/docs/projects.md#multiple-environments

