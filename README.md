# indigo-prometheus

[Prometheus](https://prometheus.io) is a time-series database, widely used for
visualizing application metrics.  This is a simple client that will present device &
variable information for Prometheus to gather.  Once running, Prometheus has a rich
query engine for building simple views or you can integrate with much more powerful
visualization tools (such as [Grafana](https://grafana.com)).

## Configuring the Plugin

You can choose to present variables, devices or both.  If you run into performance issues
with either option, please submit an issue.

## Viewing Data

Once your plugin is configured, you can view the metrics by visiting
http://localhost:9167/metrics (replace host and port as needed).  This is the default
endpoint used by Prometheus to scrape data.  This can be done before installing
Prometheus.

## Installing Prometheus

The easiest way to install Prometheus on macOS is using
[Homebrew](https://formulae.brew.sh/formula/prometheus).  From there, you can either
register it as a service to run automatically, or run it manually to view debugging
output.

## Configuring Prometheus

Once you have Prometheus installed, simply add the following job to your `scrape_configs` and restart Prometheus:

```
  - job_name: 'indigo'
    scrape_interval: 1m
    static_configs:
      - targets: ['localhost:9176']
```

Modify `scrape_interval` or other configuration values as needed for your installation.

## Querying Prometheus

Once you start collecting data, Prometheus has a rich query language called
[PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/).

### Example: track the value of a single variable over time

Variables are stored in time series using their ID:

    indigo_var_1061581346_value

![](https://github.com/jheddings/indigo-prometheus/raw/master/etc/images/example_variable_over_time.png)

*TIP:* The same variable can be referenced by name using a label selector:
`{name="cfg_irrigation_wx_coef"}`

### Example: show how many SwitchLinc devices are on throughout the day

Device states are either on (1) or off (0).  Using label selectors and regular expressions,
metrics can be combined into custom reports.

    sum({model=~"SwitchLinc.*"})

![](https://github.com/jheddings/indigo-prometheus/raw/master/etc/images/example_switchlinc_day.png)

