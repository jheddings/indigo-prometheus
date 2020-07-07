# Prometheus client for Indigo

import logging
import time

import iplug

# XXX included as part of the plugin structure
from prometheus_client import start_http_server, Gauge, Counter, Metric, REGISTRY

# TODO review naming conventions (underscore vs camel case)

# TODO look for refactoring opportunities to remove code duplication

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

        self.collect_devices = self.getPref(prefs, 'collect_devices', True)
        self.collect_variables = self.getPref(prefs, 'collect_variables', True)
        self.user_info = self.getPref(prefs, 'user_info', None)

    #---------------------------------------------------------------------------
    def buildDeviceList(self, filter=None, values=None, typeId=None, targetId=0):
        devices = list()

        for device in indigo.devices:
            if device.pluginId != self.pluginId:
                devices.append([ device.id, device.name ])

        return devices

    #---------------------------------------------------------------------------
    def buildDeviceStateList(self, filter=None, values=None, typeId=None, targetId=0):
        states = list()

        if values is not None and 'device_id' in values:
            device_id = int(values['device_id'])
            device = indigo.devices[device_id]
            self.logger.debug('loading states for device %s [%d]', device.name, device.id)

            states.extend(device.states.keys())

        return states

    #---------------------------------------------------------------------------
    def validateDeviceConfigUi(self, values, typeId, devId):
        errors = indigo.Dict()

        if typeId == 'gauge' or typeId == 'counter':
            device_id = values.get('device_id', None)
            state_id = values.get('state_id', None)
            values['address'] = device_id + ':' + state_id

        # XXX we aren't using errors currently, keeping the placeholder for future use

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def collect(self):
        self.logger.debug('BEGIN metrics collection')

        # update custom metrics first to make sure devices are up
        # to date for collecting regular device metrics later on...
        for custom_dev in indigo.devices.itervalues('self'):
            metric = self.buildCustomMetric(custom_dev)
            if metric is not None: yield metric

        if self.collect_variables:
            for indigo_var in indigo.variables:
                metric = self.buildVarMetric(indigo_var)
                if metric is not None: yield metric

        if self.collect_devices:
            for indigo_dev in indigo.devices:
                metric = self.buildDevMetric(indigo_dev)
                if metric is not None: yield metric

        self.logger.debug('END metrics collection')

    #---------------------------------------------------------------------------
    def getSafeValue(self, value):
        # don't cast if the value is already a safe type
        if isinstance(value, (float, int, bool)):
            return value

        # it's not likely that we will see these types from Indigo, but just in case...
        if isinstance(value, (list, set, tuple, dict, bytes)):
            return None

        # check for "boolean strings"
        if iplug.valueIsTrue(value):
            return True
        elif iplug.valueIsFalse(value):
            return False

        # attempt casting as an int...
        try:
            return int(value)
        except (ValueError, TypeError):
            pass

        # attempt casting as a float...
        try:
            return float(value)
        except (ValueError, TypeError):
            pass

        self.logger.debug('could not convert %s :: %s', value, type(value))

        return None

    #---------------------------------------------------------------------------
    def buildVarMetric(self, var):
        self.logger.debug('reading variable data -- %s => %s', var.name, var.value)

        # use variable ID for metric name, like SQL Logger
        pro_name = 'indigo_var_%d' % var.id

        value = self.getSafeValue(var.value)
        if value is None: return None

        labels = {
            'readOnly' : str(var.readOnly),
            'visible' : str(var.remoteDisplay),
            'name' : var.name
        }

        if self.user_info is not None and len(self.user_info) > 0:
            labels['user_info'] = self.substitute(self.user_info)

        self.logger.debug('%s (%s) -- %s <%s>', pro_name, var.name, value, type(value))

        metric = Metric(pro_name, var.name, 'gauge')
        metric.add_sample(pro_name, value=value, labels=labels)

        return metric

    #---------------------------------------------------------------------------
    def buildDevMetric(self, dev):
        if not dev.enabled: return None
        if not dev.configured: return None

        # don't report back our own devices...
        if dev.pluginId == self.pluginId: return None

        self.logger.debug('reading device data -- %s', dev.name)

        # use device ID for metric name, like SQL Logger
        pro_name = 'indigo_dev_%d' % dev.id

        raw_value = dev.displayStateValRaw
        self.logger.debug('raw display value: %s', str(raw_value))

        value = self.getSafeValue(raw_value)
        if value is None: return None

        labels = {
            'address' : dev.address,
            'enabled' : str(dev.enabled),
            'visible' : str(dev.remoteDisplay),
            'model' : dev.model,
            'name' : dev.name
        }

        if self.user_info is not None and len(self.user_info) > 0:
            labels['user_info'] = self.substitute(self.user_info)

        self.logger.debug('%s (%s) -- %s <%s>', pro_name, dev.name, value, type(value))

        metric = Metric(pro_name, dev.name, 'gauge')
        metric.add_sample(pro_name, value=value, labels=labels)

        return metric

    #---------------------------------------------------------------------------
    def buildCustomMetric(self, dev):
        if not dev.enabled: return None
        if not dev.configured: return None

        self.logger.debug('building custom metric -- %s', dev.name)

        # grab the source device information
        source_dev_id = int(dev.pluginProps['device_id'])
        source_device = indigo.devices[source_dev_id]

        source_state_name = dev.pluginProps['state_id']
        current_value = source_device.states[source_state_name]

        self.logger.debug('source device state -- %s[%s] => %s',
                          source_device.name, source_state_name, str(current_value))

        value = self.getSafeValue(current_value)
        if value is None:
            dev.updateStateOnServer('status', 'Error')
            dev.setErrorStateOnServer('unsupported type: %s' % type(current_value))
            return None

        # XXX do we need to sanitize state_name for Prometheus?
        pro_name = 'indigo_dev_%d_%s' % (source_dev_id, source_state_name)

        # XXX we are using the metric name, not the source device name here...
        # that's intentional, but we may want to add the source device also

        labels = {
            'name' : dev.name
        }

        user_info = dev.pluginProps.get('user_info', None)
        if user_info is not None and len(user_info) > 0:
            labels['user_info'] = self.substitute(user_info)

        self.logger.debug('%s (%s) -- %s <%s>', pro_name, dev.name, value, type(value))

        metric = Metric(pro_name, dev.name, dev.deviceTypeId)
        metric.add_sample(pro_name, value=value, labels=labels)

        dev.updateStateOnServer('status', value=value)
        dev.updateStateOnServer('lastReportedAt', value=time.strftime('%c'))

        return metric

