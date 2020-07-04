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

        # XXX if we could register custom API paths directly within Indigo,
        # we could potentially avoid spinning up an additional HTTP server...

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
    def loadPluginPrefs(self, prefs):
        iplug.PluginBase.loadPluginPrefs(self, prefs)

        self.collect_device_states = self.getPref(prefs, 'collect_device_states', False)
        self.collect_variables = self.getPref(prefs, 'collect_variables', True)

    #---------------------------------------------------------------------------
    def collect(self):
        self.logger.debug('BEGIN metrics collection')

        if self.collect_variables:
            for indigo_var in indigo.variables:
                metric = self.build_var_metric(indigo_var)
                if metric is not None: yield metric

        if self.collect_device_states:
            for indigo_dev in indigo.devices:
                metric = self.build_dev_metric(indigo_dev)
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

        # use variable ID for metric name, like SQL Logger
        pro_name = 'indigo_var_%d' % var.id

        value = self.get_safe_value(var.value)
        if value is None: return None

        labels = {
            'readOnly' : str(var.readOnly),
            'visible' : str(var.remoteDisplay),
            'name' : var.name
        }

        metric = Metric(pro_name, var.name, 'gauge')
        metric.add_sample(pro_name + '_value', value=value, labels=labels)

        return metric

    #---------------------------------------------------------------------------
    def build_dev_metric(self, dev):
        self.logger.debug('reading device data -- %s', dev.name)

        # use device ID for metric name, like SQL Logger
        pro_name = 'indigo_dev_%d' % dev.id

        labels = {
            'address' : dev.address,
            'enabled' : str(dev.enabled),
            'visible' : str(dev.remoteDisplay),
            #'protocol' : dev.protocol,
            #'model' : dev.model,
            'name' : dev.name
        }

        metric = Metric(pro_name, dev.name, 'gauge')

        for state in dev.states:
            state_name = pro_name + '_' + state
            value = dev.states[state]

            self.logger.debug('>> %s => %s', state, value)

            state_value = self.get_safe_value(value)
            if state_value is None: continue

            metric.add_sample(state_name, value=state_value, labels=labels)

        return metric

