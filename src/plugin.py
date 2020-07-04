# Prometheus client for Indigo

import logging

import iplug

# XXX included as part of the plugin structure
from prometheus_client import start_http_server, Metric, REGISTRY

################################################################################
class Plugin(iplug.PluginBase):

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        iplug.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.logger = logging.getLogger('Plugin.prometheus')

        port = int(pluginPrefs.get('port', 9176))

        self.logger.info('Starting Prometheus endpoint on port %d', port)
        start_http_server(port)

        REGISTRY.register(self)

        # XXX not sure if we will need this or not...
        #indigo.devices.subscribeToChanges()

    #---------------------------------------------------------------------------
    def validatePrefsConfigUi(self, values):
        errors = indigo.Dict()

        iplug.validateConfig_Int('port', values, errors, min=1024, max=49151)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def collect(self):
        self.logger.debug('BEGIN metrics collection')

        for indigo_var in indigo.variables:
            metric = self.build_var_metric(indigo_var)
            if metric is not None: yield metric

        self.logger.debug('END metrics collection')

    #---------------------------------------------------------------------------
    def get_safe_value(self, value):
        # TODO handle boolean values

        try:
            int_value = int(value)
            self.logger.debug('>> int(%d)', int_value)
            return int_value
        except (ValueError, TypeError):
            pass

        try:
            float_value = float(value)
            self.logger.debug('>> float(%f)', float_value)
            return float_value
        except (ValueError, TypeError):
            pass

        self.logger.debug('>> None(%s)', value)

        return None

    #---------------------------------------------------------------------------
    def build_var_metric(self, var):
        self.logger.debug('reading variable data -- %s => %s', var.name, var.value)

        # XXX should we use variable ID instead, like SQL Logger?
        pro_name = 'indigo_var_%s' % var.name

        value = self.get_safe_value(var.value)
        if value is None: return None

        value_type = self.value_type(value)
        if value_type is None: return None

        labels = {
            'readOnly' : str(var.readOnly),
            'visible' : str(var.remoteDisplay),
            'id' : str(var.id)
        }

        metric = Metric(pro_name, var.name, value_type)
        metric.add_sample(pro_name, value=value, labels=labels)

        return metric

    #---------------------------------------------------------------------------
    def value_type(self, value):
        if type(value) is int:
            return 'gauge'

        if type(value) is float:
            return 'gauge'

        return None

