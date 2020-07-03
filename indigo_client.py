# Prometheus client for Indigo

import os
import json
import sys
import time

import requests

import logging
import logging.config

from datetime import datetime

from requests.auth import HTTPDigestAuth
from prometheus_client import start_http_server, Metric, REGISTRY

################################################################################
class IndigoServer(object):

    def __init__(self, conf):
        self.host = conf.get('hostname', 'localhost')
        self.port = conf.get('port', 8176)
        self.username = conf.get('username', None)
        self.password = conf.get('password', None)

        self.logger = logging.getLogger('IndigoServer')

    #---------------------------------------------------------------------------
    def get(self, path):
        self.logger.debug('retriving API path: %s', path)

        auth = None
        if self.username is not None:
            self.logger.debug('configuring digest auth -- %s', self.username)
            auth = HTTPDigestAuth(self.username, self.password)

        url = f'http://{self.host}:{self.port}{path}'
        resp = requests.get(url, auth=auth)

        self.logger.debug('=> %s -- %d bytes', url, len(resp.content))

        if not resp.ok:
            self.logger.warn('HTTP %d', resp.status_code)

        return resp.json()

################################################################################
class IndigoCollector(object):

    def __init__(self, server):
        self.server = server
        self.logger = logging.getLogger('IndigoCollector')

    #---------------------------------------------------------------------------
    def value_type(self, value):
        if type(value) is int:
            return 'gauge'

        if type(value) is float:
            return 'gauge'

        return None

    #---------------------------------------------------------------------------
    def build_metric(self, detail):
        # TODO add logging...

        name = detail['name']
        pro_name = f'indigo_var_{name}'

        value = detail['value']
        value_type = self.value_type(value)

        # TODO add support for "info" types (e.g. summary with value of 1)
        if value_type is None:
            return None

        # pull all detail into labels, excluding special keys
        labels = { k: str(v) for (k, v) in detail.items() if k not in [ 'name', 'value' ] }

        metric = Metric(pro_name, detail['name'], value_type)
        metric.add_sample(pro_name, value=value, labels=labels)

        return metric

    #---------------------------------------------------------------------------
    def collect(self):
        start_time = datetime.now()

        indigo_vars = self.server.get('/variables.json/')

        for indigo_var in indigo_vars:
            var_detail = self.server.get(indigo_var['restURL'])
            metric = self.build_metric(var_detail)
            if metric is not None: yield metric

################################################################################
def parse_args():
    import argparse

    argp = argparse.ArgumentParser(description='Prometheus metrics client for Indigo')

    argp.add_argument('--config', default='indigo_client.cfg',
                      help='configuration file (default: indigo_client.cfg)')

    #argp.add_argument('params', nargs=argparse.REMAINDER)

    return argp.parse_args()

################################################################################
def load_config(config_file):
    import yaml
    import logging.config

    try:
        from yaml import CLoader as YamlLoader
    except ImportError:
        from yaml import Loader as YamlLoader

    if not os.path.exists(config_file):
        logging.warning('!! config file does not exist: %s', config_file)
        return None

    with open(config_file, 'r') as fp:
        conf = yaml.load(fp, Loader=YamlLoader)

    if 'Logging' in conf:
        logging.config.dictConfig(conf['Logging'])

    logging.debug('!! config file loaded: %s', config_file)

    return conf

################################################################################
def run_server_loop():
    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info('Canceled by user')

################################################################################
## MAIN ENTRY
if __name__ == '__main__':

    args = parse_args()
    conf = load_config(args.config)

    # start the server on the configured port
    port = conf['Metrics Endpoint']['port']
    logging.info('Starting metrics endpoint on port: %d', port)
    start_http_server(port)

    # add the indigo collector to the metrics registry
    server = IndigoServer(conf['Indigo API'])
    collector = IndigoCollector(server=server)
    REGISTRY.register(collector)

    run_server_loop()

