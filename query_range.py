#!/home/cmusali/forks/insights-perf/tally/swatch/venv/bin/python3

from uuid import uuid4
from random import randint
from os import getenv

from flask import Flask, g
from flask_restful import Resource, Api, reqparse

import re
import logging
import psycopg2
import time
import datetime


def get_Logger(log_name: str, log_level: int = 20) -> logging.Logger:
    '''
    Initialize the logger with a name and an optional level.
    '''
    # Create a custom logger, handler and formatter
    logger = logging.Logger(log_name, level = log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
 
    # Add custom formatter to the log handler and also set the log level.
    log_handler.setFormatter(log_formatter)
    if log_level == 10:
        log_handler.setLevel(logging.DEBUG)
    else:
        log_handler.setLevel(logging.INFO)

    # Add custom handler to the logger and return the logger object to log events
    logger.addHandler(log_handler)
    return logger

class swatch_rds(object):
    '''
    Connect to SWATCH RDS and return orgID from org_config/account_config tables
    '''

    def __init__(self, ):
        self.db_host_name = getenv('RHSM_DB_HOST')
        self.db_name = getenv('RHSM_DB_NAME')
        self.db_user = getenv('RHSM_DB_USER')
        self.db_password = getenv('RHSM_DB_PASS')
        self.DSN = f'host={self.db_host_name} dbname={self.db_name} user={self.db_user} password={self.db_password}'
        self.db_queries = {
            'get_orgID': 'SELECT org_id FROM org_config;',
            'get_accountID': 'SELECT account_number FROM account_config WHERE org_id = %s;',
        }

    def get_orgID(self, ):
        # Returns orgID from SWATCH database
        try:
            with psycopg2.connect(self.DSN) as db_conn:
                with db_conn.cursor() as cursor:
                    cursor.execute(self.db_queries['get_orgID'])
                    self.org_Ids = cursor.fetchall()
                    self.org_Ids = [ item[0] for item in self.org_Ids ]
        
            if self.org_Ids:
                logger.info(f'orgIDs available in SWATCH database - {self.org_Ids}')
            else:
                logger.info(f'No orgIDs available in SWATCH database - {self.org_Ids}')
        except Exception as E:
            logger.error(f'An exception occured while querying database {E}')
            self.org_Ids = []

        return self.org_Ids
    
    def get_accountID(self, *data):
        # Returns accountID that is associated to an orgID from SWATCH database
        try:
            with psycopg2.connect(self.DSN) as db_conn:
                with db_conn.cursor() as cursor:
                    cursor.execute(self.db_queries['get_accountID'], data)
                    self.account_Ids = cursor.fetchall()
                    self.account_Ids = [ item[0] for item in self.account_Ids ]
 
            if self.account_Ids:
                logger.info(f'accountIDs available in SWATCH database - {self.account_Ids}')
            else:
                logger.info(f'No accountIDs available in SWATCH database - {self.account_Ids}')
        except Exception as E:
            logger.error(f'An exception occured while querying database {E}')
            self.account_Ids = []

        return self.account_Ids

# https://flask.palletsprojects.com/en/1.1.x/reqcontext/
# https://flask.palletsprojects.com/en/2.3.x/appcontext/#storing-data
app = Flask(__name__)

@app.before_request
def before_request():
    # Stores the start time of a http request
    logger.info(f'HTTP request start time - {datetime.datetime.utcnow().isoformat()}')
    g.http_request_start_time = time.time()

@app.after_request
def after_request(response):
    # Calculates the response time of a http request
    g.http_request_response_time = time.time() - g.http_request_start_time
    logger.info(f'HTTP request end time - {datetime.datetime.utcnow().isoformat()}')
    logger.info(f'HTTP request response time in seconds - {g.http_request_response_time}')
    return response

# Concrete API's should extend abstract RESTful "Resource" class 
# From this class expose methods for each supported HTTP method.
class query_range_api(Resource):
    '''
    "/query_range" mock API for swatch-metrics (Metering) scale testing.
    '''
    def metrics_sync_data(self, org_ID, start_time) -> dict:
        # Returns data for initiating metering-sync
        return {
            "metric": {
                "external_organization": f"{org_ID}"
            },
            "values": [
                [
                    f"{start_time}",
                    1
                ]
            ]
        }

    def timeseries_data(self, accountID, orgID, product_name, start_time) -> dict:
        # Returns hosts data for a given accountID and orgID
        return {
                    "metric": {
                        "_id": uuid4().__str__(),
                        "billing_marketplace_account": f"mktp-{orgID}",
                        "billing_model": "marketplace",
                        "billing_provider": "aws",
                        "ebs_account": f"{accountID}",
                        "external_organization": f"{orgID}",
                        "product": f"{product_name}",
                        "support": "Premium"
                    },
                    "values": [
                                [
                                    f"{start_time}",
                                    randint(1, 100)
                                ]
                        ]
                }

    def get(self, ) -> dict:
        # RequestParser to capture query_parameters from a request
        parser = reqparse.RequestParser()

        # Add query parameters
        # https://flask-restful.readthedocs.io/en/latest/reqparse.html#argument-locations
        parser.add_argument('query', location="args")
        parser.add_argument('start', location="args")
        args = parser.parse_args()

        # Return timeseries data for the specific tagMetrics.
        tagMetric = {
                        'ocp': {
                            'tag': 'OpenShift-metrics',
                            'prometheusMetric': 'cluster:usage:workload:capacity_physical_cpu_hours'
                        },
                        'osd': {
                            'tag': 'OpenShift-dedicated-metrics',
                            'prometheusMetric': 'cluster:usage:workload:capacity_physical_cpu_hours'
                        },
                        'rhosak': {
                            'tag': 'rhosak',
                            'prometheusMetric': 'kafka_id:kafka_broker_quota_totalstorageusedbytes:max_over_time1h_gibibyte_months'
                        },
                        'rhacs': {
                            'tag': 'rhacs',
                            'prometheusMetric': 'rhacs:rox_central_cluster_metrics_cpu_capacity:avg_over_time1h'
                        },
            }
        product_label = [ product for product in tagMetric if product in args['query'] ]

        # For processing metrics-sync cronjob promQL queries
        if re.search(r'^group.+subscription_labels.+organization\)$', args['query']) and product_label:
            # 
            orgIds = swatch_rds().get_orgID()   #list
 
            return {
                'status': 'success',
                'data': {
                    'resultType': 'matrix',
                    'result': [
                        self.metrics_sync_data(_ID, args['start']) for _ID in orgIds
                    ]
                }
            }, 200  

        # For processing metrics-service promQL queries
        elif 'support' in args['query'] and product_label:
            #
            SYSTEM_PER_ORGANIZATION = getenv('SYS_PER_ORG', 10)
            logger.info(f'HTTP request for total host events - {SYSTEM_PER_ORGANIZATION}')
            orgIds = re.sub(r'.+external_organization\=[\"\'](.+)[\'\"]\,.+marketplace.+', r'\1', args['query'])    #string
            accountIds = swatch_rds().get_accountID(orgIds)

            if accountIds and orgIds not in SYSTEMS_LIST:
                logger.info(f'Data does not exist for {orgIds} in the system memory')
                SYSTEMS_LIST.clear()
                SYSTEMS_LIST[orgIds] = [ 
                    self.timeseries_data(accountIds[-1], orgIds, product_label[-1], args['start']) for _ in range(int(SYSTEM_PER_ORGANIZATION))
                ]
            else:
                logger.info(f'Data exists for {orgIds} in the system memory, Useful for re-metering operation')

            if accountIds:
                return {
                    'status': 'success',
                    'data': {
                        'resultType': 'matrix',
                        'result': SYSTEMS_LIST[orgIds]
                    }
                }, 200
            else:
                return {
                "status":"success",
                "data": {
                    "resultType":"matrix",
                    "result":[]
                }
            }, 200

        # For any other promQL queries
        else:
            return {
                "status":"success",
                "data": {
                    "resultType":"matrix",
                    "result":[]
                }
            }, 200
 
class HealthCheck(Resource):
    '''
    Simple healthcheck endpoint to verify server is running
    '''
    def get(self):
        return {
            "status": "success",
            "service": "metering-prometheus-mock",
            "message": "Server is healthy and running",
            "endpoint": "/api/v1/query_range",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }, 200
    
if __name__ == '__main__':
    # create logging
    logger = get_Logger('metering-prometheus-mock')

    # create a Flask app and main entrypoint for the application
    #app = Flask(__name__)
    api = Api(app)

    # hold the systems list for re-metering
    SYSTEMS_LIST = {}

    # adds a resource to the api.
    api.add_resource(query_range_api, '/api/v1/query_range')
    
    api.add_resource(HealthCheck, '/')

    # run the application on a local development server
    app.run(host='0.0.0.0', port=9090)
